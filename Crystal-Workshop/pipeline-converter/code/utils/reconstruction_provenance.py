"""
Purpose: Preserve source identity and raw Cockpit settings in derived GLB files.
Metadata documents provenance; it is not a lossless copy of the source cloud.
"""
import hashlib
import json
from pathlib import Path
import struct
from zipfile import ZipFile
import xml.etree.ElementTree as ET


def source_identity(path):
    path = Path(path)
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return {'name': path.name, 'bytes': path.stat().st_size, 'sha256': digest.hexdigest()}


def read_cockpit_settings(path):
    if not path or Path(path).suffix.lower() != '.cockpit':
        return None
    with ZipFile(path) as archive:
        root = ET.fromstring(archive.read('CockpitScene.xml'))
    tags = {'Settings', 'PointCloudBuilderSettings', 'PortraitRasterizerSettings',
            'VectorRasterizerSettings', 'LightmapMaskParameters', 'Template',
            'RasterizerSettings', 'ProjectionSetting', 'ThreeSixtyRasterizerSettings'}
    return {'source': 'CockpitScene.xml', 'rawAttributes': [
        {'element': e.tag.split('}')[-1], 'attributes': dict(e.attrib)}
        for e in root.iter() if e.tag.split('}')[-1] in tags and e.attrib]}


def build_provenance(source, scene, report):
    # Exclude absolute server paths from downloadable/public model metadata.
    options = {k: v for k, v in report['options'].items()
               if k not in {'file', 'texture_from', 'inspect_scene', 'output_subdir'}}
    return {
        'schemaVersion': 1, 'jobId': report['jobId'],
        'source': source_identity(source),
        'scene': source_identity(scene) if scene else None,
        'cockpitSettings': read_cockpit_settings(scene),
        'appliedSceneTransform': report['sceneTransform'],
        'reconstruction': options, 'sampledPoints': report['sampledPoints'],
        'allSourcePointsRequested': options['sample_rate'] == 1 and options['limit'] == 0,
        'glbCoordinateUnit': 'metre',
        'sourceCoordinateUnit': {'value': 'millimetre', 'basis': 'Workshop Cockpit export convention'},
        'exactOriginalCloudRecoverableFromSurface': False,
    }


def embed_provenance(path, metadata):
    """Replace only the GLB JSON chunk; preserve all binary chunks verbatim."""
    path = Path(path)
    data = path.read_bytes()
    if len(data) < 20 or struct.unpack_from('<4sII', data) != (b'glTF', 2, len(data)):
        raise ValueError('Invalid GLB header.')
    size, kind = struct.unpack_from('<II', data, 12)
    if kind != 0x4E4F534A or 20 + size > len(data):
        raise ValueError('Invalid GLB JSON chunk.')
    document = json.loads(data[20:20 + size])
    extras = document.setdefault('asset', {}).setdefault('extras', {})
    if not isinstance(extras, dict):
        raise ValueError('GLB asset extras must be an object to preserve provenance.')
    extras['acmReconstruction'] = metadata
    encoded = json.dumps(document, separators=(',', ':'), allow_nan=False).encode('utf-8')
    encoded += b' ' * (-len(encoded) % 4)
    tail = data[20 + size:]
    path.write_bytes(struct.pack('<4sII', b'glTF', 2, 20 + len(encoded) + len(tail))
                     + struct.pack('<II', len(encoded), kind) + encoded + tail)
