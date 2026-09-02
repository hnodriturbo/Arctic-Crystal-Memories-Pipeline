"""
File: code/research/add_silhouette_depth_skirts.py
Purpose:
 - Connect human boundary edges backward toward the MoGe scene depth with short ruled surfaces.
 - Preserve outer silhouettes and natural internal openings while hiding empty side-view gaps.
 - Implement the AC3D-inspired "strekking" hypothesis as a measurable optional layer.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import trimesh


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fusion-dir", required=True, type=Path)
    parser.add_argument("--scene-depth-raw", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--minimum-skirt-depth", type=float, default=0.025)
    return parser.parse_args()


def scene_xy_to_source_pixels(xy: np.ndarray, source_size: tuple[int, int]) -> np.ndarray:
    width, height = source_size
    half_height = (height - 1) * 0.5
    return np.column_stack(
        (xy[:, 0] * half_height + (width - 1) * 0.5, (height - 1) * 0.5 - xy[:, 1] * half_height)
    )


def sample_depth(depth: np.ndarray, pixels: np.ndarray) -> np.ndarray:
    height, width = depth.shape
    x = np.clip(pixels[:, 0], 0.0, width - 1)
    y = np.clip(pixels[:, 1], 0.0, height - 1)
    x0 = np.floor(x).astype(np.int64)
    y0 = np.floor(y).astype(np.int64)
    x1 = np.minimum(x0 + 1, width - 1)
    y1 = np.minimum(y0 + 1, height - 1)
    fx = x - x0
    fy = y - y0
    top = depth[y0, x0] * (1.0 - fx) + depth[y0, x1] * fx
    bottom = depth[y1, x0] * (1.0 - fx) + depth[y1, x1] * fx
    return top * (1.0 - fy) + bottom * fy


def build_skirt(
    human_mesh: trimesh.Trimesh,
    depth: np.ndarray,
    source_size: tuple[int, int],
    global_anchor: float,
    depth_scale: float,
    minimum_skirt_depth: float,
) -> tuple[trimesh.Trimesh, dict]:
    sorted_edges = np.sort(np.asarray(human_mesh.edges, dtype=np.int64), axis=1)
    unique_edges, edge_counts = np.unique(sorted_edges, axis=0, return_counts=True)
    boundary_edges = unique_edges[edge_counts == 1]
    boundary_ids = np.unique(boundary_edges)
    local_ids = np.full(len(human_mesh.vertices), -1, dtype=np.int64)
    local_ids[boundary_ids] = np.arange(len(boundary_ids))
    front = np.asarray(human_mesh.vertices)[boundary_ids]
    pixels = scene_xy_to_source_pixels(front[:, :2], source_size)
    raw_depth = sample_depth(depth, pixels)
    back = front.copy()
    moge_scene_z = (global_anchor - raw_depth) * depth_scale
    back[:, 2] = np.minimum(moge_scene_z, front[:, 2] - minimum_skirt_depth)
    vertices = np.vstack((front, back))
    edge_local = local_ids[boundary_edges]
    count = len(boundary_ids)
    faces = np.empty((len(edge_local) * 2, 3), dtype=np.int64)
    faces[0::2] = np.column_stack((edge_local[:, 0], edge_local[:, 1], edge_local[:, 1] + count))
    faces[1::2] = np.column_stack(
        (edge_local[:, 0], edge_local[:, 1] + count, edge_local[:, 0] + count)
    )
    source_colors = np.asarray(human_mesh.visual.vertex_colors)[boundary_ids]
    colors = np.vstack((source_colors, source_colors))
    skirt = trimesh.Trimesh(
        vertices=vertices,
        faces=faces,
        process=False,
        maintain_order=True,
        vertex_colors=colors,
    )
    skirt_depths = front[:, 2] - back[:, 2]
    return skirt, {
        "boundary_edges": int(len(boundary_edges)),
        "boundary_vertices": int(len(boundary_ids)),
        "triangles": int(len(faces)),
        "skirt_depth_min": float(skirt_depths.min()),
        "skirt_depth_median": float(np.median(skirt_depths)),
        "skirt_depth_max": float(skirt_depths.max()),
    }


def main() -> None:
    args = parse_arguments()
    fusion_dir = args.fusion_dir.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    parent = json.loads((fusion_dir / "scene_fusion_stats.json").read_text(encoding="utf-8"))
    depth = np.load(args.scene_depth_raw).astype(np.float32)
    source_size = tuple(parent["source_size"])
    depth_scale = 1.0 / parent["raw_depth_units_per_scene_unit"]
    global_anchor = parent["global_human_depth_anchor"]

    meshes = {}
    scene = trimesh.load(fusion_dir / "scene_depth_layer.obj", force="mesh", process=False)
    scene.export(output_dir / "scene_depth_layer.obj")
    meshes["scene_depth"] = scene
    stats = {
        "method": "silhouette depth skirt from each human boundary toward sampled MoGe scene depth",
        "status": "candidate",
        "source_size": list(source_size),
        "minimum_skirt_depth": args.minimum_skirt_depth,
        "natural_internal_gaps_preserved": True,
        "subjects": {},
    }
    for subject in ("man", "woman"):
        human_name = f"{subject}_source_camera_scene_anchored.obj"
        human = trimesh.load(fusion_dir / human_name, force="mesh", process=False, maintain_order=True)
        human.export(output_dir / human_name)
        skirt, subject_stats = build_skirt(
            human,
            depth,
            source_size,
            global_anchor,
            depth_scale,
            args.minimum_skirt_depth,
        )
        skirt_name = f"{subject}_silhouette_depth_skirt.obj"
        skirt.export(output_dir / skirt_name)
        skirt.export(output_dir / f"{subject}_silhouette_depth_skirt.glb")
        meshes[subject] = human
        meshes[f"{subject}_skirt"] = skirt
        stats["subjects"][subject] = subject_stats

    combined = trimesh.util.concatenate(list(meshes.values()))
    combined.export(output_dir / "both_people_scene_with_depth_skirts.obj")
    combined_scene = trimesh.Scene()
    for name, mesh in meshes.items():
        combined_scene.add_geometry(mesh, node_name=name, geom_name=name)
    combined_scene.export(output_dir / "both_people_scene_with_depth_skirts.glb")
    stats["combined"] = {
        "vertices": int(len(combined.vertices)),
        "triangles": int(len(combined.faces)),
        "bounds": combined.bounds.tolist(),
    }
    (output_dir / "silhouette_depth_skirt_stats.json").write_text(
        json.dumps(stats, indent=2), encoding="utf-8"
    )
    print(
        f"[depth-skirt] combined {len(combined.vertices):,} vertices / "
        f"{len(combined.faces):,} triangles"
    )


if __name__ == "__main__":
    main()
