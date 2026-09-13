"""
Purpose: Verify source evidence survives GLB metadata insertion without changing geometry bytes.
"""
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'code'))
from utils.reconstruction_provenance import build_provenance, embed_provenance


class ProvenanceTests(unittest.TestCase):
    def test_preserves_binary_and_records_only_observed_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source.dxf'
            source.write_text('0\nEOF\n')
            scene = root / 'source.cockpit'
            with ZipFile(scene, 'w') as archive:
                archive.writestr('CockpitScene.xml', '<Scene><PointCloudBuilderSettings PointXyDistance="0.08" PointZDistance="0.09"/></Scene>')
            report = {'jobId': 'test', 'sampledPoints': 12, 'sceneTransform': {'Eulers': [-15, 0, 0]},
                      'options': {'file': '/private/input', 'sample_rate': 1, 'limit': 0}}
            metadata = build_provenance(source, scene, report)
            self.assertNotIn('file', metadata['reconstruction'])
            self.assertEqual(len(metadata['source']['sha256']), 64)
            attrs = metadata['cockpitSettings']['rawAttributes'][0]['attributes']
            self.assertEqual(attrs['PointZDistance'], '0.09')
            self.assertNotIn('ZJitter', attrs)
            self.assertFalse(metadata['exactOriginalCloudRecoverableFromSurface'])
            doc = json.dumps({'asset': {'version': '2.0', 'extras': {'existing': True}}}).encode()
            doc += b' ' * (-len(doc) % 4)
            binary = struct.pack('<II', 4, 0x004E4942) + b'1234'
            path = root / 'test.glb'
            path.write_bytes(struct.pack('<4sII', b'glTF', 2, 20 + len(doc) + len(binary))
                             + struct.pack('<II', len(doc), 0x4E4F534A) + doc + binary)
            embed_provenance(path, metadata)
            result = path.read_bytes()
            size = struct.unpack_from('<I', result, 12)[0]
            self.assertEqual(result[20 + size:], binary)
            self.assertEqual(len(result), struct.unpack_from('<I', result, 8)[0])
            extras = json.loads(result[20:20 + size])['asset']['extras']
            self.assertTrue(extras['existing'])
            self.assertEqual(extras['acmReconstruction'], metadata)


if __name__ == '__main__':
    unittest.main()
