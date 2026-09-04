"""
File: code/research/add_portrait_silhouette_backfill.py
Purpose:
 - Smooth only the outermost Z boundary of an open portrait relief.
 - Add an AC3D-like multi-ring silhouette backfill behind the accepted front surface.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import trimesh


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--rings", type=int, default=8)
    parser.add_argument("--inset", type=float, default=0.65)
    parser.add_argument("--minimum-depth", type=float, default=0.35)
    parser.add_argument("--maximum-depth", type=float, default=3.0)
    parser.add_argument("--smoothing-iterations", type=int, default=32)
    parser.add_argument("--smoothing-weight", type=float, default=0.52)
    return parser.parse_args()


def smoothstep(values: np.ndarray) -> np.ndarray:
    values = np.clip(values, 0.0, 1.0)
    return values * values * (3.0 - 2.0 * values)


def boundary_data(mesh: trimesh.Trimesh) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    faces = np.asarray(mesh.faces, dtype=np.int64)
    directed = np.vstack((faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]))
    thirds = np.concatenate((faces[:, 2], faces[:, 0], faces[:, 1]))
    sorted_edges = np.sort(directed, axis=1)
    _, inverse, counts = np.unique(sorted_edges, axis=0, return_inverse=True, return_counts=True)
    selected = counts[inverse] == 1
    edges = directed[selected]
    thirds = thirds[selected]
    ids = np.unique(edges)
    local = np.full(len(mesh.vertices), -1, dtype=np.int64)
    local[ids] = np.arange(len(ids))
    local_edges = local[edges]

    xy = np.asarray(mesh.vertices, dtype=np.float64)[:, :2]
    vectors = xy[edges[:, 1]] - xy[edges[:, 0]]
    normals = np.column_stack((-vectors[:, 1], vectors[:, 0]))
    normals /= np.maximum(np.linalg.norm(normals, axis=1)[:, None], 1e-12)
    midpoints = 0.5 * (xy[edges[:, 0]] + xy[edges[:, 1]])
    into_face = np.einsum("ij,ij->i", normals, xy[thirds] - midpoints) > 0.0
    normals[into_face] *= -1.0
    outward = np.zeros((len(ids), 2), dtype=np.float64)
    np.add.at(outward, local_edges[:, 0], normals)
    np.add.at(outward, local_edges[:, 1], normals)
    outward /= np.maximum(np.linalg.norm(outward, axis=1)[:, None], 1e-12)
    return ids, local_edges, outward


def smooth_values(values: np.ndarray, edges: np.ndarray, iterations: int, weight: float) -> np.ndarray:
    result = np.asarray(values, dtype=np.float64).copy()
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


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    front = trimesh.load(args.input, force="mesh", process=False, maintain_order=True)
    boundary_ids, local_edges, outward = boundary_data(front)
    vertices = np.asarray(front.vertices, dtype=np.float64).copy()
    original_boundary_z = vertices[boundary_ids, 2].copy()
    smoothed_boundary_z = smooth_values(
        original_boundary_z,
        local_edges,
        args.smoothing_iterations,
        args.smoothing_weight,
    )
    # Repair only the single outermost vertex row; all interior face geometry stays native.
    vertices[boundary_ids, 2] = smoothed_boundary_z
    front.vertices = vertices

    global_rear = float(np.percentile(vertices[:, 2], 1.0))
    front_boundary = vertices[boundary_ids].copy()
    requested_depth = np.maximum(smoothed_boundary_z - global_rear, args.minimum_depth)
    bounded_depth = np.clip(requested_depth, args.minimum_depth, args.maximum_depth)
    rear_z = smoothed_boundary_z - bounded_depth
    ring_t = np.linspace(0.0, 1.0, args.rings)
    rings = []
    for amount in ring_t:
        eased = smoothstep(np.asarray(amount)).item()
        ring = front_boundary.copy()
        ring[:, :2] -= outward * args.inset * eased
        ring[:, 2] = smoothed_boundary_z * (1.0 - eased) + rear_z * eased
        rings.append(ring)
    skirt_vertices = np.vstack(rings)
    count = len(boundary_ids)
    skirt_faces = []
    for index in range(args.rings - 1):
        current = local_edges + index * count
        following = local_edges + (index + 1) * count
        skirt_faces.append(np.column_stack((current[:, 0], current[:, 1], following[:, 1])))
        skirt_faces.append(np.column_stack((current[:, 0], following[:, 1], following[:, 0])))
    skirt_faces = np.vstack(skirt_faces)
    colors = np.asarray(front.visual.vertex_colors)[boundary_ids]
    skirt = trimesh.Trimesh(
        vertices=skirt_vertices,
        faces=skirt_faces,
        vertex_colors=np.tile(colors, (args.rings, 1)),
        process=False,
        maintain_order=True,
    )

    front.export(output_dir / "portrait-front-boundary-repaired.obj")
    skirt.export(output_dir / "portrait-silhouette-backfill.obj")
    scene = trimesh.Scene()
    scene.add_geometry(front, node_name="portrait_front", geom_name="portrait_front")
    scene.add_geometry(skirt, node_name="silhouette_backfill", geom_name="silhouette_backfill")
    scene.export(output_dir / "portrait-with-silhouette-backfill.glb")
    combined = trimesh.util.concatenate((front, skirt))
    combined.export(output_dir / "portrait-with-silhouette-backfill.obj")

    stats = {
        "method": "outer-boundary smoothing plus multi-ring silhouette backfill",
        "front_surface_interior_modified": False,
        "front_boundary_vertices_modified": int(len(boundary_ids)),
        "boundary_triangles": int(len(skirt.faces)),
        "rings": args.rings,
        "inset": args.inset,
        "minimum_depth": args.minimum_depth,
        "maximum_depth": args.maximum_depth,
        "boundary_z_change": {
            "median": float(np.median(np.abs(smoothed_boundary_z - original_boundary_z))),
            "maximum": float(np.max(np.abs(smoothed_boundary_z - original_boundary_z))),
        },
        "combined": {
            "vertices": int(len(combined.vertices)),
            "triangles": int(len(combined.faces)),
        },
    }
    (output_dir / "portrait-backfill-stats.json").write_text(
        json.dumps(stats, indent=2), encoding="utf-8"
    )
    print(
        f"PORTRAIT_BACKFILL_OK {len(combined.vertices):,} vertices / "
        f"{len(combined.faces):,} triangles"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
