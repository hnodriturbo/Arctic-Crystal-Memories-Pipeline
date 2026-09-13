"""
File: tests/test_hrn_direct_front_patch.py
Purpose:
 - Verify coordinate projection helpers used by direct native HRN geometry.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code/research/extract_hrn_direct_front_patch.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("extract_hrn_direct_front_patch", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_obj_to_blender_world_matches_import_axes() -> None:
    vertices = np.array([[1.0, 2.0, 3.0], [-4.0, 5.0, -6.0]])
    transformed = MODULE.obj_to_blender_world(vertices)
    np.testing.assert_allclose(transformed, [[1.0, -3.0, 2.0], [-4.0, 6.0, 5.0]])


def test_orthographic_projection_keeps_center_and_scale() -> None:
    points = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 1.0], [-1.0, 0.0, -1.0]])
    projected = MODULE.project_hrn_pixels(points, resolution=101, ortho_scale=4.0)
    np.testing.assert_allclose(projected, [[50.0, 50.0], [75.0, 25.0], [25.0, 75.0]])


def test_affine_application_preserves_point_order() -> None:
    points = np.array([[0.0, 0.0], [2.0, 3.0]])
    affine = np.array([[2.0, 0.0, 5.0], [0.0, 3.0, -1.0]])
    np.testing.assert_allclose(MODULE.apply_affine(points, affine), [[5.0, -1.0], [9.0, 8.0]])
