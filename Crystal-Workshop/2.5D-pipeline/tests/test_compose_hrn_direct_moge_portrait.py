"""
File: tests/test_compose_hrn_direct_moge_portrait.py
Purpose:
 - Verify portrait composition coordinate and mask helpers.
"""

import sys
from pathlib import Path

import numpy as np
import trimesh

RESEARCH = Path(__file__).resolve().parents[1] / "code" / "research"
sys.path.insert(0, str(RESEARCH))

from compose_hrn_direct_moge_portrait import (  # noqa: E402
    build_shoulder_depth_weight,
    build_frame_cut_backfill,
    build_grid_faces,
    largest_boundary_component,
    rasterize_patch_footprint,
    scene_xy_to_source_pixels,
)


def test_scene_xy_to_source_pixels_restores_source_frame() -> None:
    scene = np.array([[0.0, 0.0], [-0.5, 1.0], [0.5, -1.0]])
    pixels = scene_xy_to_source_pixels(scene, (100, 101))
    np.testing.assert_allclose(pixels[0], [49.5, 50.0])
    np.testing.assert_allclose(pixels[1], [24.5, 0.0])
    np.testing.assert_allclose(pixels[2], [74.5, 100.0])


def test_rasterize_patch_footprint_fills_triangle() -> None:
    points = np.array([[1.0, 1.0], [6.0, 1.0], [1.0, 6.0]])
    mask = rasterize_patch_footprint((8, 8), points, np.array([[0, 1, 2]]))
    assert mask[2, 2]
    assert not mask[7, 7]


def test_build_grid_faces_keeps_only_fully_masked_cells() -> None:
    mask = np.ones((3, 3), dtype=bool)
    mask[0, 0] = False
    faces = build_grid_faces(mask)
    assert len(faces) == 6


def test_largest_boundary_component_discards_small_hole() -> None:
    edges = np.array(
        [[0, 1], [1, 2], [2, 3], [3, 0], [8, 9], [9, 10], [10, 8]]
    )
    selected = largest_boundary_component(edges)
    assert len(selected) == 4
    assert set(selected.ravel()) == {0, 1, 2, 3}


def test_shoulder_depth_weight_is_bounded_and_leaves_lower_torso_unchanged() -> None:
    weight = build_shoulder_depth_weight(
        (12, 4),
        face_y=1.0,
        face_height=4.0,
        start_factor=0.5,
        peak_factor=1.0,
        end_factor=2.0,
    )
    assert np.all(weight >= 0.0)
    assert np.all(weight <= 1.0)
    assert np.allclose(weight[5], 1.0)
    assert np.allclose(weight[10:], 0.0)


def test_shoulder_depth_weight_rejects_invalid_factor_order() -> None:
    try:
        build_shoulder_depth_weight((4, 4), 0.0, 1.0, 1.0, 0.5, 2.0)
    except ValueError as error:
        assert "start < peak < end" in str(error)
    else:
        raise AssertionError("Invalid shoulder factors must fail")


def test_frame_cut_backfill_selects_only_edges_touching_source_frame() -> None:
    mesh = trimesh.Trimesh(
        vertices=np.array(
            [
                [-1.0, -1.0, 0.2],
                [1.0, -1.0, 0.2],
                [1.0, 1.0, 0.2],
                [-1.0, 1.0, 0.2],
            ]
        ),
        faces=np.array([[0, 1, 2], [0, 2, 3]]),
        vertex_colors=np.full((4, 4), 255, dtype=np.uint8),
        process=False,
    )
    backfill, stats = build_frame_cut_backfill(
        mesh,
        source_size=(11, 11),
        border_px=0.5,
        back_depth=0.3,
        inset_px=1.0,
        ring_count=4,
    )
    assert backfill is not None
    assert stats["selected_edges"] == 4
    assert stats["triangles"] == 24
    assert np.isclose(backfill.vertices[:, 2].max(), 0.2)
    assert backfill.vertices[:, 2].min() < 0.0
