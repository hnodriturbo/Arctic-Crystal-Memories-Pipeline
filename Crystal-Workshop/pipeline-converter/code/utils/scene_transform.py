"""
Purpose: Read the paired scene transform and undo its rotation before XY reconstruction.
DXF already contains object scale; applying ScaleXYZ again would double-scale it.
"""
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET
import numpy as np
from scipy.spatial.transform import Rotation


def override_scene_transform(original, eulers, position):
    """Replace the export pose, never multiply it onto an already posed DXF."""
    if not np.isfinite([eulers, position]).all():
        raise ValueError('Scene pose must contain finite degrees and millimetres.')
    metadata = dict(original or {})
    metadata.update(originalPose=original, Eulers=list(eulers), Position=list(position), overridden=True)
    return Rotation.from_euler('xyz', eulers, degrees=True), np.asarray(position), metadata


def read_scene_transform(source):
    """Select the exact textured entity and return finite XYZ pose metadata."""
    if Path(source).suffix.lower() != '.cockpit':
        return Rotation.identity(), np.zeros(3), None
    with ZipFile(source) as archive:
        root = ET.fromstring(archive.read('CockpitScene.xml'))
    entities = [e for e in root.iter() if e.tag.split('}')[-1] == 'SolidEntity' and e.get('Texture')]
    if len(entities) != 1:
        raise ValueError('Choose a scene with exactly one textured SolidEntity.')
    entity = entities[0]
    values = {key: [float(entity.get(key + a, default)) for a in 'XYZ']
              for key, default in [('Eulers', '0'), ('Position', '0'), ('Scale', '1')]}
    if not np.isfinite(list(values.values())).all() or min(values['Scale']) <= 0:
        raise ValueError('Invalid scene transform.')
    values['texture'] = entity.get('Texture')
    values['rotationConvention'] = 'extrinsic xyz; validate against scene preview'
    return Rotation.from_euler('xyz', values['Eulers'], degrees=True), np.array(values['Position']), values
