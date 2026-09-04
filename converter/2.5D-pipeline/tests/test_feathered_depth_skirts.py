"""
File: tests/test_feathered_depth_skirts.py
Purpose:
 - Verify feather interpolation, boundary smoothing, and outward skirt construction.
"""

import sys
from pathlib import Path

import numpy as np
import trimesh

RESEARCH_DIR = Path(__file__).resolve().parents[1] / "code" / "research"
sys.path.insert(0, str(RESEARCH_DIR))

from add_feathered_depth_skirts import (  # noqa: E402
    boundary_geometry,
    smooth_boundary_values,
    smooth_boundary_vectors,
    smoothstep,
)


def test_smoothstep_keeps_endpoints_and_has_soft_middle() -> None:
    values = smoothstep(np.array([0.0, 0.25, 0.5, 0.75, 1.0]))
    np.testing.assert_allclose(values[[0, -1]], [0.0, 1.0])
    np.testing.assert_allclose(values[2], 0.5)
    assert values[1] < 0.25
    assert values[3] > 0.75


def test_boundary_normals_point_away_from_square_center() -> None:
    mesh = trimesh.Trimesh(
        vertices=np.array(
            [[-1.0, -1.0, 0.0], [1.0, -1.0, 0.0], [1.0, 1.0, 0.0], [-1.0, 1.0, 0.0]]
        ),
        faces=np.array([[0, 1, 2], [0, 2, 3]]),
        process=False,
    )
    boundary_ids, edge_local, outward, _ = boundary_geometry(mesh)
    assert len(boundary_ids) == 4
    assert len(edge_local) == 4
    positions = mesh.vertices[boundary_ids, :2]
    assert np.all(np.einsum("ij,ij->i", positions, outward) > 0.0)


def test_boundary_smoothing_reduces_isolated_depth_spike() -> None:
    edges = np.array([[0, 1], [1, 2], [2, 3], [3, 0]])
    source = np.array([0.0, 0.0, 10.0, 0.0])
    smoothed = smooth_boundary_values(source, edges, iterations=4, weight=0.5)
    assert smoothed.max() < source.max()
    assert smoothed[1] > 0.0
    assert smoothed[3] > 0.0


def test_smoothed_boundary_vectors_remain_normalized() -> None:
    edges = np.array([[0, 1], [1, 2], [2, 3], [3, 0]])
    vectors = np.array([[1.0, 0.0], [0.8, 0.2], [1.0, 0.0], [0.8, -0.2]])
    smoothed = smooth_boundary_vectors(vectors, edges, iterations=5, weight=0.4)
    np.testing.assert_allclose(np.linalg.norm(smoothed, axis=1), 1.0)
