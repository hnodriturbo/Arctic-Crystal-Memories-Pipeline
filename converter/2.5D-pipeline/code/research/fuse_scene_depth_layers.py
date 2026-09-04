"""
File: code/research/fuse_scene_depth_layers.py
Purpose:
 - Combine accepted source-camera human surfaces with MoGe depth for the rest of the image.
 - Preserve natural holes in human masks so the deeper scene remains visible through them.
 - Keep human local detail intact while using MoGe only for macro placement and non-human layers.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
import trimesh
from PIL import Image, ImageDraw

from source_camera_fusion import apply_affine, sample_source_colors, source_pixels_to_scene


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--scene-depth-raw", required=True, type=Path)
    parser.add_argument("--human-stats", required=True, type=Path)
    parser.add_argument("--human-mesh-dir", required=True, type=Path)
    parser.add_argument("--raw-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--stride", type=int, default=3)
    parser.add_argument("--scene-depth-span", type=float, default=0.35)
    parser.add_argument("--clip-percent", type=float, default=1.0)
    parser.add_argument("--boundary-clearance-px", type=int, default=2)
    parser.add_argument(
        "--scene-underlap-px",
        type=int,
        default=0,
        help="Extend the rear scene under the human edge to close sampling gaps from behind.",
    )
    return parser.parse_args()


def sample_axis(length: int, stride: int) -> np.ndarray:
    values = np.arange(0, length, stride, dtype=np.int32)
    if values[-1] != length - 1:
        values = np.append(values, length - 1)
    return values


def build_faces(valid: np.ndarray) -> np.ndarray:
    indices = np.full(valid.shape, -1, dtype=np.int64)
    indices[valid] = np.arange(int(valid.sum()))
    quads_valid = valid[:-1, :-1] & valid[1:, :-1] & valid[1:, 1:] & valid[:-1, 1:]
    rows, columns = np.where(quads_valid)
    quads = np.column_stack(
        (
            indices[rows, columns],
            indices[rows + 1, columns],
            indices[rows + 1, columns + 1],
            indices[rows, columns + 1],
        )
    )
    return trimesh.geometry.triangulate_quads(quads)


def build_layer_overlay(source: np.ndarray, masks: dict[str, np.ndarray], output_path: Path) -> None:
    overlay = np.round(source * 0.48).astype(np.uint8)
    palette = {"man": np.array([38, 203, 255]), "woman": np.array([255, 88, 166])}
    for subject, mask in masks.items():
        color = palette.get(subject, np.array([255, 209, 64]))
        overlay[mask] = np.round(source[mask] * 0.65 + color * 0.35).astype(np.uint8)
        contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(overlay, contours, -1, tuple(int(v) for v in color), 2, cv2.LINE_AA)
    image = Image.fromarray(overlay)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((14, 14, 445, 76), radius=8, fill=(0, 0, 0, 190))
    draw.text((26, 24), "cyan/magenta = accepted human geometry", fill="white")
    draw.text((26, 49), "dark source = MoGe rest-of-image depth layer", fill="white")
    image.save(output_path, optimize=True)


def main() -> None:
    args = parse_arguments()
    if args.stride < 1:
        raise ValueError("--stride must be at least 1")
    if args.boundary_clearance_px > 0 and args.scene_underlap_px > 0:
        raise ValueError("boundary clearance and scene underlap cannot both be enabled")
    with Image.open(args.source) as source_image:
        source_image.load()
        source = np.array(source_image.convert("RGB"))
        source_alpha = (
            np.array(source_image.convert("RGBA").getchannel("A")) >= 128
            if source_image.mode in ("RGBA", "LA") or "transparency" in source_image.info
            else np.ones((source_image.height, source_image.width), dtype=bool)
        )
    height, width = source.shape[:2]
    depth = np.load(args.scene_depth_raw).astype(np.float32)
    if depth.shape != (height, width):
        raise RuntimeError(f"Depth {depth.shape} does not match source {(height, width)}")
    human_stats = json.loads(args.human_stats.read_text(encoding="utf-8"))
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    subject_masks = {}
    for subject, subject_stats in human_stats["subjects"].items():
        raw_mask = np.load(args.raw_dir / f"{subject}_icon_front_raw.npz")["mask"].astype(np.uint8)
        affine = np.asarray(subject_stats["affine_raw_px_to_source_px"], dtype=np.float64)
        subject_masks[subject] = cv2.warpAffine(
            raw_mask,
            affine,
            (width, height),
            flags=cv2.INTER_NEAREST,
        ).astype(bool)
    human_union = np.logical_or.reduce(list(subject_masks.values()))
    if args.scene_underlap_px > 0:
        kernel_size = args.scene_underlap_px * 2 + 1
        clearance_mask = cv2.erode(
            human_union.astype(np.uint8), np.ones((kernel_size, kernel_size), np.uint8)
        ).astype(bool)
    elif args.boundary_clearance_px > 0:
        kernel_size = args.boundary_clearance_px * 2 + 1
        clearance_mask = cv2.dilate(
            human_union.astype(np.uint8), np.ones((kernel_size, kernel_size), np.uint8)
        ).astype(bool)
    else:
        clearance_mask = human_union

    finite = np.isfinite(depth)
    low, high = np.percentile(
        depth[finite], [args.clip_percent, 100.0 - args.clip_percent]
    )
    depth_scale = args.scene_depth_span / (high - low)
    global_human_anchor = float(np.median(depth[human_union]))

    rows = sample_axis(height, args.stride)
    columns = sample_axis(width, args.stride)
    grid_columns, grid_rows = np.meshgrid(columns, rows)
    valid = (
        (~clearance_mask[grid_rows, grid_columns])
        & finite[grid_rows, grid_columns]
        & source_alpha[grid_rows, grid_columns]
    )
    sampled_pixels = np.column_stack((grid_columns[valid], grid_rows[valid])).astype(np.float64)
    scene_xy = source_pixels_to_scene(sampled_pixels, (width, height))
    scene_z = (global_human_anchor - depth[grid_rows[valid], grid_columns[valid]]) * depth_scale
    scene_vertices = np.column_stack((scene_xy, scene_z))
    scene_colors = sample_source_colors(source, sampled_pixels)
    scene_faces = build_faces(valid)
    scene_mesh = trimesh.Trimesh(
        vertices=scene_vertices,
        faces=scene_faces,
        process=False,
        maintain_order=True,
        vertex_colors=scene_colors,
    )
    scene_obj = output_dir / "scene_depth_layer.obj"
    scene_glb = output_dir / "scene_depth_layer.glb"
    scene_mesh.export(scene_obj)
    scene_mesh.export(scene_glb)

    meshes = {"scene_depth": scene_mesh}
    subject_offsets = {}
    for subject, mask in subject_masks.items():
        mesh = trimesh.load(
            args.human_mesh_dir / human_stats["subjects"][subject]["output_obj"],
            force="mesh",
            process=False,
            maintain_order=True,
        )
        subject_depth_anchor = float(np.median(depth[mask]))
        offset = (global_human_anchor - subject_depth_anchor) * depth_scale
        mesh.vertices[:, 2] += offset
        meshes[subject] = mesh
        subject_offsets[subject] = {
            "moge_median_depth": subject_depth_anchor,
            "scene_z_offset": float(offset),
        }
        mesh.export(output_dir / f"{subject}_source_camera_scene_anchored.obj")

    combined = trimesh.util.concatenate(list(meshes.values()))
    combined_obj = output_dir / "both_people_with_scene_depth.obj"
    combined.export(combined_obj)
    combined_scene = trimesh.Scene()
    for name, mesh in meshes.items():
        combined_scene.add_geometry(mesh, node_name=name, geom_name=name)
    combined_glb = output_dir / "both_people_with_scene_depth.glb"
    combined_scene.export(combined_glb)

    layer_overlay = output_dir / "human_and_scene_layer_overlay.png"
    build_layer_overlay(source, subject_masks, layer_overlay)
    stats = {
        "method": "accepted human front surfaces plus MoGe rest-of-image depth layer",
        "source_size": [width, height],
        "stride": args.stride,
        "boundary_clearance_px": args.boundary_clearance_px,
        "scene_underlap_px": args.scene_underlap_px,
        "scene_depth_span": args.scene_depth_span,
        "raw_depth_percentiles": {"low": float(low), "high": float(high)},
        "raw_depth_units_per_scene_unit": float(1.0 / depth_scale),
        "global_human_depth_anchor": global_human_anchor,
        "subject_offsets": subject_offsets,
        "natural_internal_gaps_preserved": True,
        "source_alpha_respected": bool(not source_alpha.all()),
        "scene": {
            "vertices": int(len(scene_mesh.vertices)),
            "triangles": int(len(scene_mesh.faces)),
            "components": int(len(scene_mesh.split(only_watertight=False))),
            "bounds": scene_mesh.bounds.tolist(),
        },
        "combined": {
            "vertices": int(len(combined.vertices)),
            "triangles": int(len(combined.faces)),
            "bounds": combined.bounds.tolist(),
            "obj": combined_obj.name,
            "glb": combined_glb.name,
        },
        "layer_overlay": layer_overlay.name,
    }
    (output_dir / "scene_fusion_stats.json").write_text(
        json.dumps(stats, indent=2), encoding="utf-8"
    )
    print(
        f"[scene-fusion] scene {len(scene_mesh.vertices):,} vertices / "
        f"{len(scene_mesh.faces):,} triangles; combined {len(combined.faces):,} triangles"
    )


if __name__ == "__main__":
    main()
