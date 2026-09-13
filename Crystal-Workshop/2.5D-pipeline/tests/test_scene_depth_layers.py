"""
File: tests/test_scene_depth_layers.py
Purpose:
 - Verify deterministic scene sampling and topology for MoGe rest-of-image layers.
"""

import importlib.util
from pathlib import Path
import sys

import numpy as np


RESEARCH_DIR = Path(__file__).parents[1] / "code" / "research"
sys.path.insert(0, str(RESEARCH_DIR))
SPEC = importlib.util.spec_from_file_location(
    "fuse_scene_depth_layers", RESEARCH_DIR / "fuse_scene_depth_layers.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_sample_axis_always_contains_last_pixel():
    np.testing.assert_array_equal(MODULE.sample_axis(8, 3), [0, 3, 6, 7])
    np.testing.assert_array_equal(MODULE.sample_axis(7, 3), [0, 3, 6])


def test_grid_faces_do_not_bridge_a_mask_gap():
    valid = np.ones((4, 4), dtype=bool)
    valid[1:3, 1:3] = False
    faces = MODULE.build_faces(valid)
    assert len(faces) == 0


def test_full_three_by_three_grid_has_eight_triangles():
    faces = MODULE.build_faces(np.ones((3, 3), dtype=bool))
    assert faces.shape == (8, 3)
