"""
File: code/research/extract_hrn_direct_front_patch.py
Purpose:
 - Preserve the native HRN head topology as a source-camera-aligned front patch.
 - Use the rendered HRN depth only to identify visible faces, never to rebuild geometry.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
import trimesh
from PIL import Image

from fuse_hrn_locked_head_moge_body_depth import (
    build_head_region,
    detect_single_face,
)
from fuse_hrn_moge_portrait_depth import (
    largest_alpha_component,
    register_hrn_texture,
    robust_normalize,
)
from source_camera_fusion import sample_source_colors, source_pixels_to_scene


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--hrn-mesh", required=True, type=Path)
    parser.add_argument("--hrn-assets-dir", required=True, type=Path)
    parser.add_argument("--moge-depth", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--head-depth-span", type=float, default=0.60)
    parser.add_argument("--body-depth-span", type=float, default=0.26)
    parser.add_argument("--visibility-tolerance", type=float, default=0.035)
    parser.add_argument("--front-normal-maximum", type=float, default=0.10)
    parser.add_argument("--ratio-threshold", type=float, default=0.72)
    parser.add_argument("--ransac-threshold-px", type=float, default=3.0)
    parser.add_argument(
        "--surface-mode",
        choices=("front-patch", "closed-head"),
        default="front-patch",
        help="Keep only source-visible faces or retain native HRN side/back topology.",
    )
    parser.add_argument("--closed-head-neck-cut-factor", type=float, default=1.25)
    return parser.parse_args()


def obj_to_blender_world(vertices: np.ndarray) -> np.ndarray:
    """Match Blender's OBJ import axes: OBJ (x, y, z) -> Blender (x, -z, y)."""

    return np.column_stack((vertices[:, 0], -vertices[:, 2], vertices[:, 1]))


def project_hrn_pixels(
    centered_world: np.ndarray,
    resolution: int,
    ortho_scale: float,
) -> np.ndarray:
    """Project centred Blender-world vertices into the deterministic HRN render."""

    columns = (centered_world[:, 0] / ortho_scale + 0.5) * (resolution - 1)
    rows = (0.5 - centered_world[:, 2] / ortho_scale) * (resolution - 1)
    return np.column_stack((columns, rows))


def apply_affine(points: np.ndarray, affine: np.ndarray) -> np.ndarray:
    return points @ affine[:, :2].T + affine[:, 2]


def sample_boolean(mask: np.ndarray, points: np.ndarray) -> np.ndarray:
    height, width = mask.shape
    columns = np.rint(points[:, 0]).astype(np.int64)
    rows = np.rint(points[:, 1]).astype(np.int64)
    inside = (
        (columns >= 0)
        & (rows >= 0)
        & (columns < width)
        & (rows < height)
    )
    sampled = np.zeros(len(points), dtype=bool)
    sampled[inside] = mask[rows[inside], columns[inside]]
    return sampled


def sample_float(values: np.ndarray, points: np.ndarray) -> np.ndarray:
    height, width = values.shape
    columns = np.clip(np.rint(points[:, 0]).astype(np.int64), 0, width - 1)
    rows = np.clip(np.rint(points[:, 1]).astype(np.int64), 0, height - 1)
    return values[rows, columns]


def fit_depth_display_curve(
    native_depth: np.ndarray,
    rendered_depth: np.ndarray,
    reliable: np.ndarray,
) -> tuple[np.ndarray, dict]:
    """Fit Blender's display transform so its PNG can act only as a visibility buffer."""

    if int(reliable.sum()) < 100:
        raise RuntimeError("Too few strongly front-facing HRN faces for visibility fitting")
    selected = reliable.copy()
    coefficients = np.polyfit(native_depth[selected], rendered_depth[selected], 1)
    for _ in range(3):
        residual = np.abs(np.polyval(coefficients, native_depth) - rendered_depth)
        threshold = float(np.percentile(residual[selected], 90.0))
        selected = reliable & (residual <= max(threshold, 0.004))
        coefficients = np.polyfit(native_depth[selected], rendered_depth[selected], 1)
    residual = np.abs(np.polyval(coefficients, native_depth) - rendered_depth)
    return residual, {
        "linear_coefficients": coefficients.tolist(),
        "fit_faces": int(selected.sum()),
        "median_residual": float(np.median(residual[selected])),
        "p95_residual": float(np.percentile(residual[selected], 95.0)),
    }


