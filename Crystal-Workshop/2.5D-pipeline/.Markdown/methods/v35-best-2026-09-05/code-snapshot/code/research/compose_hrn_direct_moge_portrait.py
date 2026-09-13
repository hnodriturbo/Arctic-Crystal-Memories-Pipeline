"""
File: code/research/compose_hrn_direct_moge_portrait.py
Purpose:
 - Combine a native HRN front-face patch with a MoGe neck/body underlay.
 - Keep BiRefNet segmentation separate from real-valued depth evidence.
 - Produce subject-only depth QA and a layered GLB without rasterising HRN geometry.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
import trimesh
from PIL import Image
from scipy.ndimage import distance_transform_edt

from add_feathered_depth_skirts import boundary_geometry, smoothstep
from fuse_hrn_moge_portrait_depth import largest_alpha_component, robust_normalize
from source_camera_fusion import sample_source_colors, source_pixels_to_scene


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--moge-depth", required=True, type=Path)
    parser.add_argument("--hrn-patch", required=True, type=Path)
    parser.add_argument("--hrn-stats", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--grid-long-edge", type=int, default=700)
    parser.add_argument("--body-depth-span", type=float, default=0.26)
    parser.add_argument("--body-base-depth", type=float, default=0.10)
    parser.add_argument("--shoulder-depth-boost", type=float, default=0.12)
    parser.add_argument("--shoulder-start-factor", type=float, default=0.95)
    parser.add_argument("--shoulder-peak-factor", type=float, default=1.20)
    parser.add_argument("--shoulder-end-factor", type=float, default=1.75)
    parser.add_argument("--frame-cut-back-depth", type=float, default=0.24)
    parser.add_argument("--frame-cut-border-px", type=float, default=5.0)
    parser.add_argument("--frame-cut-inset-px", type=float, default=7.0)
    parser.add_argument("--frame-cut-rings", type=int, default=13)
    parser.add_argument(
        "--frame-cut-backfill",
        action="store_true",
        help="Opt-in experimental rear fold for source-frame-cut edges.",
    )
    parser.add_argument("--patch-overlap-px", type=int, default=6)
    parser.add_argument("--glide-rings", type=int, default=7)
    parser.add_argument("--glide-width-px", type=float, default=10.0)
    parser.add_argument(
        "--outer-glide",
        action="store_true",
        help="Add an explicit outer-boundary strip; normally unnecessary for closed HRN heads.",
    )
    parser.add_argument(
        "--closed-head-hair-mode",
        choices=("none", "fringe"),
        default="none",
        help="Use clean HRN head geometry or retain experimental MoGe hair fringe.",
    )
    parser.add_argument("--minimum-subject-depth-span", type=float, default=0.08)
    return parser.parse_args()


def scene_xy_to_source_pixels(
    scene_xy: np.ndarray, source_size: tuple[int, int]
) -> np.ndarray:
    source_width, source_height = source_size
    half_height = (source_height - 1) * 0.5
    center_x = (source_width - 1) * 0.5
    center_y = (source_height - 1) * 0.5
    columns = scene_xy[:, 0] * half_height + center_x
    rows = center_y - scene_xy[:, 1] * half_height
    return np.column_stack((columns, rows))


def build_shoulder_depth_weight(
    shape: tuple[int, int],
    face_y: float,
    face_height: float,
    start_factor: float,
    peak_factor: float,
    end_factor: float,
) -> np.ndarray:
    """Create a feathered vertical shoulder band without changing the lower torso."""

    if not start_factor < peak_factor < end_factor:
        raise ValueError("Shoulder factors must satisfy start < peak < end")
    image_rows = np.indices(shape, dtype=np.float32)[0]
    start = face_y + start_factor * face_height
    peak = face_y + peak_factor * face_height
    end = face_y + end_factor * face_height
    rise = np.clip((image_rows - start) / max(peak - start, 1e-6), 0.0, 1.0)
    fall = np.clip((end - image_rows) / max(end - peak, 1e-6), 0.0, 1.0)
    rise = rise * rise * (3.0 - 2.0 * rise)
    fall = fall * fall * (3.0 - 2.0 * fall)
    return rise * fall


def build_frame_cut_backfill(
    body_mesh: trimesh.Trimesh,
    source_size: tuple[int, int],
    border_px: float,
    back_depth: float,
    inset_px: float,
    ring_count: int,
) -> tuple[trimesh.Trimesh | None, dict]:
    """Fold only source-frame-cut body edges backward into a feathered skirt."""

    if ring_count < 2:
        raise ValueError("frame-cut ring count must be at least 2")
    if border_px < 0.0 or back_depth <= 0.0 or inset_px < 0.0:
        raise ValueError("frame-cut dimensions must be non-negative and depth positive")

    boundary_ids, edge_local, outward, boundary_edges = boundary_geometry(body_mesh)
    front = np.asarray(body_mesh.vertices, dtype=np.float64)[boundary_ids]
    pixels = scene_xy_to_source_pixels(front[:, :2], source_size)
    width, height = source_size
    at_left = pixels[:, 0] <= border_px
    at_right = pixels[:, 0] >= width - 1.0 - border_px
    at_top = pixels[:, 1] <= border_px
    at_bottom = pixels[:, 1] >= height - 1.0 - border_px
    side_flags = np.column_stack((at_left, at_right, at_top, at_bottom))
    vertex_selected = side_flags.any(axis=1)
    selected_edges_mask = vertex_selected[edge_local].all(axis=1)
    selected_edge_local = edge_local[selected_edges_mask]
    selected_boundary_edges = boundary_edges[selected_edges_mask]
    if len(selected_edge_local) == 0:
        return None, {
            "enabled": True,
            "selected_edges": 0,
            "reason": "subject does not intersect the source frame",
        }

    selected_local_ids = np.unique(selected_edge_local)
    remap = np.full(len(boundary_ids), -1, dtype=np.int64)
    remap[selected_local_ids] = np.arange(len(selected_local_ids))
    selected_edges = remap[selected_edge_local]
    selected_front = front[selected_local_ids]
    selected_outward = outward[selected_local_ids]
    selected_flags = side_flags[selected_local_ids]

    scene_units_per_pixel = 2.0 / max(height - 1, 1)
    back_plane = float(np.percentile(body_mesh.vertices[:, 2], 5.0) - back_depth)
    ring_t = np.linspace(0.0, 1.0, ring_count, dtype=np.float64)
    depth_blend = smoothstep(ring_t)
    inset_blend = smoothstep(ring_t) ** 0.72
    rings = []
    for depth_amount, inset_amount in zip(depth_blend, inset_blend, strict=True):
        ring = selected_front.copy()
        ring[:, :2] -= (
            selected_outward
            * inset_px
            * scene_units_per_pixel
            * inset_amount
        )
        ring[:, 2] = (
            selected_front[:, 2] * (1.0 - depth_amount)
            + back_plane * depth_amount
        )
        rings.append(ring)
    vertices = np.vstack(rings)

    boundary_count = len(selected_local_ids)
    faces = []
    for ring_index in range(ring_count - 1):
        current = selected_edges + ring_index * boundary_count
        following = selected_edges + (ring_index + 1) * boundary_count
        faces.append(np.column_stack((current[:, 0], current[:, 1], following[:, 1])))
        faces.append(np.column_stack((current[:, 0], following[:, 1], following[:, 0])))
    backfill_faces = np.vstack(faces)
    source_colours = np.asarray(body_mesh.visual.vertex_colors)[boundary_ids[selected_local_ids]]
    colours = np.tile(source_colours, (ring_count, 1))
    backfill = trimesh.Trimesh(
        vertices=vertices,
        faces=backfill_faces,
        vertex_colors=colours,
        process=False,
        maintain_order=True,
    )
    side_names = ("left", "right", "top", "bottom")
    return backfill, {
        "enabled": True,
        "border_px": border_px,
        "back_depth": back_depth,
        "back_plane": back_plane,
        "inset_px": inset_px,
        "rings": ring_count,
        "selected_edges": int(len(selected_edges)),
        "selected_vertices": int(boundary_count),
        "triangles": int(len(backfill_faces)),
        "sides": {
            name: int(selected_flags[:, index].sum())
            for index, name in enumerate(side_names)
        },
        "source_frame_only": True,
        "front_surface_modified": False,
    }


def rasterize_patch_footprint(
    shape: tuple[int, int], source_pixels: np.ndarray, faces: np.ndarray
) -> np.ndarray:
    footprint = np.zeros(shape, dtype=np.uint8)
    points = np.rint(source_pixels).astype(np.int32)
    height, width = shape
    points[:, 0] = np.clip(points[:, 0], 0, width - 1)
    points[:, 1] = np.clip(points[:, 1], 0, height - 1)
    for triangle in faces:
        cv2.fillConvexPoly(footprint, points[triangle], 255, lineType=cv2.LINE_8)
    return footprint > 0


def rasterize_patch_depth(
    shape: tuple[int, int],
    source_pixels: np.ndarray,
    vertex_depth: np.ndarray,
    faces: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Rasterise only a recessed support target, never the visible HRN surface."""

    depth = np.zeros(shape, dtype=np.float32)
    footprint = np.zeros(shape, dtype=np.uint8)
    points = np.rint(source_pixels).astype(np.int32)
    height, width = shape
    points[:, 0] = np.clip(points[:, 0], 0, width - 1)
    points[:, 1] = np.clip(points[:, 1], 0, height - 1)
    face_depth = vertex_depth[faces].mean(axis=1)
    for face_index in np.argsort(face_depth):
        triangle = faces[face_index]
        cv2.fillConvexPoly(
            depth, points[triangle], float(face_depth[face_index]), lineType=cv2.LINE_8
        )
        cv2.fillConvexPoly(footprint, points[triangle], 255, lineType=cv2.LINE_8)
    return depth, footprint > 0


