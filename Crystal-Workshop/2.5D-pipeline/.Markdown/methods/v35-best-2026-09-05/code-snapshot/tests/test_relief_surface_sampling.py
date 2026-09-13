"""
Purpose: Verify dense stretch sampling preserves the original surface and fills long edges.
"""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'code/research'))
from sample_relief_surface import sample_surface, quantize_point_lattice


def test_stretched_triangle_stays_on_surface_and_preserves_uv():
    vertices = np.array([[0., 0., 0.], [.01, 0., .02], [0., .0001, 0.]])
    uv = np.array([[0., 0.], [1., 0.], [0., 1.]])
    points, texcoords, report = sample_surface(vertices, np.array([[0, 1, 2]]), uv, .0002)
    assert np.array_equal(points[:3], vertices)
    assert np.allclose(points[:, 2], 2*points[:, 0])
    assert np.allclose(points, texcoords[:, :1]*vertices[1]+texcoords[:, 1:]*vertices[2])
    assert (texcoords >= 0).all() and (texcoords.sum(axis=1) <= 1+1e-12).all()
    edge = points[np.abs(points[:, 1]) < 1e-12]
    edge = edge[np.argsort(edge[:, 0])]
    assert np.max(np.linalg.norm(np.diff(edge, axis=0), axis=1)) <= .0002+1e-12
    assert report['added_points'] > 100


def test_already_dense_triangle_is_unchanged():
    v = np.array([[0.,0.,0.],[.0001,0.,0.],[0.,.0001,0.]])
    p, uv, report = sample_surface(v, np.array([[0,1,2]]), v[:, :2], .0002)
    assert np.array_equal(p, v)
    assert report['added_points'] == 0


def test_invalid_spacing_and_point_budget_fail():
    v = np.array([[0.,0.,0.],[1.,0.,0.],[0.,1.,0.]])
    with pytest.raises(ValueError):
        sample_surface(v, np.array([[0,1,2]]), v[:, :2], 0)
    with pytest.raises(ValueError):
        sample_surface(v, np.array([[0,1,2]]), v[:, :2], .1, max_points=5)


def test_fixed_point_lattice_has_unique_cells_and_exact_pitch():
    points = np.array([[0.,0.,0.],[.00001,0.,0.],[.00008,.00008,.00009],[.00015,0.,.00017]])
    result, retained, stats = quantize_point_lattice(points, .00008, .00009)
    assert len(result) == 3
    assert retained.tolist() == [0,2,3]
    assert np.allclose(result/np.array([.00008,.00008,.00009]),np.rint(result/np.array([.00008,.00008,.00009])))
    assert (np.abs(result-points[retained]) <= np.array([.00004,.00004,.000045])).all()
