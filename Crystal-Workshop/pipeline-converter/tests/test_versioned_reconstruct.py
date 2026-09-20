"""Purpose: Verify real Reconstruct output pairs a versioned GLB with exact source photo bytes."""
import io
import json
from pathlib import Path
import struct
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from zipfile import ZipFile
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'code'))
import cockpit_reconstruct


class VersionedReconstructTests(unittest.TestCase):
    def test_real_named_output_and_embedded_photo_reference(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            dxf = root / 'source.dxf'
            dxf.write_text('0\nSECTION\n2\nENTITIES\n' + ''.join(
                f'0\nPOINT\n10\n{x}\n20\n{y}\n30\n{(x*y)/100}\n'
                for x in range(20) for y in range(20)) + '0\nENDSEC\n0\nEOF\n')
            photo = io.BytesIO()
            Image.new('RGB', (32, 32), 'white').save(photo, format='JPEG')
            scene = root / 'source.cockpit'
            with ZipFile(scene, 'w') as archive:
                archive.writestr('CockpitScene.xml', '<Scene><SolidEntity Texture="actual.jpg"/></Scene>')
                archive.writestr('actual.jpg', photo.getvalue())
            stem = '55777-volcanic-activity-v001'
            argv = ['reconstruct', '--file', str(dxf), '--texture-from', str(scene),
                    '--output-stem', stem, '--grid-resolution', '64']
            with patch.object(cockpit_reconstruct, 'ROOT', root), patch.object(sys, 'argv', argv):
                cockpit_reconstruct.main()
            output = root / 'output' / 'cockpit-reconstruct'
            report = json.loads((output / (stem + '.json')).read_text())
            self.assertTrue(report['files']['glb'].endswith(stem + '.glb'))
            self.assertTrue(report['files']['original'].endswith(stem + '.jpg'))
            self.assertEqual((output / (stem + '.jpg')).read_bytes(), photo.getvalue())
            data = (output / (stem + '.glb')).read_bytes()
            size = struct.unpack_from('<I', data, 12)[0]
            metadata = json.loads(data[20:20+size])['asset']['extras']['acmReconstruction']
            self.assertEqual(metadata['originalPhoto']['name'], stem + '.jpg')
