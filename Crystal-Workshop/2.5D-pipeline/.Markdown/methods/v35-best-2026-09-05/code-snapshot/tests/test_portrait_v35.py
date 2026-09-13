"""
File: tests/test_portrait_v35.py
Purpose:
 - Check perspective normal signs, disconnected integration and export invariants.
"""

import sys
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'code' / 'research'))
from build_portrait_v35 import normal_near_gradients, screened_integration, export_surface


def test_perspective_plane_gradients_have_near_positive_sign():
    rows, cols = 30, 40
    yy, xx = np.mgrid[:rows, :cols]
    k = np.array([[1., 0, .5], [0, 1., .5], [0, 0, 1.]])
    # Plane with n=(.2,.1,-1): its metric depth grows towards image right/down.
    rx, ry = (xx + .5) / cols - .5, (yy + .5) / rows - .5
    depth = 2 / (1 - .2 * rx - .1 * ry)
    normal = np.broadcast_to(np.array([.2, .1, -1.]), (*depth.shape, 3))
    gx, gy, valid = normal_near_gradients(depth, normal, k)
    assert valid.all()
    assert np.all(gx < 0) and np.all(gy < 0)
    np.testing.assert_allclose(gx[:, 1:-1], np.gradient(-depth, axis=1)[:, 1:-1], rtol=1e-4)
    np.testing.assert_allclose(gy[1:-1], np.gradient(-depth, axis=0)[1:-1], rtol=1e-4)
    flipped = normal_near_gradients(depth, -normal, k)
    np.testing.assert_allclose(gx, flipped[0])


def test_integration_does_not_bridge_disconnected_regions():
    mask = np.ones((20, 40), dtype=bool)
    mask[:, 18:22] = False
    gx = np.zeros(mask.shape)
    gx[:, :18] = .1
    out = screened_integration(gx, np.zeros_like(gx), mask)
    assert np.max(abs(out[:, 22:])) < 1e-10
    assert np.ptp(out[:, :18]) > .1
    assert not out[:, 18:22].any()


def test_flat_normals_produce_no_displacement():
    zeros = np.zeros((15, 15))
    out = screened_integration(zeros, zeros, np.ones_like(zeros, dtype=bool))
    assert not out.any()


def test_glb_and_obj_roundtrip_share_geometry_in_different_units(tmp_path):
    z = np.arange(120).reshape(12, 10) * .01
    mask = np.ones_like(z, dtype=bool)
    mask[4:7, 4:6] = False
    out = tmp_path / 'mesh'
    stats = export_surface(z, mask, Image.new('RGBA', (10, 12), (180, 160, 140, 255)), out, 80.)
    obj = trimesh.load(out / 'relief-mm.obj', force='mesh', process=False)
    glb = trimesh.load(out / 'relief.glb', force='mesh', process=False)
    np.testing.assert_allclose(obj.vertices, glb.vertices * 1000, atol=5e-6)
    np.testing.assert_array_equal(obj.faces, glb.faces)
    assert stats['zero_area_triangles'] == 0
    assert stats['nonmanifold_edges'] == 0
    assert stats['boundary_edges'] > 0
