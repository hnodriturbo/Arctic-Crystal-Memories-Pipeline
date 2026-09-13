"""
File: converter/2.5D-pipeline/code/gnm_head_refine.py
Purpose:
 - Fit the Apache-2.0 Google GNM Head v3 model to every 468-point MediaPipe
   face measured by the existing 2.5D pipeline.
 - Convert each fitted head into a smooth, low-frequency depth prior while
   preserving MoGe/normal-map beard, hair, skin, and clothing detail.
 - Produce inspectable fitted-head OBJ files and QA images before the refined
   depth is converted into the final Blender relief mesh.

This is the automatic head-shape stage. Blender/ACM Scene Composer remains the
approval and manual finishing stage rather than the place where missing head
geometry must be created by hand.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn.functional as functional
from PIL import Image, ImageDraw


PIPELINE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_GNM_ROOT = PIPELINE_ROOT / "Models" / "research" / "GNM"
DEFAULT_CORRESPONDENCE = (
    PIPELINE_ROOT / "Models" / "research" / "mediapipe" / "gnm_head_dense_468.txt"
)


@dataclass(frozen=True)
class FitResult:
    """Optimized GNM shape and weak-perspective camera for one face."""

    vertices: np.ndarray
    triangles: np.ndarray
    skin_indices: np.ndarray
    rotation: np.ndarray
    scale: float
    translation: np.ndarray
    fitted_landmarks_normalized: np.ndarray
    loss: float
    identity_rms: float
    expression_rms: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--depth", required=True, type=Path, help="16-bit bright-is-near depth PNG.")
    parser.add_argument("--faces", required=True, type=Path, help="face_refine.py JSON with 468 landmarks.")
    parser.add_argument("--photo", required=True, type=Path, help="Source RGB/RGBA photograph.")
    parser.add_argument("--output", required=True, type=Path, help="Refined 16-bit depth PNG.")
    parser.add_argument("--qa-dir", required=True, type=Path, help="Directory for overlays, priors, and OBJs.")
    parser.add_argument("--gnm-root", type=Path, default=DEFAULT_GNM_ROOT)
    parser.add_argument("--correspondence", type=Path, default=DEFAULT_CORRESPONDENCE)
    parser.add_argument("--head-span", type=float, default=0.34, help="Head relief span as normalized depth.")
    parser.add_argument(
        "--front-headroom",
        type=float,
        default=0.12,
        help="Reserved normalized depth in front of the source before the head prior is fused.",
    )
    parser.add_argument(
        "--back-headroom",
        type=float,
        default=0.12,
        help="Reserved normalized depth behind the source before the head prior is fused.",
    )
    parser.add_argument("--detail-sigma", type=float, default=11.0)
    parser.add_argument("--feather", type=float, default=24.0, help="Prior edge feather in pixels.")
    parser.add_argument(
        "--silhouette-taper",
        type=float,
        default=12.0,
        help="Pixels used to ease cut-out edges toward the back plane.",
    )
    parser.add_argument("--camera-steps", type=int, default=350)
    parser.add_argument("--shape-steps", type=int, default=850)
    parser.add_argument("--device", choices=("auto", "cuda", "cpu"), default="auto")
    return parser.parse_args()


def centre_depth_with_headroom(
    depth: np.ndarray,
    front_headroom: float,
    back_headroom: float,
) -> np.ndarray:
    """Place the source surface inside the depth envelope before anatomy fitting.

    The source depth often already touches 0 and 1. A face/head prior added to
    that range is clipped at the envelope, flattening the nose or the back of
    the skull. Reserving both sides first gives the fitted anatomy signed room
    to move while preserving every relative depth value in the source.
    """
    if front_headroom < 0 or back_headroom < 0:
        raise ValueError("Front and back headroom must be non-negative.")
    active_span = 1.0 - front_headroom - back_headroom
    if active_span <= 0:
        raise ValueError("Front and back headroom must add up to less than 1.0.")
    return back_headroom + np.clip(depth, 0.0, 1.0) * active_span


def load_correspondence(path: Path) -> tuple[np.ndarray, np.ndarray]:
    rows = np.loadtxt(path, dtype=np.float64)
    if rows.shape != (468, 6):
        raise ValueError(f"Expected a 468x6 GNM correspondence, got {rows.shape}.")
    indices = rows[:, (0, 2, 4)].astype(np.int64)
    weights = rows[:, (1, 3, 5)].astype(np.float32)
    if not np.allclose(weights.sum(axis=1), 1.0, atol=2e-5):
        raise ValueError("GNM correspondence barycentric weights do not sum to one.")
    return indices, weights


def euler_rotation(angles: torch.Tensor) -> torch.Tensor:
    """Return differentiable XYZ Euler rotation matrix."""
    pitch, yaw, roll = angles.unbind()
    one = torch.ones((), dtype=angles.dtype, device=angles.device)
    zero = torch.zeros((), dtype=angles.dtype, device=angles.device)
    cx, sx = torch.cos(pitch), torch.sin(pitch)
    cy, sy = torch.cos(yaw), torch.sin(yaw)
    cz, sz = torch.cos(roll), torch.sin(roll)
    rotate_x = torch.stack((one, zero, zero, zero, cx, -sx, zero, sx, cx)).reshape(3, 3)
    rotate_y = torch.stack((cy, zero, sy, zero, one, zero, -sy, zero, cy)).reshape(3, 3)
    rotate_z = torch.stack((cz, -sz, zero, sz, cz, zero, zero, zero, one)).reshape(3, 3)
    return rotate_z @ rotate_y @ rotate_x


def embedded_values(values: torch.Tensor, indices: torch.Tensor, weights: torch.Tensor) -> torch.Tensor:
    """Evaluate a vertex array or basis at the 468 barycentric anchors."""
    if values.ndim == 2:
        return (values[indices] * weights[..., None]).sum(dim=1)
    return (values[:, indices, :] * weights[None, ..., None]).sum(dim=2)


def fit_one_face(
    model: object,
    correspondence_indices: np.ndarray,
    correspondence_weights: np.ndarray,
    landmarks: np.ndarray,
    face_box: np.ndarray,
    device: torch.device,
    camera_steps: int,
    shape_steps: int,
) -> FitResult:
    """Fit GNM identity/expression and an orthographic camera to one face."""
    indices = torch.as_tensor(correspondence_indices, dtype=torch.long, device=device)
    weights = torch.as_tensor(correspondence_weights, dtype=torch.float32, device=device)
    template = model.template_vertex_positions.to(device)
    identity_basis = model.vertex_identity_basis[:170].to(device)
    expression_basis = model.expression_basis[:350].to(device)
    template_landmarks = embedded_values(template, indices, weights)
    identity_landmarks = embedded_values(identity_basis, indices, weights)
    expression_landmarks = embedded_values(expression_basis, indices, weights)

    x1, y1, x2, y2 = face_box.astype(np.float64)
    face_width = max(1.0, x2 - x1)
    center = np.array([(x1 + x2) / 2.0, (y1 + y2) / 2.0], dtype=np.float32)
    target_xy = np.stack(
        (
            (landmarks[:, 0] - center[0]) / face_width,
            -(landmarks[:, 1] - center[1]) / face_width,
        ),
        axis=1,
    ).astype(np.float32)
    target_z = (-landmarks[:, 2]).astype(np.float32)
    target_z -= np.median(target_z)
    target_xy_tensor = torch.as_tensor(target_xy, device=device)
    target_z_tensor = torch.as_tensor(target_z, device=device)

    source_range = float(torch.quantile(template_landmarks[:, 0], 0.98) - torch.quantile(template_landmarks[:, 0], 0.02))
    target_range = float(np.quantile(target_xy[:, 0], 0.98) - np.quantile(target_xy[:, 0], 0.02))
    initial_scale = max(0.1, target_range / max(source_range, 1e-5))
    log_scale = torch.nn.Parameter(torch.tensor(math.log(initial_scale), device=device))
    translation = torch.nn.Parameter(target_xy_tensor.mean(dim=0) - initial_scale * template_landmarks[:, :2].mean(dim=0))
    angles = torch.nn.Parameter(torch.zeros(3, device=device))
    identity = torch.nn.Parameter(torch.zeros(170, device=device))
    expression = torch.nn.Parameter(torch.zeros(350, device=device))

    # Oval, eyes, nose, and mouth all contribute; the outer oval gets slightly
    # more weight because it carries cheek, chin, and skull-scale information.
    landmark_weights = torch.ones(468, device=device)
    landmark_weights[torch.as_tensor((10, 21, 54, 58, 67, 93, 127, 132, 136, 148, 152, 172, 176, 234, 251, 284, 288, 297, 323, 356, 361, 365, 377, 389, 397, 454), device=device)] = 1.8

    def predict() -> tuple[torch.Tensor, torch.Tensor]:
        local = template_landmarks + torch.einsum("i,ijk->jk", identity, identity_landmarks)
        local = local + torch.einsum("i,ijk->jk", expression, expression_landmarks)
        rotated = local @ euler_rotation(angles).T
        scale = torch.exp(log_scale)
        return scale * rotated[:, :2] + translation, scale * rotated[:, 2]

    def objective(allow_shape: bool) -> torch.Tensor:
        prediction_xy, prediction_z = predict()
        xy_error = functional.smooth_l1_loss(
            prediction_xy,
            target_xy_tensor,
            reduction="none",
            beta=0.012,
        ).sum(dim=1)
        prediction_z = prediction_z - torch.median(prediction_z)
        z_error = functional.smooth_l1_loss(
            prediction_z,
            target_z_tensor,
            reduction="none",
            beta=0.018,
        )
        loss = (xy_error * landmark_weights).mean() + 0.12 * z_error.mean()
        if allow_shape:
            loss = loss + 0.0015 * identity.square().mean() + 0.004 * expression.square().mean()
        return loss + 0.0002 * angles.square().mean()

    camera_optimizer = torch.optim.Adam((log_scale, translation, angles), lr=0.025)
    for _ in range(camera_steps):
        camera_optimizer.zero_grad(set_to_none=True)
        loss = objective(False)
        loss.backward()
        camera_optimizer.step()
        with torch.no_grad():
            angles.clamp_(-1.25, 1.25)

    shape_optimizer = torch.optim.Adam(
        (
            {"params": (log_scale, translation, angles), "lr": 0.006},
            {"params": (identity,), "lr": 0.035},
            {"params": (expression,), "lr": 0.025},
        )
    )
    for _ in range(shape_steps):
        shape_optimizer.zero_grad(set_to_none=True)
        loss = objective(True)
        loss.backward()
        shape_optimizer.step()
        with torch.no_grad():
            identity.clamp_(-3.0, 3.0)
            expression.clamp_(-3.0, 3.0)
            angles.clamp_(-1.25, 1.25)

    with torch.no_grad():
        vertices = template + torch.einsum("i,ijk->jk", identity, identity_basis)
        vertices = vertices + torch.einsum("i,ijk->jk", expression, expression_basis)
        fitted_xy, _ = predict()
        final_loss = float(objective(True))
        rotation = euler_rotation(angles).detach().cpu().numpy()
        scale = float(torch.exp(log_scale))
        translation_value = translation.detach().cpu().numpy()
        identity_rms = float(torch.sqrt(identity.square().mean()))
        expression_rms = float(torch.sqrt(expression.square().mean()))

    skin_group_index = list(model.vertex_group_names).index("skin_exterior")
    skin_indices = np.flatnonzero(
        (model.vertex_groups[skin_group_index] > 1e-4).detach().cpu().numpy()
    ).astype(np.int64)
    return FitResult(
        vertices=vertices.detach().cpu().numpy(),
        triangles=np.asarray(model.triangles.detach().cpu(), dtype=np.int64),
        skin_indices=skin_indices,
        rotation=rotation,
        scale=scale,
        translation=translation_value,
        fitted_landmarks_normalized=fitted_xy.detach().cpu().numpy(),
        loss=final_loss,
        identity_rms=identity_rms,
        expression_rms=expression_rms,
    )


def vertex_normals(vertices: np.ndarray, triangles: np.ndarray) -> np.ndarray:
    normals = np.zeros_like(vertices, dtype=np.float64)
    edges_a = vertices[triangles[:, 1]] - vertices[triangles[:, 0]]
    edges_b = vertices[triangles[:, 2]] - vertices[triangles[:, 0]]
    face_normals = np.cross(edges_a, edges_b)
    for corner in range(3):
        np.add.at(normals, triangles[:, corner], face_normals)
    lengths = np.linalg.norm(normals, axis=1, keepdims=True)
    return normals / np.maximum(lengths, 1e-10)


def rasterize_head_prior(
    fit: FitResult,
    face_box: np.ndarray,
    image_shape: tuple[int, int],
) -> tuple[np.ndarray, np.ndarray]:
    """Rasterize the visible exterior GNM triangles into an image-space prior.

    A point-cloud Delaunay interpolation can bridge unrelated samples across
    the mouth, the profile, or two touching heads.  Rasterizing the original
    GNM topology and keeping the nearest triangle gives us a real projected
    surface instead of a convex sheet stretched between visible vertices.
    """
    image_height, image_width = image_shape
    x1, y1, x2, y2 = face_box.astype(np.float64)
    box_width = max(1.0, x2 - x1)
    center_x, center_y = (x1 + x2) / 2.0, (y1 + y2) / 2.0
    rotated = fit.vertices @ fit.rotation.T
    projected = np.empty((len(rotated), 2), dtype=np.float32)
    projected[:, 0] = center_x + box_width * (
        fit.scale * rotated[:, 0] + fit.translation[0]
    )
    projected[:, 1] = center_y - box_width * (
        fit.scale * rotated[:, 1] + fit.translation[1]
    )
    projected_z = (fit.scale * rotated[:, 2]).astype(np.float32)

    is_skin = np.zeros(len(rotated), dtype=bool)
    is_skin[fit.skin_indices] = True
    triangles = fit.triangles[np.all(is_skin[fit.triangles], axis=1)]
    if len(triangles) < 100:
        raise RuntimeError("GNM skin exterior contains too few triangles.")

    # The fitted camera looks along +Z. Cull back-facing triangles before the
    # z-buffer so the back of the skull cannot overwrite cheeks or the nose.
    edge_a = rotated[triangles[:, 1]] - rotated[triangles[:, 0]]
    edge_b = rotated[triangles[:, 2]] - rotated[triangles[:, 0]]
    face_normal_z = np.cross(edge_a, edge_b)[:, 2]
    triangles = triangles[face_normal_z > 1e-9]

    z_buffer = np.full((image_height, image_width), -np.inf, dtype=np.float32)
    epsilon = 1e-5
    for triangle in triangles:
        xy = projected[triangle]
        z = projected_z[triangle]
        min_x = max(0, int(np.floor(xy[:, 0].min())))
        max_x = min(image_width - 1, int(np.ceil(xy[:, 0].max())))
        min_y = max(0, int(np.floor(xy[:, 1].min())))
        max_y = min(image_height - 1, int(np.ceil(xy[:, 1].max())))
        if min_x > max_x or min_y > max_y:
            continue

        x0, y0 = xy[0]
        x1p, y1p = xy[1]
        x2p, y2p = xy[2]
        denominator = (y1p - y2p) * (x0 - x2p) + (x2p - x1p) * (y0 - y2p)
        if abs(float(denominator)) < epsilon:
            continue
        grid_y, grid_x = np.mgrid[min_y : max_y + 1, min_x : max_x + 1]
        sample_x = grid_x.astype(np.float32) + 0.5
        sample_y = grid_y.astype(np.float32) + 0.5
        weight_0 = (
            (y1p - y2p) * (sample_x - x2p)
            + (x2p - x1p) * (sample_y - y2p)
        ) / denominator
        weight_1 = (
            (y2p - y0) * (sample_x - x2p)
            + (x0 - x2p) * (sample_y - y2p)
        ) / denominator
        weight_2 = 1.0 - weight_0 - weight_1
        inside = (
            (weight_0 >= -epsilon)
            & (weight_1 >= -epsilon)
            & (weight_2 >= -epsilon)
        )
        if not inside.any():
            continue
        triangle_z = weight_0 * z[0] + weight_1 * z[1] + weight_2 * z[2]
        local = z_buffer[min_y : max_y + 1, min_x : max_x + 1]
        update = inside & (triangle_z > local)
        local[update] = triangle_z[update]

    mask = np.isfinite(z_buffer)
    if mask.sum() < 100:
        raise RuntimeError("GNM triangle rasterizer produced an empty head prior.")

    # GNM HEAD is a complete character asset: eyeballs, teeth, and tongue are
    # separate geometry, so the skin mesh intentionally has openings around
    # the eyes, nostrils, and mouth.  A single-sheet 2.5D relief cannot keep
    # those topology holes. Fill only background islands fully enclosed by the
    # projected skin silhouette; the photograph's source_detail then restores
    # eyelids, nostrils, lips, moustache, and beard on the continuous base.
    inverse = (~mask).astype(np.uint8)
    padded = cv2.copyMakeBorder(inverse, 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=1)
    exterior = padded.copy()
    cv2.floodFill(exterior, None, (0, 0), 2)
    enclosed_holes = exterior[1:-1, 1:-1] == 1
    if enclosed_holes.any():
        safe_depth = z_buffer.copy()
        safe_depth[~mask] = 0.0
        radius = max(3.0, min(18.0, box_width * 0.022))
        safe_depth = cv2.inpaint(
            safe_depth,
            enclosed_holes.astype(np.uint8) * 255,
            radius,
            cv2.INPAINT_NS,
        )
        z_buffer[enclosed_holes] = safe_depth[enclosed_holes]
        mask |= enclosed_holes

    prior = z_buffer
    prior[~mask] = np.nan
    return prior, mask.astype(np.uint8)


def export_obj(path: Path, vertices: np.ndarray, triangles: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Fitted Google GNM Head v3; units are metres.\n"]
    lines.extend(f"v {x:.8f} {y:.8f} {z:.8f}\n" for x, y, z in vertices)
    lines.extend(f"f {a + 1} {b + 1} {c + 1}\n" for a, b, c in triangles)
    path.write_text("".join(lines), encoding="utf-8")


def save_prior_preview(path: Path, prior: np.ndarray) -> None:
    valid = np.isfinite(prior)
    preview = np.zeros(prior.shape, dtype=np.uint8)
    if valid.any():
        low, high = np.percentile(prior[valid], (1.0, 99.0))
        normalized = np.clip((prior - low) / max(high - low, 1e-6), 0.0, 1.0)
        preview[valid] = np.round(normalized[valid] * 255.0).astype(np.uint8)
    Image.fromarray(preview, mode="L").save(path)


def main() -> int:
    args = parse_args()
    args.qa_dir.mkdir(parents=True, exist_ok=True)
    metadata = json.loads(args.faces.read_text(encoding="utf-8"))
    face_rows = metadata.get("faces", [])
    for row in face_rows:
        if len(row.get("dense_landmarks_468", [])) != 468:
            raise ValueError("Every face requires exactly 468 dense landmarks.")

    depth_image = np.asarray(Image.open(args.depth), dtype=np.float32)
    if depth_image.ndim != 2:
        raise ValueError("Depth input must be one-channel 16-bit PNG.")
    input_depth = depth_image / 65535.0
    photo = Image.open(args.photo).convert("RGBA")
    if photo.size != (input_depth.shape[1], input_depth.shape[0]):
        raise ValueError(
            f"Photo {photo.size} does not match depth "
            f"{(input_depth.shape[1], input_depth.shape[0])}."
        )
    alpha = np.asarray(photo, dtype=np.uint8)[..., 3] > 8

    if not face_rows:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(depth_image.astype(np.uint16)).save(args.output)
        report = {
            "head_refinement_complete": True,
            "head_refinement_required": False,
            "backend": "pass-through-no-human-faces",
            "depth_input": str(args.depth),
            "faces_input": str(args.faces),
            "output": str(args.output),
            "faces": [],
        }
        args.output.with_suffix(".json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"GNM_HEAD_REFINE_OK faces=0 pass-through output={args.output.resolve()}")
        return 0

    depth = centre_depth_with_headroom(
        input_depth,
        args.front_headroom,
        args.back_headroom,
    )
    centred_u16 = np.round(depth * 65535.0).astype(np.uint16)
    Image.fromarray(centred_u16, mode="I;16").save(args.qa_dir / "depth-centred-headroom.png")

    correspondence_indices, correspondence_weights = load_correspondence(args.correspondence)
    sys.path.insert(0, str(args.gnm_root.resolve()))
    from gnm.shape import gnm_pytorch

    device_name = "cuda" if args.device == "auto" and torch.cuda.is_available() else args.device
    if device_name == "auto":
        device_name = "cpu"
    device = torch.device(device_name)
    model = gnm_pytorch.GNM.from_local(
        version=gnm_pytorch.GNMMajorVersion.V3,
        variant=gnm_pytorch.GNMVariant.HEAD,
    ).to(device)

    fused = depth.copy()
    source_low = cv2.GaussianBlur(depth, (0, 0), args.detail_sigma)
    source_detail = depth - source_low
    combined_prior = np.full(depth.shape, np.nan, dtype=np.float32)
    overlay = photo.convert("RGB")
    drawing = ImageDraw.Draw(overlay)
    face_reports: list[dict[str, object]] = []

    for face_index, row in enumerate(face_rows, start=1):
        landmarks = np.asarray(row["dense_landmarks_468"], dtype=np.float32)
        face_box = np.asarray(row["box"], dtype=np.float32)
        fit = fit_one_face(
            model,
            correspondence_indices,
            correspondence_weights,
            landmarks,
            face_box,
            device,
            args.camera_steps,
            args.shape_steps,
        )
        prior, prior_mask = rasterize_head_prior(fit, face_box, depth.shape)
        prior_mask = (prior_mask > 0) & alpha
        values = prior[prior_mask]
        if values.size < 100:
            raise RuntimeError(f"Face {face_index} produced an empty head prior.")
        low, high = np.percentile(values, (1.0, 99.0))
        prior_normalized = np.clip((prior - low) / max(high - low, 1e-6), 0.0, 1.0)
        current_median = float(np.median(source_low[prior_mask]))
        prior_median = float(np.median(prior_normalized[prior_mask]))
        candidate = current_median + (prior_normalized - prior_median) * args.head_span + source_detail
        candidate[~prior_mask] = fused[~prior_mask]

        distance = cv2.distanceTransform(prior_mask.astype(np.uint8), cv2.DIST_L2, 5)
        blend = np.clip(distance / max(args.feather, 1.0), 0.0, 1.0)
        blend *= prior_mask.astype(np.float32)
        fused = fused * (1.0 - blend) + np.clip(candidate, 0.0, 1.0) * blend
        replace = prior_mask & (~np.isfinite(combined_prior) | (prior > combined_prior))
        combined_prior[replace] = prior[replace]

        x1, y1, x2, y2 = face_box
        box_width = max(1.0, x2 - x1)
        center_x, center_y = (x1 + x2) / 2.0, (y1 + y2) / 2.0
        fitted_pixels = np.stack(
            (
                center_x + box_width * fit.fitted_landmarks_normalized[:, 0],
                center_y - box_width * fit.fitted_landmarks_normalized[:, 1],
            ),
            axis=1,
        )
        for x, y, _z in landmarks:
            drawing.ellipse((x - 1, y - 1, x + 1, y + 1), fill=(0, 230, 255))
        for x, y in fitted_pixels:
            drawing.ellipse((x - 1, y - 1, x + 1, y + 1), fill=(255, 145, 0))
        export_obj(args.qa_dir / f"face-{face_index:02d}-gnm-fitted.obj", fit.vertices, fit.triangles)
        face_reports.append(
            {
                "index": face_index,
                "fit_loss": fit.loss,
                "identity_rms": fit.identity_rms,
                "expression_rms": fit.expression_rms,
                "scale": fit.scale,
                "translation": fit.translation.tolist(),
                "rotation": fit.rotation.tolist(),
                "prior_pixels": int(prior_mask.sum()),
            }
        )
        print(
            f"[gnm] face {face_index}/{len(face_rows)} loss={fit.loss:.6f} "
            f"identity_rms={fit.identity_rms:.3f} expression_rms={fit.expression_rms:.3f}"
        )

    # A cut-out surface whose boundary keeps arbitrary face/head depth becomes
    # a comb of horizontal spikes in side view. Ease the last few foreground
    # pixels to one robust back-plane value while leaving interior hair and
    # beard detail untouched.
    if args.silhouette_taper > 0:
        alpha_distance = cv2.distanceTransform(alpha.astype(np.uint8), cv2.DIST_L2, 5)
        edge_weight = np.clip(alpha_distance / args.silhouette_taper, 0.0, 1.0)
        edge_weight = edge_weight * edge_weight * (3.0 - 2.0 * edge_weight)
        back_plane = float(np.percentile(fused[alpha], 2.0))
        fused[alpha] = back_plane * (1.0 - edge_weight[alpha]) + fused[alpha] * edge_weight[alpha]

    output_u16 = np.round(np.clip(fused, 0.0, 1.0) * 65535.0).astype(np.uint16)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(output_u16, mode="I;16").save(args.output)
    overlay.save(args.qa_dir / "gnm-landmark-fit.png")
    save_prior_preview(args.qa_dir / "gnm-head-prior.png", combined_prior)
    comparison = Image.new("RGB", (depth.shape[1] * 3, depth.shape[0]))
    comparison.paste(Image.fromarray(np.round(depth * 255.0).astype(np.uint8), mode="L").convert("RGB"), (0, 0))
    prior_preview = Image.open(args.qa_dir / "gnm-head-prior.png").convert("RGB")
    comparison.paste(prior_preview, (depth.shape[1], 0))
    comparison.paste(Image.fromarray(np.round(np.clip(fused, 0.0, 1.0) * 255.0).astype(np.uint8), mode="L").convert("RGB"), (depth.shape[1] * 2, 0))
    comparison.save(args.qa_dir / "depth-before-prior-after.png")

    report = {
        "head_refinement_complete": True,
        "head_refinement_required": True,
        "backend": "google-gnm-head-v3-mediapipe-468",
        "depth_input": str(args.depth),
        "faces_input": str(args.faces),
        "output": str(args.output),
        "device": str(device),
        "settings": {
            "head_span": args.head_span,
            "front_headroom": args.front_headroom,
            "back_headroom": args.back_headroom,
            "active_source_span": 1.0 - args.front_headroom - args.back_headroom,
            "detail_sigma": args.detail_sigma,
            "feather": args.feather,
            "silhouette_taper": args.silhouette_taper,
            "camera_steps": args.camera_steps,
            "shape_steps": args.shape_steps,
        },
        "faces": face_reports,
    }
    args.output.with_suffix(".json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"GNM_HEAD_REFINE_OK faces={len(face_rows)} device={device} output={args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
