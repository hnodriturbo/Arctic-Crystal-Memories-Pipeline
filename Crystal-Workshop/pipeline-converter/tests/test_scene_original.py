"""Purpose: Verify exact named texture extraction, repeat safety and ambiguity rejection."""
import sys
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'code'))
from extract_scene_original import extract_original


class OriginalTests(unittest.TestCase):
    def test_named_member_not_first_photo(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            scene = root / 'test.cockpit'
            with ZipFile(scene, 'w') as archive:
                archive.writestr('wrong.jpg', b'wrong')
                archive.writestr('chosen.jpg', b'exact original bytes')
                archive.writestr('CockpitScene.xml', '<Scene><SolidEntity Texture="chosen.jpg"/></Scene>')
            result = extract_original(scene, root)
            self.assertEqual((root / result['name']).read_bytes(), b'exact original bytes')
            self.assertEqual(extract_original(scene, root), result)
            versioned = extract_original(scene, root, '55777-volcanic-activity-v001')
            self.assertEqual(versioned['name'], '55777-volcanic-activity-v001.jpg')
            self.assertEqual(versioned['sha256'], result['sha256'])
            self.assertEqual((root / versioned['name']).read_bytes(), b'exact original bytes')
            (root / result['name']).write_bytes(b'changed')
            with self.assertRaises(ValueError):
                extract_original(scene, root)

    def test_ambiguous_scene_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            scene = Path(folder) / 'test.cockpit'
            with ZipFile(scene, 'w') as archive:
                archive.writestr('CockpitScene.xml', '<Scene><SolidEntity Texture="a.jpg"/><SolidEntity Texture="b.jpg"/></Scene>')
            with self.assertRaises(ValueError):
                extract_original(scene, folder)
