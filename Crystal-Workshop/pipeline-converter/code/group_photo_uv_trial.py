"""
Purpose: Test inverse scene-transform texture projection without changing geometry.
Context: XYZ extrinsic Euler order and local bounds mapping are hypotheses, not decoded CI UVs.
"""
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile
import json
import xml.etree.ElementTree as ET
import numpy as np
import trimesh
from scipy.spatial.transform import Rotation
from utils.parsers import parse_dxf_points_fast
from utils.photo_projection import load_photo


def main():
    """Preserve the original mesh and photo while testing local-space UV coordinates."""
    root = Path(__file__).resolve().parents[1]
    base = root / 'output/cockpit-reconstruct'
    previous = json.loads((base / '20260913-122335-23f2e969.json').read_text())
    scene_path = (root / previous['options']['texture_from']).resolve()
    with ZipFile(scene_path) as archive:
        scene = ET.fromstring(archive.read('CockpitScene.xml'))
    entity, = [n for n in scene.iter() if n.tag.split('}')[-1] == 'SolidEntity' and n.get('Texture')]
    position = np.array([float(entity.get('Position' + a)) for a in 'XYZ'])
    scale = np.array([float(entity.get('Scale' + a)) for a in 'XYZ'])
    angles = [float(entity.get('Eulers' + a)) for a in 'XYZ']
    rotation = Rotation.from_euler('xyz', angles, degrees=True)
    points = np.asarray(parse_dxf_points_fast(root / previous['options']['file'], sample_rate=4))
    center = (points.min(axis=0) + points.max(axis=0)) / 2
    model = trimesh.load(root / 'output' / previous['files']['glb'], force='mesh', process=False)
    before_vertices, before_faces = model.vertices.copy(), model.faces.copy()
    local = rotation.inv().apply(model.vertices * 1000 + center - position) / scale
    xy = local[:, :2]
    model.visual.uv = (xy - xy.min(axis=0)) / np.ptp(xy, axis=0)
    name = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S') + '-group-photo-local-uv'
    target = base / (name + '.glb')
    model.export(target, file_type='glb', include_normals=True)
    reloaded = trimesh.load(target, force='mesh', process=False)
    photo, _ = load_photo(scene_path)
    assert np.array_equal(before_vertices, reloaded.vertices)
    assert np.array_equal(before_faces, reloaded.faces)
    assert np.array_equal(np.asarray(photo), np.asarray(reloaded.visual.material.baseColorTexture.convert('RGB')))
    previous.update(jobId=name, glbBytes=target.stat().st_size)
    previous['files'] = {'glb': 'cockpit-reconstruct/' + target.name,
                         'stl': previous['files']['stl'], 'report': 'cockpit-reconstruct/' + name + '.json'}
    previous['uvTrial'] = {'eulerDegrees': angles, 'scale': scale.tolist(),
        'position': position.tolist(), 'assumedOrder': 'extrinsic xyz',
        'mapping': 'inverse transform then local XY bounds',
        'geometryUnchanged': True, 'texturePixelsMatchScene': True,
        'limitation': 'Original CI UVs and unclipped local bounds are not available; visual review required.'}
    (base / (name + '.json')).write_text(json.dumps(previous, indent=2) + '\n')
    print(json.dumps({'glb': str(target), 'verification': previous['uvTrial']}, indent=2))


if __name__ == '__main__':
    main()
