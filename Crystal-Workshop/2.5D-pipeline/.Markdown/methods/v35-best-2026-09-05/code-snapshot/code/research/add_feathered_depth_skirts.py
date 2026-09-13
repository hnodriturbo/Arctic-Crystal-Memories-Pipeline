"""
File: code/research/add_feathered_depth_skirts.py
Purpose:
 - Build multi-ring silhouette skirts with a smooth human-to-scene depth transition.
 - Feather the rear edge outward over the MoGe scene layer to cover sampling gaps.
 - Preserve true internal occlusion openings while smoothing unwanted edge banding.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import trimesh

from add_silhouette_depth_skirts import scene_xy_to_source_pixels, sample_depth


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fusion-dir", required=True, type=Path)
    parser.add_argument("--scene-depth-raw", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--minimum-skirt-depth", type=float, default=0.025)
    parser.add_argument("--feather-width-px", type=float, default=9.0)
    parser.add_argument("--scene-sample-offset-px", type=float, default=3.0)
    parser.add_argument("--feather-rings", type=int, default=9)
    parser.add_argument("--depth-smoothing-iterations", type=int, default=18)
    parser.add_argument("--depth-smoothing-weight", type=float, default=0.55)
    return parser.parse_args()


def smoothstep(values: np.ndarray) -> np.ndarray:
    values = np.clip(values, 0.0, 1.0)
    return values * values * (3.0 - 2.0 * values)


def boundary_geometry(
    mesh: trimesh.Trimesh,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Return boundary ids/edges and per-vertex normals pointing away from mesh faces."""
    faces = np.asarray(mesh.faces, dtype=np.int64)
    directed_edges = np.vstack((faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]))
    third_vertices = np.concatenate((faces[:, 2], faces[:, 0], faces[:, 1]))
    sorted_edges = np.sort(directed_edges, axis=1)
    _, inverse, counts = np.unique(sorted_edges, axis=0, return_inverse=True, return_counts=True)
    boundary_occurrences = counts[inverse] == 1
    boundary_edges = directed_edges[boundary_occurrences]
    adjacent_third = third_vertices[boundary_occurrences]

    boundary_ids = np.unique(boundary_edges)
    local_ids = np.full(len(mesh.vertices), -1, dtype=np.int64)
    local_ids[boundary_ids] = np.arange(len(boundary_ids))
    edge_local = local_ids[boundary_edges]

    vertices_xy = np.asarray(mesh.vertices, dtype=np.float64)[:, :2]
    edge_vectors = vertices_xy[boundary_edges[:, 1]] - vertices_xy[boundary_edges[:, 0]]
    edge_normals = np.column_stack((-edge_vectors[:, 1], edge_vectors[:, 0]))
    lengths = np.linalg.norm(edge_normals, axis=1)
    edge_normals /= np.maximum(lengths[:, None], 1e-12)
    midpoints = 0.5 * (
        vertices_xy[boundary_edges[:, 0]] + vertices_xy[boundary_edges[:, 1]]
    )
    toward_face = vertices_xy[adjacent_third] - midpoints
    points_into_face = np.einsum("ij,ij->i", edge_normals, toward_face) > 0.0
    edge_normals[points_into_face] *= -1.0

    outward = np.zeros((len(boundary_ids), 2), dtype=np.float64)
    np.add.at(outward, edge_local[:, 0], edge_normals)
    np.add.at(outward, edge_local[:, 1], edge_normals)
    outward /= np.maximum(np.linalg.norm(outward, axis=1)[:, None], 1e-12)
    return boundary_ids, edge_local, outward, boundary_edges