def resize_grid_shape(
    source_width: int, source_height: int, long_edge: int
) -> tuple[int, int]:
    scale = long_edge / max(source_width, source_height)
    return max(2, round(source_width * scale)), max(2, round(source_height * scale))


def build_grid_faces(mask: np.ndarray) -> np.ndarray:
    rows, columns = mask.shape
    row_index, column_index = np.meshgrid(
        np.arange(rows - 1), np.arange(columns - 1), indexing="ij"
    )
    top_left = (row_index * columns + column_index).ravel()
    top_right = top_left + 1
    bottom_left = top_left + columns
    bottom_right = bottom_left + 1
    inside = mask.ravel()
    keep = (
        inside[top_left]
        & inside[top_right]
        & inside[bottom_left]
        & inside[bottom_right]
    )
    lower = np.stack(
        (top_left[keep], bottom_left[keep], bottom_right[keep]), axis=1
    )
    upper = np.stack(
        (top_left[keep], bottom_right[keep], top_right[keep]), axis=1
    )
    return np.concatenate((lower, upper), axis=0)


def save_depth_preview(path: Path, values: np.ndarray, mask: np.ndarray) -> None:
    preview = np.zeros(values.shape, dtype=np.uint8)
    preview[mask] = np.round(np.clip(values[mask], 0.0, 1.0) * 255.0).astype(
        np.uint8
    )
    Image.fromarray(preview, mode="L").save(path)


