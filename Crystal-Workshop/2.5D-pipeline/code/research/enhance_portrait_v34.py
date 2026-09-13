"""
File: code/research/enhance_portrait_v34.py
Purpose:
 - Add source-aligned facial micro-relief, open eyeglass-frame geometry, and a
   shallow hair silhouette shell to an existing layered HRN + MoGe portrait.
 - Constrain the result to a measured Cockpit3D-like depth-to-height envelope.
 - Preserve every v3.3 input and write a separate, auditable v3.4 scene.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import trimesh
from PIL import Image
from scipy.ndimage import distance_transform_edt

CODE_DIR = Path(__file__).resolve().parents[1]
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

from face_landmarks import DenseFaceLandmarks, detect_dense_faces  # noqa: E402

from compose_hrn_direct_moge_portrait import (  # noqa: E402
    build_grid_faces,
    rasterize_patch_depth,
    rasterize_patch_footprint,
    resize_grid_shape,
    sample_nearest,
    scene_xy_to_source_pixels,
)
from fuse_hrn_moge_portrait_depth import largest_alpha_component  # noqa: E402
from source_camera_fusion import sample_source_colors, source_pixels_to_scene  # noqa: E402


FACE_OVAL = (
    10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365,
    379, 378, 400, 377, 152, 148, 176, 149, 150, 136, 172, 58, 132, 93,
    234, 127, 162, 21, 54, 103, 67, 109,
)
LEFT_EYE = (33, 133, 159, 145)
RIGHT_EYE = (362, 263, 386, 374)


@dataclass(frozen=True)
class FramePath:
    """One source-pixel path used to create a narrow raised ribbon."""

    name: str
    points: np.ndarray
    closed: bool


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--input-glb", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--target-depth-height-ratio", type=float, default=0.227)
    parser.add_argument("--detail-amplitude", type=float, default=0.0015)
    parser.add_argument("--frame-rise", type=float, default=0.016)
    parser.add_argument("--frame-width-px", type=float, default=3.2)
    parser.add_argument("--frame-backfill-rings", type=int, default=6)
    parser.add_argument("--hair-grid-long-edge", type=int, default=500)
    parser.add_argument("--hair-recess", type=float, default=0.012)
    return parser.parse_args()


def smoothstep(values: np.ndarray) -> np.ndarray:
    values = np.clip(values, 0.0, 1.0)
    return values * values * (3.0 - 2.0 * values)


def find_node_geometry(scene: trimesh.Scene, node_name: str) -> str:
    flattened = scene.graph.to_flattened()
    if node_name not in flattened:
        raise KeyError(f"Required scene node is missing: {node_name}")
    transform = np.asarray(flattened[node_name]["transform"], dtype=np.float64)
    if not np.allclose(transform, np.eye(4), atol=1e-7):
        raise ValueError(f"{node_name} must have an identity transform for v3.4")
    return str(flattened[node_name]["geometry"])


def apply_depth_envelope(
    meshes: list[trimesh.Trimesh], target_depth: float
) -> dict[str, float]:
    """Compress all depth behind the existing front plane without flattening XY."""

    if target_depth <= 0.0:
        raise ValueError("Target depth must be positive")
    front = max(float(mesh.vertices[:, 2].max()) for mesh in meshes)
    back = min(float(mesh.vertices[:, 2].min()) for mesh in meshes)
    original_depth = front - back
    scale = min(1.0, target_depth / max(original_depth, 1e-9))
    for mesh in meshes:
        vertices = np.asarray(mesh.vertices).copy()
        vertices[:, 2] = front - (front - vertices[:, 2]) * scale
        mesh.vertices = vertices
    return {
        "front_anchor": front,
        "original_depth": original_depth,
        "target_depth": target_depth,
        "applied_scale": scale,
        "result_depth": original_depth * scale,
    }


def eye_geometry(points: np.ndarray, indices: tuple[int, ...]) -> dict[str, object]:
    selected = points[np.asarray(indices), :2]
    left = selected[np.argmin(selected[:, 0])]
    right = selected[np.argmax(selected[:, 0])]
    top = selected[np.argmin(selected[:, 1])]
    bottom = selected[np.argmax(selected[:, 1])]
    centre = selected.mean(axis=0)
    angle = float(np.arctan2(right[1] - left[1], right[0] - left[0]))
    return {
        "centre": centre,
        "width": float(np.linalg.norm(right - left)),
        "height": float(max(4.0, bottom[1] - top[1])),
        "angle": angle,
    }


def superellipse_points(
    centre: np.ndarray,
    radius_x: float,
    radius_y: float,
    exponent: float,
    angle: float,
    count: int = 112,
) -> np.ndarray:
    """Return a rounded-rectangle/ellipse contour in source-pixel coordinates."""

    theta = np.linspace(0.0, 2.0 * np.pi, count, endpoint=False)
    power = 2.0 / exponent
    local_x = radius_x * np.sign(np.cos(theta)) * np.abs(np.cos(theta)) ** power
    local_y = radius_y * np.sign(np.sin(theta)) * np.abs(np.sin(theta)) ** power
    cosine = np.cos(angle)
    sine = np.sin(angle)
    columns = centre[0] + local_x * cosine - local_y * sine
    rows = centre[1] + local_x * sine + local_y * cosine
    return np.column_stack((columns, rows))


def bilinear_sample(values: np.ndarray, points: np.ndarray) -> np.ndarray:
    height, width = values.shape
    x = np.clip(points[:, 0], 0.0, width - 1.0)
    y = np.clip(points[:, 1], 0.0, height - 1.0)
    x0 = np.floor(x).astype(np.int64)
    y0 = np.floor(y).astype(np.int64)
    x1 = np.minimum(x0 + 1, width - 1)
    y1 = np.minimum(y0 + 1, height - 1)
    wx = x - x0
    wy = y - y0
    return (
        values[y0, x0] * (1.0 - wx) * (1.0 - wy)
        + values[y0, x1] * wx * (1.0 - wy)
        + values[y1, x0] * (1.0 - wx) * wy
        + values[y1, x1] * wx * wy
    )


def score_frame_candidate(
    gray: np.ndarray, gradient: np.ndarray, contour: np.ndarray
) -> float:
    darkness = 1.0 - bilinear_sample(gray, contour)
    edge = bilinear_sample(gradient, contour)
    return float(np.mean(0.62 * edge + 0.38 * darkness))


def fit_lens_path(
    gray: np.ndarray,
    gradient: np.ndarray,
    geometry: dict[str, object],
) -> tuple[np.ndarray, dict[str, float]]:
    """Select the source-supported rounded lens contour around one landmark eye."""

    centre = np.asarray(geometry["centre"], dtype=np.float64)
    eye_width = float(geometry["width"])
    eye_height = float(geometry["height"])
    angle = float(geometry["angle"])
    best: tuple[float, np.ndarray, dict[str, float]] | None = None
    # Eyelids are strong dark edges, so an unconstrained edge maximisation can
    # collapse onto the eye itself. Keep the search inside realistic spectacle
    # proportions and use the source score only to refine that anatomical prior.
    for radius_x_factor in (0.90, 1.00, 1.10):
        for radius_y_factor in (2.40, 2.80, 3.20):
            for centre_y_factor in (0.65, 0.85, 1.05):
                for exponent in (2.0, 3.0, 4.0):
                    candidate_centre = centre + np.array(
                        [0.0, eye_height * centre_y_factor]
                    )
                    contour = superellipse_points(
                        candidate_centre,
                        eye_width * radius_x_factor,
                        eye_height * radius_y_factor,
                        exponent,
                        angle,
                    )
                    source_score = score_frame_candidate(gray, gradient, contour)
                    prior_penalty = (
                        0.07 * abs(radius_x_factor - 1.0)
                        + 0.055 * abs(radius_y_factor - 2.8)
                        + 0.045 * abs(centre_y_factor - 0.85)
                    )
                    score = source_score - prior_penalty
                    parameters = {
                        "score": score,
                        "source_score": source_score,
                        "prior_penalty": prior_penalty,
                        "radius_x": eye_width * radius_x_factor,
                        "radius_y": eye_height * radius_y_factor,
                        "centre_x": float(candidate_centre[0]),
                        "centre_y": float(candidate_centre[1]),
                        "angle_degrees": float(np.degrees(angle)),
                        "superellipse_exponent": exponent,
                    }
                    if best is None or score > best[0]:
                        best = (score, contour, parameters)
    assert best is not None
    return best[1], best[2]


def quadratic_path(start: np.ndarray, control: np.ndarray, end: np.ndarray, count: int) -> np.ndarray:
    t = np.linspace(0.0, 1.0, count)[:, None]
    return (1.0 - t) ** 2 * start + 2.0 * (1.0 - t) * t * control + t**2 * end


def fit_eyeglass_paths(
    source_rgb: np.ndarray, landmarks: DenseFaceLandmarks
) -> tuple[list[FramePath], dict[str, object], np.ndarray]:
    """Fit two open lenses, their bridge, and visible temple arms to the source."""

    points = np.asarray(landmarks.core, dtype=np.float64)
    gray = cv2.cvtColor(source_rgb, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
    blurred = cv2.GaussianBlur(gray, (0, 0), 1.2)
    gx = cv2.Sobel(blurred, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(blurred, cv2.CV_32F, 0, 1, ksize=3)
    gradient = np.hypot(gx, gy)
    gradient /= max(float(np.percentile(gradient, 99.0)), 1e-6)
    gradient = np.clip(gradient, 0.0, 1.0)

    left_contour, left_stats = fit_lens_path(
        gray, gradient, eye_geometry(points, LEFT_EYE)
    )
    right_contour, right_stats = fit_lens_path(
        gray, gradient, eye_geometry(points, RIGHT_EYE)
    )

    left_inner = left_contour[np.argmax(left_contour[:, 0])]
    right_inner = right_contour[np.argmin(right_contour[:, 0])]
    bridge_control = np.array(
        [
            (left_inner[0] + right_inner[0]) * 0.5,
            min(left_inner[1], right_inner[1])
            - 0.11 * (left_stats["radius_y"] + right_stats["radius_y"]),
        ]
    )
    bridge = quadratic_path(left_inner, bridge_control, right_inner, 28)

    face_x1, _face_y1, face_x2, _face_y2 = landmarks.bounds
    left_outer = left_contour[np.argmin(left_contour[:, 0])]
    right_outer = right_contour[np.argmax(right_contour[:, 0])]
    left_end = np.array([max(0.0, face_x1 - 0.025 * (face_x2 - face_x1)), left_outer[1]])
    right_end = np.array([min(source_rgb.shape[1] - 1.0, face_x2 + 0.025 * (face_x2 - face_x1)), right_outer[1]])
    left_arm = quadratic_path(
        left_outer,
        (left_outer + left_end) * 0.5 + np.array([0.0, -2.0]),
        left_end,
        22,
    )
    right_arm = quadratic_path(
        right_outer,
        (right_outer + right_end) * 0.5 + np.array([0.0, -2.0]),
        right_end,
        22,
    )

    paths = [
        FramePath("left-lens", left_contour, True),
        FramePath("right-lens", right_contour, True),
        FramePath("bridge", bridge, False),
        FramePath("left-temple", left_arm, False),
        FramePath("right-temple", right_arm, False),
    ]
    overlay = source_rgb.copy()
    for path in paths:
        cv2.polylines(
            overlay,
            [np.rint(path.points).astype(np.int32)],
            path.closed,
            (255, 128, 0),
            3,
            cv2.LINE_AA,
        )
    return paths, {"left_lens": left_stats, "right_lens": right_stats}, overlay


def build_source_detail_field(
    source_rgb: np.ndarray, landmarks: DenseFaceLandmarks
) -> tuple[np.ndarray, np.ndarray, dict[str, float]]:
    """Build bounded source-luminance micro-relief inside skin-safe face regions."""

    height, width = source_rgb.shape[:2]
    points = np.asarray(landmarks.core, dtype=np.float64)
    face_width = landmarks.bounds[2] - landmarks.bounds[0]
    gray = cv2.cvtColor(source_rgb, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
    fine = cv2.GaussianBlur(gray, (0, 0), max(1.2, face_width * 0.008))
    coarse = cv2.GaussianBlur(gray, (0, 0), max(2.4, face_width * 0.025))
    band = fine - coarse

    skin = np.zeros((height, width), dtype=np.uint8)
    cv2.fillPoly(skin, [np.rint(points[list(FACE_OVAL), :2]).astype(np.int32)], 255)
    for indices in (LEFT_EYE, RIGHT_EYE):
        geometry = eye_geometry(points, indices)
        centre = tuple(np.rint(geometry["centre"]).astype(int))
        axes = (
            max(2, int(round(float(geometry["width"]) * 1.16))),
            max(2, int(round(float(geometry["height"]) * 2.7))),
        )
        cv2.ellipse(skin, centre, axes, np.degrees(float(geometry["angle"])), 0, 360, 0, -1)

    skin_bool = skin > 0
    if not skin_bool.any():
        raise RuntimeError("Face detail mask is empty")
    band = cv2.GaussianBlur(band, (0, 0), max(0.8, face_width * 0.004))
    robust_scale = max(float(np.percentile(np.abs(band[skin_bool]), 95.0)), 1e-4)
    field = np.clip(band / robust_scale, -1.0, 1.0)
    inward = cv2.distanceTransform(skin, cv2.DIST_L2, 5)
    feather = smoothstep(inward / max(face_width * 0.045, 1.0))
    field *= feather
    field[~skin_bool] = 0.0
    return field.astype(np.float32), skin_bool, {
        "face_width_px": float(face_width),
        "robust_bandpass_scale": robust_scale,
        "active_pixels": int(skin_bool.sum()),
    }


def fill_patch_depth(depth: np.ndarray, mask: np.ndarray) -> np.ndarray:
    if not mask.any():
        raise RuntimeError("HRN depth footprint is empty")
    _distance, nearest = distance_transform_edt(~mask, return_indices=True)
    return depth[tuple(nearest)]


def build_ribbon_mesh(
    paths: list[FramePath],
    face_depth: np.ndarray,
    source_rgb: np.ndarray,
    width_px: float,
    rise: float,
    rings: int,
) -> tuple[trimesh.Trimesh, dict[str, int]]:
    """Create tapered raised ribbons with a multi-ring face-to-frame backfill."""

    if rings < 3 or rings > 8:
        raise ValueError("Eyeglass backfill must use between 3 and 8 rings")
    if width_px <= 0.0 or rise <= 0.0:
        raise ValueError("Eyeglass width and rise must be positive")
    source_size = (source_rgb.shape[1], source_rgb.shape[0])
    luma = cv2.cvtColor(source_rgb, cv2.COLOR_RGB2GRAY)
    luma_rgb = np.repeat(luma[:, :, None], 3, axis=2)
    meshes: list[trimesh.Trimesh] = []
    total_segments = 0

    for path in paths:
        points = np.asarray(path.points, dtype=np.float64)
        previous = np.roll(points, 1, axis=0)
        following = np.roll(points, -1, axis=0)
        if not path.closed:
            previous[0] = points[0]
            following[-1] = points[-1]
        tangents = following - previous
        tangent_length = np.linalg.norm(tangents, axis=1, keepdims=True)
        tangents /= np.maximum(tangent_length, 1e-6)
        normals = np.column_stack((-tangents[:, 1], tangents[:, 0]))
        base_depth = bilinear_sample(face_depth, points)
        ring_vertices = []
        ring_pixels = []
        for ring_index in range(rings):
            fraction = ring_index / (rings - 1)
            eased = float(smoothstep(np.asarray(fraction)))
            half_width = width_px * (0.22 + 0.78 * eased) * 0.5
            sides = np.stack(
                (points - normals * half_width, points + normals * half_width), axis=1
            )
            scene_xy = source_pixels_to_scene(sides.reshape(-1, 2), source_size)
            z = np.repeat(base_depth + rise * eased, 2)
            ring_vertices.append(np.column_stack((scene_xy, z)))
            ring_pixels.append(sides.reshape(-1, 2))
        vertices = np.concatenate(ring_vertices, axis=0)
        pixels = np.concatenate(ring_pixels, axis=0)
        vertex_colours = sample_source_colors(luma_rgb, pixels)
        count = len(points)
        segment_count = count if path.closed else count - 1
        faces: list[tuple[int, int, int]] = []

        def vertex(level: int, point: int, side: int) -> int:
            return level * count * 2 + (point % count) * 2 + side

        for level in range(rings - 1):
            for index in range(segment_count):
                following_index = (index + 1) % count
                for side in (0, 1):
                    a = vertex(level, index, side)
                    b = vertex(level, following_index, side)
                    c = vertex(level + 1, following_index, side)
                    d = vertex(level + 1, index, side)
                    if side == 0:
                        faces.extend(((a, c, b), (a, d, c)))
                    else:
                        faces.extend(((a, b, c), (a, c, d)))
        top = rings - 1
        for index in range(segment_count):
            following_index = (index + 1) % count
            left = vertex(top, index, 0)
            right = vertex(top, index, 1)
            next_left = vertex(top, following_index, 0)
            next_right = vertex(top, following_index, 1)
            faces.extend(((left, next_right, right), (left, next_left, next_right)))
        mesh = trimesh.Trimesh(
            vertices=vertices,
            faces=np.asarray(faces, dtype=np.int64),
            vertex_colors=vertex_colours,
            process=False,
            maintain_order=True,
        )
        meshes.append(mesh)
        total_segments += segment_count

    combined = trimesh.util.concatenate(meshes)
    return combined, {
        "paths": len(paths),
        "segments": total_segments,
        "rings": rings,
        "vertices": int(len(combined.vertices)),
        "triangles": int(len(combined.faces)),
    }


def build_hair_shell(
    subject_mask: np.ndarray,
    patch_footprint: np.ndarray,
    face_depth: np.ndarray,
    source_rgb: np.ndarray,
    landmarks: DenseFaceLandmarks,
    back_anchor: float,
    recess: float,
    long_edge: int,
) -> tuple[trimesh.Trimesh | None, np.ndarray, dict[str, object]]:
    """Create a smooth hair-only shell that reaches the back anchor at its silhouette."""

    height, width = subject_mask.shape
    points = np.asarray(landmarks.core, dtype=np.float64)
    face_height = landmarks.bounds[3] - landmarks.bounds[1]
    upper_limit = int(round(landmarks.bounds[1] + 0.52 * face_height))
    rows = np.indices(subject_mask.shape)[0]
    kernel_size = max(3, int(round((landmarks.bounds[2] - landmarks.bounds[0]) * 0.018)))
    if kernel_size % 2 == 0:
        kernel_size += 1
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
    # Retain a narrow overlap under the HRN scalp instead of opening a visible
    # gap between two independent surfaces.
    contracted_patch = cv2.erode(
        patch_footprint.astype(np.uint8), kernel, iterations=1
    ) > 0
    hair_mask = subject_mask & (rows < upper_limit) & ~contracted_patch
    hair_mask = cv2.morphologyEx(
        hair_mask.astype(np.uint8), cv2.MORPH_CLOSE, kernel, iterations=1
    ).astype(bool)

    components, labels, statistics, _centroids = cv2.connectedComponentsWithStats(
        hair_mask.astype(np.uint8), connectivity=8
    )
    minimum_area = max(32, int(0.0015 * face_height * face_height))
    keep = np.zeros_like(hair_mask)
    for label in range(1, components):
        if int(statistics[label, cv2.CC_STAT_AREA]) >= minimum_area:
            keep |= labels == label
    hair_mask = keep
    if not hair_mask.any():
        return None, hair_mask, {"enabled": True, "pixels": 0, "reason": "no hair fringe outside HRN"}

    distance_from_patch = distance_transform_edt(~contracted_patch)
    distance_from_edge = distance_transform_edt(hair_mask)
    pullback = distance_from_patch / np.maximum(distance_from_patch + distance_from_edge, 1e-6)
    pullback = smoothstep(pullback)
    inner_depth = face_depth - recess
    # The AC3D reference pulls hair backward, but not all the way to the deepest
    # cranium vertex. A local scalp percentile avoids a vertical comb wall.
    local_back_anchor = max(
        back_anchor, float(np.percentile(face_depth[patch_footprint], 18.0))
    )
    shell_depth = inner_depth * (1.0 - pullback) + local_back_anchor * pullback
    weights = hair_mask.astype(np.float32)
    blur_sigma = max(1.0, face_height * 0.008)
    smoothed_values = cv2.GaussianBlur(shell_depth * weights, (0, 0), blur_sigma)
    smoothed_weights = cv2.GaussianBlur(weights, (0, 0), blur_sigma)
    shell_depth[hair_mask] = (
        smoothed_values[hair_mask] / np.maximum(smoothed_weights[hair_mask], 1e-6)
    )

    columns, grid_rows_count = resize_grid_shape(width, height, long_edge)
    grid_mask = cv2.resize(
        hair_mask.astype(np.uint8), (columns, grid_rows_count), interpolation=cv2.INTER_NEAREST
    ).astype(bool)
    grid_depth = cv2.resize(shell_depth, (columns, grid_rows_count), interpolation=cv2.INTER_CUBIC)
    grid_columns, grid_rows = np.meshgrid(
        np.linspace(0.0, width - 1.0, columns),
        np.linspace(0.0, height - 1.0, grid_rows_count),
    )
    pixels = np.column_stack((grid_columns.ravel(), grid_rows.ravel()))
    xy = source_pixels_to_scene(pixels, (width, height))
    vertices = np.column_stack((xy, grid_depth.ravel()))
    faces = build_grid_faces(grid_mask)
    luma = cv2.cvtColor(source_rgb, cv2.COLOR_RGB2GRAY)
    colours = sample_source_colors(np.repeat(luma[:, :, None], 3, axis=2), pixels)
    mesh = trimesh.Trimesh(
        vertices=vertices,
        faces=faces,
        vertex_colors=colours,
        process=False,
        maintain_order=True,
    )
    mesh.remove_unreferenced_vertices()
    return mesh, hair_mask, {
        "enabled": True,
        "pixels": int(hair_mask.sum()),
        "upper_limit_row": upper_limit,
        "minimum_component_area": minimum_area,
        "global_back_anchor": back_anchor,
        "local_hair_back_anchor": local_back_anchor,
        "recess": recess,
        "vertices": int(len(mesh.vertices)),
        "triangles": int(len(mesh.faces)),
        "pullback_method": "continuous hair-only heightfield to global back anchor",
    }


def save_float_preview(path: Path, values: np.ndarray, mask: np.ndarray) -> None:
    preview = np.zeros((*values.shape, 3), dtype=np.uint8)
    normalized = np.clip(values * 0.5 + 0.5, 0.0, 1.0)
    preview[:, :, 0] = np.round(np.maximum(-values, 0.0) * 255.0).astype(np.uint8)
    preview[:, :, 1] = np.round(normalized * 110.0).astype(np.uint8)
    preview[:, :, 2] = np.round(np.maximum(values, 0.0) * 255.0).astype(np.uint8)
    preview[~mask] = 0
    Image.fromarray(preview, mode="RGB").save(path)


def main() -> int:
    args = parse_args()
    if args.output_dir.exists():
        raise FileExistsError(f"Output directory already exists: {args.output_dir}")
    args.output_dir.mkdir(parents=True)

    source_rgba = np.asarray(Image.open(args.source).convert("RGBA"))
    source_rgb = source_rgba[:, :, :3]
    subject_mask, alpha_stats = largest_alpha_component(source_rgba)
    faces = detect_dense_faces(source_rgb, max_faces=1, min_confidence=0.40)
    if len(faces) != 1:
        raise RuntimeError(f"v3.4 portrait route requires exactly one face; detected {len(faces)}")
    landmarks = faces[0]

    loaded = trimesh.load(args.input_glb, force="scene", process=False)
    hrn_geometry = find_node_geometry(loaded, "HRN_NATIVE_FACE_HEAD")
    body_geometry = find_node_geometry(loaded, "MOGE_BODY_HAIR_UNDERLAY")
    hrn_mesh = loaded.geometry[hrn_geometry].copy()
    body_mesh = loaded.geometry[body_geometry].copy()

    subject_height = float(loaded.bounds[1, 1] - loaded.bounds[0, 1])
    envelope = apply_depth_envelope(
        [body_mesh, hrn_mesh], subject_height * args.target_depth_height_ratio
    )
    source_size = (source_rgb.shape[1], source_rgb.shape[0])
    patch_pixels = scene_xy_to_source_pixels(hrn_mesh.vertices[:, :2], source_size)
    patch_depth, patch_mask = rasterize_patch_depth(
        subject_mask.shape, patch_pixels, hrn_mesh.vertices[:, 2], hrn_mesh.faces
    )
    patch_mask &= subject_mask
    face_depth = fill_patch_depth(patch_depth, patch_mask)

    detail_field, detail_mask, detail_stats = build_source_detail_field(source_rgb, landmarks)
    displacement = bilinear_sample(detail_field, patch_pixels) * args.detail_amplitude
    active = bilinear_sample(detail_mask.astype(np.float32), patch_pixels) > 0.5
    hrn_vertices = np.asarray(hrn_mesh.vertices).copy()
    hrn_vertices[active, 2] += displacement[active]
    hrn_mesh.vertices = hrn_vertices
    detail_stats.update(
        {
            "amplitude": args.detail_amplitude,
            "affected_hrn_vertices": int(active.sum()),
            "minimum_displacement": float(displacement[active].min()) if active.any() else 0.0,
            "maximum_displacement": float(displacement[active].max()) if active.any() else 0.0,
        }
    )

    # Refresh the face support after micro-relief so frames sit above the final skin.
    patch_depth, patch_mask = rasterize_patch_depth(
        subject_mask.shape, patch_pixels, hrn_mesh.vertices[:, 2], hrn_mesh.faces
    )
    patch_mask &= subject_mask
    face_depth = fill_patch_depth(patch_depth, patch_mask)
    frame_paths, frame_fit, frame_overlay = fit_eyeglass_paths(source_rgb, landmarks)
    frame_mesh, frame_mesh_stats = build_ribbon_mesh(
        frame_paths,
        face_depth,
        source_rgb,
        args.frame_width_px,
        args.frame_rise,
        args.frame_backfill_rings,
    )

    patch_footprint = rasterize_patch_footprint(
        subject_mask.shape, patch_pixels, hrn_mesh.faces
    )
    back_anchor = min(
        float(body_mesh.vertices[:, 2].min()), float(hrn_mesh.vertices[:, 2].min())
    )
    hair_mesh, hair_mask, hair_stats = build_hair_shell(
        subject_mask,
        patch_footprint,
        face_depth,
        source_rgb,
        landmarks,
        back_anchor,
        args.hair_recess,
        args.hair_grid_long_edge,
    )

    scene = trimesh.Scene()
    scene.add_geometry(body_mesh, node_name="MOGE_BODY_HAIR_UNDERLAY")
    if hair_mesh is not None:
        scene.add_geometry(hair_mesh, node_name="SOURCE_HAIR_SHALLOW_PULLBACK")
    scene.add_geometry(hrn_mesh, node_name="HRN_NATIVE_FACE_HEAD_SOURCE_DETAIL")
    scene.add_geometry(frame_mesh, node_name="SOURCE_ALIGNED_OPEN_EYEGLASS_FRAMES")
    glb_path = args.output_dir / "portrait-v34-source-structured.glb"
    scene.export(glb_path)
    combined = [body_mesh]
    if hair_mesh is not None:
        combined.append(hair_mesh)
    combined.extend((hrn_mesh, frame_mesh))
    obj_path = args.output_dir / "portrait-v34-source-structured.obj"
    trimesh.util.concatenate(combined).export(obj_path)

    Image.fromarray(frame_overlay, mode="RGB").save(args.output_dir / "01-eyeglass-fit-overlay.png")
    Image.fromarray(detail_mask.astype(np.uint8) * 255, mode="L").save(
        args.output_dir / "02-face-detail-mask.png"
    )
    save_float_preview(
        args.output_dir / "03-source-detail-displacement.png", detail_field, detail_mask
    )
    Image.fromarray(hair_mask.astype(np.uint8) * 255, mode="L").save(
        args.output_dir / "04-hair-shell-mask.png"
    )

    final_depth = float(scene.bounds[1, 2] - scene.bounds[0, 2])
    stats = {
        "method": "portrait v3.4 source-structured HRN/MoGe refinement",
        "source": str(args.source.resolve()),
        "input_glb": str(args.input_glb.resolve()),
        "alpha": alpha_stats,
        "depth_envelope": {
            **envelope,
            "reference": "Cockpit3D amma AC3D mesh depth/height ratio 28.9007/127.5276",
            "requested_ratio": args.target_depth_height_ratio,
            "subject_height": subject_height,
            "final_scene_depth_including_glasses": final_depth,
            "final_ratio": final_depth / subject_height,
        },
        "source_detail": detail_stats,
        "eyeglasses": {
            "fit": frame_fit,
            "geometry": {
                **frame_mesh_stats,
                "width_px": args.frame_width_px,
                "rise": args.frame_rise,
                "lenses_are_open": True,
                "independent_thick_lens_discs": False,
                "backfill": "tapered source-face to raised-frame rings",
            },
        },
        "hair_shell": hair_stats,
        "model_routing": {
            "head_identity": "existing native HRN v3.3 mesh",
            "body_and_garment": "existing subject-normalized MoGe v3.3 underlay",
            "facial_detail": "bounded source luminance band-pass inside MediaPipe face mask",
            "glasses": "MediaPipe-guided source edge/darkness fit",
            "pare_full_body_completion": False,
        },
        "meshes": {
            "body_triangles": int(len(body_mesh.faces)),
            "hrn_triangles": int(len(hrn_mesh.faces)),
            "hair_triangles": int(len(hair_mesh.faces)) if hair_mesh is not None else 0,
            "eyeglass_triangles": int(len(frame_mesh.faces)),
        },
        "outputs": {"glb": glb_path.name, "obj": obj_path.name},
    }
    (args.output_dir / "portrait-v34-stats.json").write_text(
        json.dumps(stats, indent=2), encoding="utf-8"
    )
    print(
        "PORTRAIT_V34_OK "
        f"depth_ratio={stats['depth_envelope']['final_ratio']:.4f} "
        f"glasses={len(frame_mesh.faces):,}tris hair={stats['meshes']['hair_triangles']:,}tris"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
