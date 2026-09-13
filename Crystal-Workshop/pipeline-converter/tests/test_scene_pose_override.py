"""Purpose: Verify absolute Cockpit pose replacement and projection round-trip in millimetres."""
import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'code'))
from utils.scene_transform import override_scene_transform


class ScenePoseTests(unittest.TestCase):
    def test_combined_axes_replace_saved_pose_without_double_rotation(self):
        original = {'Eulers': [-15, 0, 0], 'Position': [0, 0, -2.486], 'Scale': [6, 6, 6]}
        rotation, position, metadata = override_scene_transform(original, [12, -8, 23], [2, -3, 4])
        local = np.array([[1., 2., 3.], [-4., 5., 6.]])
        exported = rotation.apply(local) + position
        np.testing.assert_allclose(rotation.inv().apply(exported - position), local, atol=1e-12)
        np.testing.assert_allclose(rotation.as_euler('xyz', degrees=True), [12, -8, 23])
        self.assertEqual(metadata['originalPose'], original)
        self.assertEqual(metadata['Scale'], [6, 6, 6])

    def test_nonfinite_pose_is_rejected(self):
        with self.assertRaises(ValueError):
            override_scene_transform({}, [float('nan'), 0, 0], [0, 0, 0])


if __name__ == '__main__':
    unittest.main()