def boundary_edges(faces: np.ndarray) -> np.ndarray:
    edges = np.concatenate(
        (faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]), axis=0
    )
    ordered = np.sort(edges, axis=1)
    unique, counts = np.unique(ordered, axis=0, return_counts=True)
    return unique[counts == 1]


def largest_boundary_component(edges: np.ndarray) -> np.ndarray:
    adjacency: dict[int, set[int]] = {}
    for left, right in edges:
        adjacency.setdefault(int(left), set()).add(int(right))
        adjacency.setdefault(int(right), set()).add(int(left))
    remaining = set(adjacency)
    components: list[set[int]] = []
    while remaining:
        pending = [remaining.pop()]
        component: set[int] = set()
        while pending:
            current = pending.pop()
            component.add(current)
            neighbours = adjacency[current] & remaining
            remaining -= neighbours
            pending.extend(neighbours)
        components.append(component)
    outer = max(components, key=len)
    return np.asarray(
        [edge for edge in edges if int(edge[0]) in outer and int(edge[1]) in outer],
        dtype=np.int64,
    )


def sample_nearest(values: np.ndarray, pixels: np.ndarray) -> np.ndarray:
    height, width = values.shape
    columns = np.clip(np.rint(pixels[:, 0]).astype(np.int64), 0, width - 1)
    rows = np.clip(np.rint(pixels[:, 1]).astype(np.int64), 0, height - 1)
    return values[rows, columns]