def largest_face_component(mesh: trimesh.Trimesh, face_indices: np.ndarray) -> np.ndarray:
    """Discard isolated visibility specks while retaining the connected native face patch."""

    if len(face_indices) == 0:
        raise RuntimeError("No source-visible HRN faces survived selection")
    selected = np.zeros(len(mesh.faces), dtype=bool)
    selected[face_indices] = True
    adjacency = np.asarray(mesh.face_adjacency)
    adjacency = adjacency[selected[adjacency].all(axis=1)]
    components = trimesh.graph.connected_components(
        adjacency, nodes=face_indices, min_len=1
    )
    if not components:
        raise RuntimeError("HRN front selection produced no connected surface")
    return np.asarray(max(components, key=len), dtype=np.int64)


def extract_indexed_patch(
    vertices: np.ndarray,
    faces: np.ndarray,
    selected_faces: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    chosen = faces[selected_faces]
    used = np.unique(chosen)
    remap = np.full(len(vertices), -1, dtype=np.int64)
    remap[used] = np.arange(len(used), dtype=np.int64)
    return vertices[used], remap[chosen], used


def raster_depth_preview(
    source_shape: tuple[int, int],
    points: np.ndarray,
    depth: np.ndarray,
    head_mask: np.ndarray,
) -> np.ndarray:
    """Create a diagnostic preview; this raster is never used as output geometry."""

    height, width = source_shape
    canvas = np.full((height, width), np.nan, dtype=np.float32)
    columns = np.rint(points[:, 0]).astype(np.int64)
    rows = np.rint(points[:, 1]).astype(np.int64)
    inside = (
        (columns >= 0)
        & (rows >= 0)
        & (columns < width)
        & (rows < height)
    )
    for row, column, value in zip(rows[inside], columns[inside], depth[inside]):
        if not np.isfinite(canvas[row, column]) or value > canvas[row, column]:
            canvas[row, column] = value
    valid = np.isfinite(canvas)
    if valid.any():
        _, nearest = cv2.distanceTransformWithLabels(
            (~valid).astype(np.uint8), cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL
        )
        valid_values = canvas[valid]
        labels = nearest.astype(np.int64) - 1
        labels = np.clip(labels, 0, max(len(valid_values) - 1, 0))
        filled = valid_values[labels]
    else:
        filled = np.zeros_like(canvas)
    filled[~head_mask] = 0.0
    preview = np.zeros_like(canvas, dtype=np.uint16)
    sample = filled[head_mask]
    low, high = np.percentile(sample, [1.0, 99.0])
    normalized = np.clip((filled - low) / max(high - low, 1e-8), 0.0, 1.0)
    preview[head_mask] = np.round(normalized[head_mask] * 65535.0).astype(np.uint16)
    return preview


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=False)

    source_rgba = np.asarray(Image.open(args.source).convert("RGBA"))
    source_rgb = source_rgba[:, :, :3]
    source_height, source_width = source_rgb.shape[:2]
    subject_mask, alpha_stats = largest_alpha_component(source_rgba)

    pipeline_root = Path(__file__).resolve().parents[2]
    face_model = pipeline_root / "Models/opencv-face-detector-yunet/face_detection_yunet_2023mar.onnx"
    face = detect_single_face(source_rgb, face_model)
    head_mask, head_stats = build_head_region(subject_mask, face)

    assets_dir = args.hrn_assets_dir.resolve()
    assets = json.loads((assets_dir / "hrn-front-assets.json").read_text(encoding="utf-8"))
    hrn_texture = np.asarray(Image.open(assets_dir / "hrn-front-texture.png").convert("RGBA"))
    affine, registration = register_hrn_texture(
        hrn_texture, source_rgba, args.ratio_threshold, args.ransac_threshold_px
    )

    native_mesh = trimesh.load(
        args.hrn_mesh.resolve(), force="mesh", process=False, maintain_order=True
    )
    native_vertices = np.asarray(native_mesh.vertices)
    native_faces = np.asarray(native_mesh.faces)
    world_vertices = obj_to_blender_world(native_vertices)
    centered_world = world_vertices - np.asarray(assets["center_removed"], dtype=np.float64)
    raw_normals = np.asarray(native_mesh.face_normals)
    world_normals = obj_to_blender_world(raw_normals)

    resolution = int(assets["resolution"])
    ortho_scale = float(assets["camera"]["ortho_scale"])
    near_y = float(assets["camera"]["near_object_y"])
    far_y = float(assets["camera"]["far_object_y"])
    face_centers = centered_world[native_faces].mean(axis=1)
    face_hrn_pixels = project_hrn_pixels(face_centers, resolution, ortho_scale)
    face_source_pixels = apply_affine(face_hrn_pixels, affine)

    depth_rgba = cv2.imread(str(assets_dir / "hrn-front-depth.png"), cv2.IMREAD_UNCHANGED)
    if depth_rgba is None or depth_rgba.ndim != 3 or depth_rgba.shape[2] != 4:
        raise RuntimeError("HRN front depth must be a four-channel 16-bit PNG")
    render_valid = sample_boolean(depth_rgba[:, :, 3] > 0, face_hrn_pixels)
    rendered_depth = sample_float(
        depth_rgba[:, :, 0].astype(np.float32) / 65535.0, face_hrn_pixels
    )
    native_depth = (far_y - face_centers[:, 1]) / max(far_y - near_y, 1e-8)
    strongly_front = render_valid & (world_normals[:, 1] < -0.75)
    visibility_residual, display_fit = fit_depth_display_curve(
        native_depth, rendered_depth, strongly_front
    )
    in_head = sample_boolean(head_mask, face_source_pixels)
    if args.surface_mode == "closed-head":
        # Preserve native side/back topology and crop only the generic lower
        # bust by image row. Unlike a silhouette mask, this horizontal cut does
        # not remove the rear hemisphere of the head.
        _, face_y, _, face_height = face["box_xywh"]
        neck_cut_row = min(
            source_height - 1,
            int(round(face_y + args.closed_head_neck_cut_factor * face_height)),
        )
        selected = face_source_pixels[:, 1] <= neck_cut_row
    else:
        selected = (
            render_valid
            & in_head
            & (world_normals[:, 1] < args.front_normal_maximum)
            & (visibility_residual <= args.visibility_tolerance)
        )
    selected_indices = largest_face_component(native_mesh, np.flatnonzero(selected))
    patch_world, patch_faces, used_vertices = extract_indexed_patch(
        centered_world, native_faces, selected_indices
    )

    patch_hrn_pixels = project_hrn_pixels(patch_world, resolution, ortho_scale)
    patch_source_pixels = apply_affine(patch_hrn_pixels, affine)
    patch_xy = source_pixels_to_scene(
        patch_source_pixels, (source_width, source_height)
    )

    moge_metric = np.load(args.moge_depth).astype(np.float32)
    if moge_metric.shape != subject_mask.shape:
        raise RuntimeError("MoGe depth shape does not match the portrait source")
    moge_near = robust_normalize(moge_metric, subject_mask, invert=True)
    body_field = 0.12 + moge_near * args.body_depth_span
    x, y, face_width, face_height = face["box_xywh"]
    lower_band = subject_mask.copy()
    rows = np.indices(subject_mask.shape)[0]
    lower_band &= rows >= int(round(y + 0.92 * face_height))
    lower_band &= rows <= int(round(y + 1.06 * face_height))
    body_anchor = float(np.median(body_field[lower_band]))

    frontness = -patch_world[:, 1]
    if args.surface_mode == "closed-head":
        # Extremal vertices define the actual rear and nose silhouette. Robust
        # clipping is useful for a front relief, but it flattens the rear
        # hemisphere of a complete native head into a vertical plane.
        low, high = float(frontness.min()), float(frontness.max())
    else:
        low, high = np.percentile(frontness, [1.0, 99.0])
    normalized_frontness = np.clip((frontness - low) / max(high - low, 1e-8), 0.0, 1.0)
    patch_rows = patch_source_pixels[:, 1]
    anchor_vertices = (
        (patch_rows >= y + 0.82 * face_height)
        & (patch_rows <= y + 1.06 * face_height)
    )
    if int(anchor_vertices.sum()) < 100:
        anchor_vertices = np.ones(len(patch_world), dtype=bool)
    head_anchor = float(np.median(normalized_frontness[anchor_vertices]))
    patch_z = body_anchor + (normalized_frontness - head_anchor) * args.head_depth_span
    patch_vertices = np.column_stack((patch_xy, patch_z))

    patch_mesh = trimesh.Trimesh(
        vertices=patch_vertices,
        faces=patch_faces,
        process=False,
        maintain_order=True,
        vertex_colors=sample_source_colors(source_rgb, patch_source_pixels),
    )
    obj_path = output_dir / "hrn-direct-front-patch.obj"
    glb_path = output_dir / "hrn-direct-front-patch.glb"
    patch_mesh.export(obj_path)
    patch_mesh.export(glb_path)

    preview = raster_depth_preview(
        (source_height, source_width), patch_source_pixels, patch_z, head_mask
    )
    Image.fromarray(preview, mode="I;16").save(output_dir / "hrn-direct-depth-preview.png")
    Image.fromarray(head_mask.astype(np.uint8) * 255, mode="L").save(
        output_dir / "hrn-direct-ownership-mask.png"
    )

    stats = {
        "method": "native HRN topology transformed directly into source camera",
        "surface_mode": args.surface_mode,
        "rasterized_geometry": False,
        "model_stack": {
            "head_and_face": "Official ModelScope HRN Head v0.1 native mesh",
            "depth_anchor_only": "MoGe-2 ViT-L",
            "silhouette": "BiRefNet portrait alpha",
        },
        "source": str(args.source.resolve()),
        "hrn_mesh": str(args.hrn_mesh.resolve()),
        "alpha": alpha_stats,
        "face": face,
        "head_region": head_stats,
        "registration": registration,
        "visibility": {
            **display_fit,
            "tolerance": args.visibility_tolerance,
            "front_normal_maximum": args.front_normal_maximum,
            "candidate_faces": int(selected.sum()),
            "connected_faces": int(len(patch_faces)),
            "closed_head_neck_cut_row": (
                neck_cut_row
                if args.surface_mode == "closed-head"
                else None
            ),
        },
        "depth": {
            "head_depth_span_requested": args.head_depth_span,
            "body_anchor": body_anchor,
            "head_anchor": head_anchor,
            "z_percentiles": np.percentile(patch_z, [1.0, 50.0, 99.0]).tolist(),
            "z_span": float(patch_z.max() - patch_z.min()),
        },
        "mesh": {
            "vertices": int(len(patch_vertices)),
            "triangles": int(len(patch_faces)),
            "components": int(len(patch_mesh.split(only_watertight=False))),
            "bounds": patch_mesh.bounds.tolist(),
        },
        "outputs": {"obj": obj_path.name, "glb": glb_path.name},
    }
    (output_dir / "hrn-direct-front-patch-stats.json").write_text(
        json.dumps(stats, indent=2), encoding="utf-8"
    )
    print(
        "HRN_DIRECT_FRONT_PATCH_OK "
        f"{len(patch_vertices):,} vertices / {len(patch_faces):,} triangles; "
        f"registration {registration['median_reprojection_error_px']:.3f}px"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
