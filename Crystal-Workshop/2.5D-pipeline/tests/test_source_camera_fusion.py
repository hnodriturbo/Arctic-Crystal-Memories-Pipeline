"""
File: tests/test_source_camera_fusion.py
Purpose:
 - Verify ICON pixel conversion, source aspect preservation, and depth scaling.
"""

import importlib.util
from pathlib import Path

import numpy as np


MODULE_PATH = Path(__file__).parents[1] / "code" / "research" / "source_camera_fusion.py"
SPEC = importlib.util.spec_from_file_location("source_camera_fusion", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_icon_xy_matches_grid_sample_align_corners():
    points = np.array([[-1.0, 1.0], [0.0, 0.0], [1.0, -1.0]])
    pixels = MODULE.icon_xy_to_raw_pixels(points, (512, 512))
    np.testing.assert_allclose(pixels, [[0.0, 0.0], [255.5, 255.5], [511.0, 511.0]])


def test_source_scene_coordinates_keep_pixels_square():
    points = np.array([[0.0, 0.0], [1085.0, 1176.0], [542.5, 588.0]])
    scene = MODULE.source_pixels_to_scene(points, (1086, 1177))
    np.testing.assert_allclose(scene[2], [0.0, 0.0])
    np.testing.assert_allclose(scene[0], [-542.5 / 588.0, 1.0])
    np.testing.assert_allclose(scene[1], [542.5 / 588.0, -1.0])


def test_transform_scales_depth_with_registered_xy():
    vertices = np.array([[-1.0, 1.0, 2.0], [1.0, -1.0, 4.0]])
    affine = np.array([[2.0, 0.0, 10.0], [0.0, 2.0, 20.0]])
    transformed, stats = MODULE.transform_vertices(
        vertices,
        affine,
        raw_size=(512, 512),
        source_size=(1086, 1177),
        depth_anchor_percentile=0.0,
    )
    expected_scale = 2.0 * 511.0 / 1176.0
    np.testing.assert_allclose(transformed[:, 2], [0.0, 2.0 * expected_scale])
    assert stats["isotropic_scene_scale"] == expected_scale


def test_source_color_sampling_uses_original_image_pixels():
    image = np.zeros((4, 4, 3), dtype=np.uint8)
    image[2, 1] = [10, 20, 30]
    colors = MODULE.sample_source_colors(image, np.array([[1.0, 2.0]]))
    np.testing.assert_array_equal(colors, [[10, 20, 30, 255]])