def build_glide_mesh(
    patch_vertices: np.ndarray,
    patch_faces: np.ndarray,
    patch_pixels: np.ndarray,
    support_depth: float,
    source_rgb: np.ndarray,
    source_size: tuple[int, int],
    rings: int,
    width_px: float,
) -> tuple[trimesh.Trimesh, dict]:
    """Build an eased multi-ring bridge from every native HRN edge to the underlay."""

    all_edges = boundary_edges(patch_faces)
    edges = largest_boundary_component(all_edges)
    boundary = np.unique(edges)
    remap = np.full(len(patch_vertices), -1, dtype=np.int64)
    remap[boundary] = np.arange(len(boundary))
    local_edges = remap[edges]
    pixels = patch_pixels[boundary]
    centre = np.median(pixels, axis=0)
    directions = pixels - centre
    lengths = np.linalg.norm(directions, axis=1, keepdims=True)
    directions /= np.maximum(lengths, 1e-6)
    target_pixels = pixels + directions * width_px
    target_xy = source_pixels_to_scene(target_pixels, source_size)
    target_z = np.full(len(target_pixels), support_depth, dtype=np.float64)
    starts = patch_vertices[boundary]
    targets = np.column_stack((target_xy, target_z))

    ring_count = max(2, rings)
    ring_vertices = []
    for index in range(ring_count):
        fraction = index / (ring_count - 1)
        eased = fraction * fraction * (3.0 - 2.0 * fraction)
        ring_vertices.append(starts * (1.0 - eased) + targets * eased)
    vertices = np.concatenate(ring_vertices, axis=0)
    boundary_count = len(boundary)
    faces = []
    for ring in range(ring_count - 1):
        first = ring * boundary_count
        second = (ring + 1) * boundary_count
        for left, right in local_edges:
            faces.append((first + left, second + left, second + right))
            faces.append((first + left, second + right, first + right))
    ring_pixels = np.tile(pixels, (ring_count, 1))
    luma = cv2.cvtColor(source_rgb, cv2.COLOR_RGB2GRAY)
    luma_rgb = np.repeat(luma[:, :, None], 3, axis=2)
    colours = sample_source_colors(luma_rgb, ring_pixels)
    mesh = trimesh.Trimesh(
        vertices=vertices,
        faces=np.asarray(faces, dtype=np.int64),
        vertex_colors=colours,
        process=False,
        maintain_order=True,
    )
    return mesh, {
        "all_boundary_edges": int(len(all_edges)),
        "boundary_edges": int(len(edges)),
        "rings": ring_count,
        "width_px": width_px,
        "vertices": int(len(vertices)),
        "triangles": int(len(faces)),
    }


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=False)

    source_rgba = np.asarray(Image.open(args.source).convert("RGBA"))
    source_rgb = source_rgba[:, :, :3]
    source_height, source_width = source_rgb.shape[:2]
    subject_mask, alpha_stats = largest_alpha_component(source_rgba)

    metric_depth = np.load(args.moge_depth).astype(np.float32)
    if metric_depth.shape != subject_mask.shape:
        raise RuntimeError("MoGe depth shape does not match the portrait source")
    if not np.isfinite(metric_depth[subject_mask]).all():
        raise RuntimeError("MoGe subject depth contains NaN or infinite values")
    subject_metric_percentiles = np.percentile(
        metric_depth[subject_mask], [1.0, 5.0, 50.0, 95.0, 99.0]
    )
    metric_span = float(subject_metric_percentiles[-1] - subject_metric_percentiles[0])
    if metric_span < args.minimum_subject_depth_span:
        raise RuntimeError(
            "MoGe subject-only depth quality gate failed: "
            f"p99-p1 span {metric_span:.4f} < {args.minimum_subject_depth_span:.4f}"
        )

    # MoGe distance is converted into a near-is-white relief field only after
    # percentile estimation inside the BiRefNet subject. Background distance
    # can therefore never flatten the person's visible dynamic range.
    moge_near = robust_normalize(metric_depth, subject_mask, invert=True)
    body_depth = args.body_base_depth + moge_near * args.body_depth_span

    loaded_patch = trimesh.load(args.hrn_patch, force="mesh", process=False)
    patch_vertices = np.asarray(loaded_patch.vertices).copy()
    patch_faces = np.asarray(loaded_patch.faces).copy()
    patch_source_pixels = scene_xy_to_source_pixels(
        patch_vertices[:, :2], (source_width, source_height)
    )
    patch_footprint = rasterize_patch_footprint(
        subject_mask.shape, patch_source_pixels, patch_faces
    )
    patch_footprint &= subject_mask

    stats = json.loads(args.hrn_stats.read_text(encoding="utf-8"))
    face_x, face_y, face_width, face_height = stats["face"]["box_xywh"]
    shoulder_weight = build_shoulder_depth_weight(
        subject_mask.shape,
        face_y,
        face_height,
        args.shoulder_start_factor,
        args.shoulder_peak_factor,
        args.shoulder_end_factor,
    )
    shoulder_weight *= subject_mask
    body_depth += (
        shoulder_weight
        * args.shoulder_depth_boost
        * (0.35 + 0.65 * moge_near)
    )
    seam_top = int(round(face_y + 0.86 * face_height))
    seam_bottom = int(round(face_y + 1.06 * face_height))
    source_rows = np.indices(subject_mask.shape)[0]

    # Keep a narrow MoGe underlap behind the native patch. It fills the real
    # hair silhouette and prevents holes, while the centre of the face remains
    # exclusively native HRN topology.
    kernel_size = max(1, args.patch_overlap_px * 2 + 1)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
    footprint_core = cv2.erode(
        patch_footprint.astype(np.uint8), kernel, iterations=1
    ).astype(bool)
    closed_head = stats.get("surface_mode") == "closed-head"
    if closed_head:
        # A complete HRN head needs no MoGe plane behind its centre. Keep only
        # the real photographic hair fringe outside HRN, plus a lower-neck
        # overlap where the MoGe garment begins.
        if args.closed_head_hair_mode == "fringe":
            body_mask = subject_mask & (~footprint_core | (source_rows >= seam_top))
        else:
            body_mask = subject_mask & (source_rows >= seam_top)
    else:
        # An open front patch needs a recessed support layer behind every hole.
        body_mask = subject_mask.copy()

    # Align the HRN patch at the under-chin overlap instead of retaining the
    # provisional anchor used by the head-only B0 checkpoint.
    patch_rows = patch_source_pixels[:, 1]
    patch_seam_vertices = (patch_rows >= seam_top) & (patch_rows <= seam_bottom)
    if int(patch_seam_vertices.sum()) < 100:
        patch_seam_vertices = patch_rows >= np.percentile(patch_rows, 82.0)
    seam_pixels = subject_mask & (source_rows >= seam_top) & (source_rows <= seam_bottom)
    body_anchor = float(np.median(body_depth[seam_pixels]))
    patch_anchor_before = float(np.median(patch_vertices[patch_seam_vertices, 2]))
    patch_translation = body_anchor - patch_anchor_before
    patch_vertices[:, 2] += patch_translation

    # Hair-only MoGe geometry must stay behind the native face. This retains
    # the photographic hair outline without allowing MoGe to cover HRN detail.
    upper_head = source_rows < seam_top
    safe_underlay_depth = float(np.percentile(patch_vertices[:, 2], 2.0) - 0.012)
    body_depth[upper_head] = np.minimum(body_depth[upper_head], safe_underlay_depth)

    columns, rows = resize_grid_shape(
        source_width, source_height, args.grid_long_edge
    )
    grid_mask = cv2.resize(
        body_mask.astype(np.uint8), (columns, rows), interpolation=cv2.INTER_NEAREST
    ).astype(bool)
    grid_depth = cv2.resize(
        body_depth, (columns, rows), interpolation=cv2.INTER_CUBIC
    )
    grid_columns, grid_rows = np.meshgrid(
        np.linspace(0.0, source_width - 1.0, columns),
        np.linspace(0.0, source_height - 1.0, rows),
    )
    grid_source_pixels = np.column_stack((grid_columns.ravel(), grid_rows.ravel()))
    grid_xy = source_pixels_to_scene(
        grid_source_pixels, (source_width, source_height)
    )
    body_vertices = np.column_stack((grid_xy, grid_depth.ravel()))
    body_faces = build_grid_faces(grid_mask)
    luma = cv2.cvtColor(source_rgb, cv2.COLOR_RGB2GRAY)
    luma_rgb = np.repeat(luma[:, :, None], 3, axis=2)
    body_colours = sample_source_colors(luma_rgb, grid_source_pixels)
    body_mesh = trimesh.Trimesh(
        vertices=body_vertices,
        faces=body_faces,
        vertex_colors=body_colours,
        process=False,
        maintain_order=True,
    )

    patch_colours = sample_source_colors(luma_rgb, patch_source_pixels)
    patch_mesh = trimesh.Trimesh(
        vertices=patch_vertices,
        faces=patch_faces,
        vertex_colors=patch_colours,
        process=False,
        maintain_order=True,
    )
    # A continuous heightfield glide replaces explicit edge-wall geometry.
    # The visible HRN mesh remains untouched. Only the MoGe support approaches
    # the HRN edge over a bounded pixel band, avoiding side-view voids and the
    # horizontal spikes produced by independent strip triangles.
    patch_support_depth, patch_support_mask = rasterize_patch_depth(
        subject_mask.shape,
        patch_source_pixels,
        patch_vertices[:, 2],
        patch_faces,
    )
    distances, nearest = distance_transform_edt(
        ~patch_support_mask, return_indices=True
    )
    nearest_patch_depth = patch_support_depth[tuple(nearest)]
    glide_width = max(float(args.glide_width_px), 1.0)
    glide_weight = np.clip(1.0 - distances / glide_width, 0.0, 1.0)
    glide_weight = glide_weight * glide_weight * (3.0 - 2.0 * glide_weight)
    glide_band = subject_mask & ~patch_support_mask & (glide_weight > 0.0)
    support_target = nearest_patch_depth - 0.004
    body_depth[glide_band] = (
        body_depth[glide_band] * (1.0 - glide_weight[glide_band])
        + support_target[glide_band] * glide_weight[glide_band]
    )
    glide_stats = {
        "method": "continuous MoGe heightfield approach to native HRN boundary",
        "nominal_rings": args.glide_rings,
        "width_px": glide_width,
        "band_pixels": int(glide_band.sum()),
        "explicit_edge_wall": False,
    }

    # The grid was initially built before the support glide. Refresh only its
    # depth coordinate; XY, colours, topology, and subject ownership stay fixed.
    grid_depth = cv2.resize(
        body_depth, (columns, rows), interpolation=cv2.INTER_CUBIC
    )
    body_vertices[:, 2] = grid_depth.ravel()
    body_mesh.vertices = body_vertices
    body_mesh.remove_unreferenced_vertices()
    frame_cut_mesh = None
    if args.frame_cut_backfill:
        frame_cut_mesh, frame_cut_stats = build_frame_cut_backfill(
            body_mesh,
            (source_width, source_height),
            args.frame_cut_border_px,
            args.frame_cut_back_depth,
            args.frame_cut_inset_px,
            args.frame_cut_rings,
        )
    else:
        frame_cut_stats = {"enabled": False}
    outer_glide_mesh = None
    if args.outer_glide:
        outer_glide_mesh, outer_glide_stats = build_glide_mesh(
            patch_vertices,
            patch_faces,
            patch_source_pixels,
            safe_underlay_depth,
            source_rgb,
            (source_width, source_height),
            args.glide_rings,
            args.glide_width_px,
        )
        glide_stats["outer_boundary_glide"] = outer_glide_stats

    layered_scene = trimesh.Scene()
    layered_scene.add_geometry(body_mesh, node_name="MOGE_BODY_HAIR_UNDERLAY")
    if frame_cut_mesh is not None:
        layered_scene.add_geometry(
            frame_cut_mesh, node_name="SOURCE_FRAME_CUT_BACKFILL"
        )
    if outer_glide_mesh is not None:
        layered_scene.add_geometry(
            outer_glide_mesh, node_name="HRN_OUTER_BOUNDARY_MULTI_RING_GLIDE"
        )
    layered_scene.add_geometry(patch_mesh, node_name="HRN_NATIVE_FACE_HEAD")
    glb_path = output_dir / "portrait-v33-hrn-direct-moge-layered.glb"
    layered_scene.export(glb_path)
    combined_parts = [body_mesh, patch_mesh]
    if frame_cut_mesh is not None:
        combined_parts.insert(1, frame_cut_mesh)
    if outer_glide_mesh is not None:
        combined_parts.insert(1, outer_glide_mesh)
    combined = trimesh.util.concatenate(combined_parts)
    obj_path = output_dir / "portrait-v33-hrn-direct-moge-layered.obj"
    combined.export(obj_path)

    Image.fromarray(subject_mask.astype(np.uint8) * 255, mode="L").save(
        output_dir / "01-birefnet-semantic-mask-not-depth.png"
    )
    save_depth_preview(
        output_dir / "02-moge-subject-depth-near-white.png", moge_near, subject_mask
    )
    save_depth_preview(
        output_dir / "02b-moge-subject-depth-far-white.png", 1.0 - moge_near, subject_mask
    )
    save_depth_preview(
        output_dir / "03-moge-body-underlay-depth.png", body_depth, body_mask
    )
    Image.fromarray(patch_footprint.astype(np.uint8) * 255, mode="L").save(
        output_dir / "04-hrn-native-patch-footprint.png"
    )
    Image.fromarray(np.round(glide_weight * 255.0).astype(np.uint8), mode="L").save(
        output_dir / "05-hrn-moge-glide-weight.png"
    )
    Image.fromarray(np.round(shoulder_weight * 255.0).astype(np.uint8), mode="L").save(
        output_dir / "06-shoulder-depth-boost-weight.png"
    )

    result_stats = {
        "method": "native HRN face/head plus subject-normalized MoGe body/hair underlay",
        "model_roles": {
            "semantic_mask_not_depth": "BiRefNet Portrait",
            "metric_depth": "MoGe-2 ViT-L on original opaque image",
            "face_head_geometry": "Official ModelScope HRN Head v0.1 native mesh",
        },
        "source_separation": {
            "moge_input": "original opaque upscaled photograph",
            "geometry_silhouette": "largest connected BiRefNet alpha component",
            "appearance": "grayscale luma sampled from prepared portrait",
        },
        "alpha": alpha_stats,
        "quality_gates": {
            "finite_subject_depth": True,
            "minimum_metric_p99_p1_span": args.minimum_subject_depth_span,
            "measured_metric_p99_p1_span": metric_span,
            "passed": True,
        },
        "subject_metric_depth_percentiles_p1_p5_p50_p95_p99": (
            subject_metric_percentiles.tolist()
        ),
        "composition": {
            "grid": [columns, rows],
            "body_depth_span": args.body_depth_span,
            "body_base_depth": args.body_base_depth,
            "shoulder_depth": {
                "boost": args.shoulder_depth_boost,
                "start_factor": args.shoulder_start_factor,
                "peak_factor": args.shoulder_peak_factor,
                "end_factor": args.shoulder_end_factor,
                "weighted_pixels": int((shoulder_weight > 0.0).sum()),
            },
            "seam_rows": [seam_top, seam_bottom],
            "patch_overlap_px": args.patch_overlap_px,
            "glide": glide_stats,
            "patch_z_translation": patch_translation,
            "safe_head_underlay_depth": safe_underlay_depth,
            "closed_head_hair_mode": args.closed_head_hair_mode,
            "frame_cut_backfill": frame_cut_stats,
        },
        "meshes": {
            "body_vertices": int(len(body_mesh.vertices)),
            "body_triangles": int(len(body_mesh.faces)),
            "hrn_vertices": int(len(patch_mesh.vertices)),
            "hrn_triangles": int(len(patch_mesh.faces)),
            "frame_cut_vertices": int(len(frame_cut_mesh.vertices)) if frame_cut_mesh is not None else 0,
            "frame_cut_triangles": int(len(frame_cut_mesh.faces)) if frame_cut_mesh is not None else 0,
            "outer_glide_vertices": int(len(outer_glide_mesh.vertices)) if outer_glide_mesh is not None else 0,
            "outer_glide_triangles": int(len(outer_glide_mesh.faces)) if outer_glide_mesh is not None else 0,
        },
        "outputs": {"glb": glb_path.name, "obj": obj_path.name},
    }
    (output_dir / "portrait-v33-composition-stats.json").write_text(
        json.dumps(result_stats, indent=2), encoding="utf-8"
    )
    print(
        "PORTRAIT_V33_COMPOSE_OK "
        f"MoGe subject span {metric_span:.4f}; "
        f"body {len(body_mesh.faces):,} tris; HRN {len(patch_mesh.faces):,} tris"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
