"""
File: tests/test_enhance_portrait_v34.py
Purpose:
 - Verify the bounded v3.4 depth envelope and eyeglass ribbon geometry helpers.
"""

import sys
from pathlib import Path

import numpy as np
import trimesh

RESEARCH = Path(__file__).resolve().parents[1] / "code" / "research"
sys.path.insert(0, str(RESEARCH))

from enhance_portrait_v34 import (  # noqa: E402
    FramePath,
    apply_depth_envelope,
    build_ribbon_mesh,
    superellipse_points,
)


def test_depth_envelope_preserves_front_and_compresses_back() -> None:
    mesh = trimesh.Trimesh(
        vertices=np.array([[0.0, 0.0, -1.0], [1.0, 0.0, 0.5], [0.0, 1.0, 1.0]]),
        faces=np.array([[0, 1, 2]]),
        process=False,
    )
    stats = apply_depth_envelope([mesh], target_depth=1.0)
    assert np.isclose(mesh.vertices[:, 2].max(), 1.0)
    assert np.isclose(mesh.vertices[:, 2].min(), 0.0)
    assert np.isclose(stats["applied_scale"], 0.5)


def test_depth_envelope_never_expands_existing_depth() -> None:
    mesh = trimesh.Trimesh(
        vertices=np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.5], [0.0, 1.0, 1.0]]),
        faces=np.array([[0, 1, 2]]),
        process=False,
    )
    stats = apply_depth_envelope([mesh], target_depth=2.0)
    assert np.isclose(stats["applied_scale"], 1.0)
    assert np.isclose(mesh.vertices[:, 2].min(), 0.0)


def test_superellipse_is_closed_by_topology_and_bounded() -> None:
    points = superellipse_points(np.array([10.0, 20.0]), 4.0, 2.0, 4.0, 0.0, count=64)
    assert points.shape == (64, 2)
    assert np.isclose(points[:, 0].min(), 6.0)
    assert np.isclose(points[:, 0].max(), 14.0)
    assert np.isclose(points[:, 1].min(), 18.0)
    assert np.isclose(points[:, 1].max(), 22.0)


def test_ribbon_has_open_lens_and_requested_backfill_rings() -> None:
    depth = np.full((80, 100), 0.25, dtype=np.float32)
    source = np.full((80, 100, 3), 180, dtype=np.uint8)
    contour = superellipse_points(
        np.array([50.0, 40.0]), 18.0, 10.0, 3.0, 0.0, count=48
    )
    mesh, stats = build_ribbon_mesh(
        [FramePath("lens", contour, True)],
        depth,
        source,
        width_px=3.0,
        rise=0.02,
        rings=6,
    )
    assert stats["rings"] == 6
    assert stats["segments"] == 48
    assert len(mesh.faces) > 0
    assert np.isclose(mesh.vertices[:, 2].min(), 0.25)
    assert np.isclose(mesh.vertices[:, 2].max(), 0.27)
    centre_scene_x = 0.0
    centre_scene_y = 0.0
    assert not np.any(
        np.linalg.norm(mesh.vertices[:, :2] - [centre_scene_x, centre_scene_y], axis=1) < 0.02
    )


def test_ribbon_rejects_backfill_outside_three_to_eight_rings() -> None:
    path = FramePath(
        "line", np.array([[10.0, 10.0], [20.0, 10.0], [30.0, 10.0]]), False
    )
    try:
        build_ribbon_mesh(
            [path],
            np.zeros((40, 40), dtype=np.float32),
            np.zeros((40, 40, 3), dtype=np.uint8),
            width_px=2.0,
            rise=0.01,
            rings=2,
        )
    except ValueError as error:
        assert "between 3 and 8" in str(error)
    else:
        raise AssertionError("Two-ring eyeglass backfill must fail")
