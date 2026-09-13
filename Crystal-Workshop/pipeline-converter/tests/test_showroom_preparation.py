"""
File: tests/test_showroom_preparation.py
Purpose: Verify bounded contour changes and exact full-point preparation invariants.
"""
import json
from pathlib import Path
import sys
import unittest
import numpy as np
import trimesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'code'))
from prepare_showroom import smooth_boundary
from utils.parsers import parse_dxf_points_fast


class PreparationTests(unittest.TestCase):
    def test_boundary_does_not_change_depth_or_interior(self):
        """Only edge XY may move and its maximum movement is bounded."""
        vertices = np.array([[0., 0., 1.], [1., 0., 2.], [1., 1., 3.], [0., 1., 4.], [.5, .5, 5.]], dtype=np.float32)
        faces = np.array([[0, 1, 4], [1, 2, 4], [2, 3, 4], [3, 0, 4]])
        result = smooth_boundary(vertices, faces, maximum_mm=.1)
        np.testing.assert_array_equal(result[:, 2], vertices[:, 2])
        np.testing.assert_array_equal(result[4], vertices[4])
        self.assertLessEqual(float(np.linalg.norm(result - vertices, axis=1).max()), .100001)

    def test_prepared_group_photo_preserves_every_point(self):
        """The real prepared PLY must match all source positions in original order."""
        root = Path(__file__).resolve().parents[1]
        directory = root / 'output/showroom/group-photo-smooth-v1'
        if not directory.exists():
            self.skipTest('Local reference assets unavailable')
        report = json.loads((directory / 'provenance.json').read_text())
        if not Path(report['dxf']).exists():
            self.skipTest('Reference source has moved; historical provenance is preserved')
        source = np.asarray(parse_dxf_points_fast(report['dxf'], sample_rate=1)) - report['removedOriginMm']
        data = (directory / 'points-rgb.ply').read_bytes().split(b'end_header\n', 1)[1]
        points = np.frombuffer(data, dtype=[('xyz', '<f4', (3,)), ('rgb', 'u1', (3,))])
        self.assertEqual(len(points), len(source))
        np.testing.assert_array_equal(points['xyz'], source.astype(np.float32))
        surface = trimesh.load(directory / 'surface-smooth.glb', force='mesh')
        self.assertTrue(np.isfinite(surface.vertices).all())
        self.assertGreater(len(surface.faces), 300000)


if __name__ == '__main__':
    unittest.main()
