"""
Purpose:
 - Make a controlled scalp-only depth smoothing trial for Pabbi-Bleikja.
 - Preserve source XY, topology and every vertex outside the manual scalp region.
Context: This image-specific experiment is not an automatic bald-head detector.
"""

import argparse
import json
from pathlib import Path

import numpy as np
import trimesh
from scipy import sparse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mesh', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    mesh = trimesh.load(args.mesh, force='mesh', process=False)
    original = mesh.vertices.copy()
    # Source-camera coordinates use image height 2. Recover original pixel centres.
    x = original[:, 0] * (1800 - 1) / 2 + (1319 - 1) / 2
    y = (1 - original[:, 1]) * (1800 - 1) / 2
    # The oblique lower boundary stays above the eyes and visible ear.
    lower = 182 + .16 * (x - 380)
    weight = np.clip((lower - y) / 30, 0, 1)
    weight *= np.clip((x - 360) / 18, 0, 1) * np.clip((660 - x) / 18, 0, 1)
    edges = mesh.edges_unique
    rows = np.concatenate((edges[:, 0], edges[:, 1]))
    cols = np.concatenate((edges[:, 1], edges[:, 0]))
    adjacency = sparse.csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(len(x), len(x)))
    degrees = np.maximum(np.asarray(adjacency.sum(axis=1)).ravel(), 1)
    z = original[:, 2].copy()
    # Convex neighbour averaging removes local spikes without introducing overshoot.
    for _ in range(100):
        z += .45 * weight * (adjacency @ z / degrees - z)
    mesh.vertices[:, 2] = z
    assert np.array_equal(mesh.vertices[:, :2], original[:, :2])
    assert np.array_equal(mesh.vertices[weight == 0], original[weight == 0])
    output = args.output_dir / 'person_01_smooth_scalp.glb'
    mesh.export(output)
    restored = trimesh.load(output, force='mesh', process=False)
    assert np.array_equal(restored.faces, mesh.faces)
    assert np.allclose(restored.vertices, mesh.vertices, atol=1e-7)
    report = {
        'source': str(args.mesh.resolve()), 'manual_image_specific_region': True,
        'source_image_size': [1319, 1800], 'iterations': 100,
        'vertices': len(x), 'triangles': len(mesh.faces),
        'changed_vertices': int(np.count_nonzero(z != original[:, 2])),
        'max_depth_change_at_80mm_subject_height': float(np.max(abs(z-original[:, 2])) * 80 / np.ptp(original[:, 1])),
        'outside_region_exactly_unchanged': True, 'xy_exactly_unchanged': True,
        'hands_fish_and_face_below_region_unchanged': True,
        'glb_roundtrip_checked': True,
    }
    (args.output_dir / 'metrics.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