def smooth_boundary_values(
    values: np.ndarray,
    edges: np.ndarray,
    iterations: int,
    weight: float,
) -> np.ndarray:
    """Laplacian-smooth scalar values only along their connected boundary chains."""
    result = np.asarray(values, dtype=np.float64).copy()
    if iterations <= 0 or len(result) == 0:
        return result
    degree = np.zeros(len(result), dtype=np.float64)
    np.add.at(degree, edges[:, 0], 1.0)
    np.add.at(degree, edges[:, 1], 1.0)
    for _ in range(iterations):
        neighbor_sum = np.zeros(len(result), dtype=np.float64)
        np.add.at(neighbor_sum, edges[:, 0], result[edges[:, 1]])
        np.add.at(neighbor_sum, edges[:, 1], result[edges[:, 0]])
        neighbor_mean = neighbor_sum / np.maximum(degree, 1.0)
        result = result * (1.0 - weight) + neighbor_mean * weight
    return result


def smooth_boundary_vectors(
    vectors: np.ndarray,
    edges: np.ndarray,
    iterations: int,
    weight: float,
) -> np.ndarray:
    """Smooth and renormalize outward XY directions along boundary chains."""
    x = smooth_boundary_values(vectors[:, 0], edges, iterations, weight)
    y = smooth_boundary_values(vectors[:, 1], edges, iterations, weight)
    result = np.column_stack((x, y))
    return result / np.maximum(np.linalg.norm(result, axis=1)[:, None], 1e-12)


