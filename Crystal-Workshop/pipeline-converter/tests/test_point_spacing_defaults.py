"""Purpose: Preserve the owner's distinct 0.08 mm point and 0.09 mm layer defaults."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'code'))
from convert_model import build_parser as model_parser
from mesh_to_pointcloud import build_parser as cloud_parser


class PointSpacingDefaults(unittest.TestCase):
    def test_model_and_point_cloud_defaults_agree(self):
        model = model_parser().parse_args(['--file', 'fixture.glb', '--formats', 'dxf'])
        cloud = cloud_parser().parse_args(['--file', 'fixture.obj'])
        for arguments in [model, cloud]:
            self.assertEqual(arguments.spacing, 0.08)
            self.assertEqual(arguments.min_distance, 0.08)
            self.assertEqual(arguments.layer_spacing, 0.09)
            self.assertEqual(arguments.points, 0)


if __name__ == '__main__':
    unittest.main()