def build_feathered_skirt(
    human_mesh: trimesh.Trimesh,
    depth: np.ndarray,
    source_size: tuple[int, int],
    global_anchor: float,
    depth_scale: float,
    minimum_skirt_depth: float,
    feather_width_px: float,
    scene_sample_offset_px: float,
    feather_rings: int,
    smoothing_iterations: int,
    smoothing_weight: float,
) -> tuple[trimesh.Trimesh, dict]:
    if feather_rings < 2:
        raise ValueError("feather_rings must be at least 2")
    if feather_width_px < 0.0:
        raise ValueError("feather_width_px cannot be negative")
    if not 0.0 <= smoothing_weight <= 1.0:
        raise ValueError("smoothing_weight must be between 0 and 1")

    boundary_ids, edge_local, outward, _ = boundary_geometry(human_mesh)
    outward = smooth_boundary_vectors(outward, edge_local, max(4, smoothing_iterations), 0.42)
    front = np.asarray(human_mesh.vertices, dtype=np.float64)[boundary_ids]
    scene_units_per_pixel = 2.0 / (source_size[1] - 1)
    sample_xy = front[:, :2] + outward * scene_sample_offset_px * scene_units_per_pixel
    rear_pixels = scene_xy_to_source_pixels(sample_xy, source_size)
    raw_depth = sample_depth(depth, rear_pixels)
    sampled_scene_z = (global_anchor - raw_depth) * depth_scale
    raw_skirt_depth = np.maximum(front[:, 2] - sampled_scene_z, minimum_skirt_depth)
    smoothed_depth = smooth_boundary_values(
        raw_skirt_depth,
        edge_local,
        smoothing_iterations,
        smoothing_weight,
    )
    smoothed_depth = np.maximum(smoothed_depth, minimum_skirt_depth)

    ring_t = np.linspace(0.0, 1.0, feather_rings, dtype=np.float64)
    xy_blend = smoothstep(ring_t) ** 0.72
    z_blend = smoothstep(ring_t)
    rings = []
    for xy_amount, z_amount in zip(xy_blend, z_blend, strict=True):
        ring = front.copy()
        # The feather folds underneath the accepted front silhouette. The rear
        # scene underlap closes the join from behind without creating a front halo.
        ring[:, :2] = front[:, :2] - outward * (
            feather_width_px * scene_units_per_pixel * xy_amount
        )
        ring[:, 2] = front[:, 2] - smoothed_depth * z_amount
        rings.append(ring)
    vertices = np.vstack(rings)

    boundary_count = len(boundary_ids)
    faces = []
    for ring_index in range(feather_rings - 1):
        current = edge_local + ring_index * boundary_count
        following = edge_local + (ring_index + 1) * boundary_count
        faces.append(np.column_stack((current[:, 0], current[:, 1], following[:, 1])))
        faces.append(np.column_stack((current[:, 0], following[:, 1], following[:, 0])))
    skirt_faces = np.vstack(faces)

    source_colors = np.asarray(human_mesh.visual.vertex_colors)[boundary_ids]
    colors = np.tile(source_colors, (feather_rings, 1))
    skirt = trimesh.Trimesh(
        vertices=vertices,
        faces=skirt_faces,
        process=False,
        maintain_order=True,
        vertex_colors=colors,
    )
    return skirt, {
        "boundary_edges": int(len(edge_local)),
        "boundary_vertices": int(boundary_count),
        "feather_rings": int(feather_rings),
        "feather_width_px": float(feather_width_px),
        "scene_sample_offset_px": float(scene_sample_offset_px),
        "triangles": int(len(skirt_faces)),
        "raw_skirt_depth_min": float(raw_skirt_depth.min()),
        "raw_skirt_depth_median": float(np.median(raw_skirt_depth)),
        "raw_skirt_depth_max": float(raw_skirt_depth.max()),
        "smoothed_skirt_depth_min": float(smoothed_depth.min()),
        "smoothed_skirt_depth_median": float(np.median(smoothed_depth)),
        "smoothed_skirt_depth_max": float(smoothed_depth.max()),
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
        "method": "multi-ring feathered silhouette skirt with smoothed MoGe rear-depth overlap",
        "status": "candidate",
        "source_size": list(source_size),
        "minimum_skirt_depth": args.minimum_skirt_depth,
        "feather_width_px": args.feather_width_px,
        "scene_sample_offset_px": args.scene_sample_offset_px,
        "feather_rings": args.feather_rings,
        "depth_smoothing_iterations": args.depth_smoothing_iterations,
        "depth_smoothing_weight": args.depth_smoothing_weight,
        "natural_internal_gaps_preserved": True,
        "front_surface_modified": False,
        "subjects": {},
    }
    for subject in ("man", "woman"):
        human_name = f"{subject}_source_camera_scene_anchored.obj"
        human = trimesh.load(fusion_dir / human_name, force="mesh", process=False, maintain_order=True)
        human.export(output_dir / human_name)
        skirt, subject_stats = build_feathered_skirt(
            human,
            depth,
            source_size,
            global_anchor,
            depth_scale,
            args.minimum_skirt_depth,
            args.feather_width_px,
            args.scene_sample_offset_px,
            args.feather_rings,
            args.depth_smoothing_iterations,
            args.depth_smoothing_weight,
        )
        skirt_name = f"{subject}_feathered_depth_skirt.obj"
        skirt.export(output_dir / skirt_name)
        skirt.export(output_dir / f"{subject}_feathered_depth_skirt.glb")
        meshes[subject] = human
        meshes[f"{subject}_feathered_skirt"] = skirt
        stats["subjects"][subject] = subject_stats

    combined = trimesh.util.concatenate(list(meshes.values()))
    combined.export(output_dir / "both_people_scene_with_feathered_depth_skirts.obj")
    combined_scene = trimesh.Scene()
    for name, mesh in meshes.items():
        combined_scene.add_geometry(mesh, node_name=name, geom_name=name)
    combined_scene.export(output_dir / "both_people_scene_with_feathered_depth_skirts.glb")
    stats["combined"] = {
        "vertices": int(len(combined.vertices)),
        "triangles": int(len(combined.faces)),
        "bounds": combined.bounds.tolist(),
    }
    (output_dir / "feathered_depth_skirt_stats.json").write_text(
        json.dumps(stats, indent=2), encoding="utf-8"
    )
    print(
        f"[feathered-depth-skirt] combined {len(combined.vertices):,} vertices / "
        f"{len(combined.faces):,} triangles"
    )


if __name__ == "__main__":
    main()
