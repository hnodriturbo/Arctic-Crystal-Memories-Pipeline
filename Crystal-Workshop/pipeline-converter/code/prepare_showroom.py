"""
File: code/prepare_showroom.py
Purpose: Prepare paired, traceable display GLB and full RGB point PLY from an aligned Cockpit export.
The DXF stays unchanged; the surface is an estimate and is never laser production data.
"""
import argparse
import hashlib
import json
import struct
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET

import numpy as np
import trimesh
from utils.parsers import parse_dxf_points_fast
from utils.photo_projection import photo_uv, vertex_colors
from utils.relief_surface import reconstruct_relief
from utils.scene_transform import read_scene_transform

PRESET = json.loads(Path(__file__).with_name('showroom-preset.json').read_text(encoding='utf-8'))


def smooth_boundary(vertices, faces, iterations=8, maximum_mm=0.2):
    """Relax only two-neighbour boundary XY positions, with a bounded displacement."""
    edges = np.sort(np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]]), axis=1)
    edges, counts = np.unique(edges, axis=0, return_counts=True)
    neighbours = {}
    for a, b in edges[counts == 1]:
        neighbours.setdefault(a, []).append(b)
        neighbours.setdefault(b, []).append(a)
    ids = np.array([i for i, adjacent in neighbours.items() if len(adjacent) == 2], dtype=int)
    if not len(ids):
        return vertices.copy()
    adjacent = np.array([neighbours[i] for i in ids])
    result = vertices.copy()
    for _ in range(iterations):
        result[ids, :2] += 0.35 * (result[adjacent, :2].mean(axis=1) - result[ids, :2])
        delta = result[ids, :2] - vertices[ids, :2]
        lengths = np.linalg.norm(delta, axis=1)
        result[ids, :2] = vertices[ids, :2] + delta * np.minimum(1, maximum_mm / np.maximum(lengths, 1e-12))[:, None]
    return result


def unlit_glb(model):
    """Avoid a second layer of lighting over the photograph's baked illumination."""
    data = model.export(file_type='glb', include_normals=True)
    length = struct.unpack_from('<I', data, 12)[0]
    document = json.loads(data[20:20 + length])
    document.setdefault('extensionsUsed', []).append('KHR_materials_unlit')
    for material in document.get('materials', []):
        material.setdefault('extensions', {})['KHR_materials_unlit'] = {}
    encoded = json.dumps(document, separators=(',', ':')).encode()
    encoded += b' ' * (-len(encoded) % 4)
    tail = data[20 + length:]
    return struct.pack('<III', 0x46546c67, 2, 20 + len(encoded) + len(tail)) + struct.pack('<II', len(encoded), 0x4e4f534a) + encoded + tail


def main():
    """Fail on transformed/ambiguous scenes, then export paired display assets and provenance."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dxf', type=Path, required=True)
    parser.add_argument('--cockpit', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    with ZipFile(args.cockpit) as archive:
        scene = ET.fromstring(archive.read('CockpitScene.xml'))
        entities = [e for e in scene.iter() if e.tag.split('}')[-1] == 'SolidEntity' and e.get('Texture')]
        if len(entities) != 1:
            raise ValueError('Use a freshly saved scene with one textured SolidEntity.')
        texture_name = entities[0].get('Texture')
        texture_hash = hashlib.sha256(archive.read(texture_name)).hexdigest()
    points = np.asarray(parse_dxf_points_fast(args.dxf, sample_rate=1), dtype=np.float64)
    if len(points) < 3:
        raise ValueError('No usable DXF points.')
    origin = (points.min(axis=0) + points.max(axis=0)) / 2
    rotation, position, transform = read_scene_transform(args.cockpit)
    aligned = rotation.inv().apply(points - position)
    points -= origin
    print(f'Reconstructing all {len(points):,} points.', flush=True)
    vertices, faces = reconstruct_relief(aligned, resolution=PRESET['resolution'], smoothing=PRESET['smoothing'],
                                        gap=PRESET['gap'], percentile=PRESET['percentile'], max_vertices=PRESET['maxVertices'])
    original = vertices.copy()
    vertices = smooth_boundary(vertices, faces, PRESET['boundaryIterations'], PRESET['boundaryMaximumMm'])
    # UVs retain the original projection bounds: smoothing must not reframe the photograph.
    photo, _ = photo_uv(original, args.cockpit, 'xy')
    uv = (vertices[:, :2] - original[:, :2].min(axis=0)) / np.ptp(original[:, :2], axis=0)
    world_vertices = rotation.apply(vertices) + position - origin
    mesh = trimesh.Trimesh(vertices=world_vertices * 0.001, faces=faces, process=False)
    mesh.visual = trimesh.visual.TextureVisuals(uv=uv, material=trimesh.visual.material.PBRMaterial(
        baseColorTexture=photo, metallicFactor=0, roughnessFactor=1, doubleSided=True))
    args.output.mkdir(parents=True, exist_ok=True)
    glb = args.output / 'surface-smooth.glb'
    ply = args.output / 'points-rgb.ply'
    if glb.exists() or ply.exists():
        raise ValueError('Choose a new output folder; existing trials are never replaced.')
    glb.write_bytes(unlit_glb(mesh))
    colors = vertex_colors(aligned, args.cockpit, 'xy')[:, :3]
    packed = np.empty(len(points), dtype=[('xyz', '<f4', (3,)), ('rgb', 'u1', (3,))])
    packed['xyz'], packed['rgb'] = points, colors
    header = ('ply\nformat binary_little_endian 1.0\ncomment units millimetres; centered; display RGB from paired scene\n'
              f'element vertex {len(points)}\nproperty float x\nproperty float y\nproperty float z\n'
              'property uchar red\nproperty uchar green\nproperty uchar blue\nend_header\n')
    ply.write_bytes(header.encode('ascii') + packed.tobytes())
    report = {'created': datetime.now(timezone.utc).isoformat(), 'dxf': str(args.dxf.resolve()),
              'cockpit': str(args.cockpit.resolve()), 'texture': texture_name, 'textureSha256': texture_hash,
              'sourcePointCount': len(points), 'displayPointCount': len(points), 'removedOriginMm': origin.tolist(),
              'pointUnits': 'mm', 'glbUnits': 'm', 'vertices': len(vertices), 'triangles': len(faces),
              'sceneTransform': transform, 'preset': PRESET, 'grid': PRESET['resolution'], 'smoothingCells': PRESET['smoothing'],
              'gapCells': PRESET['gap'], 'percentile': PRESET['percentile'],
              'maxBoundaryMovementMm': float(np.linalg.norm(vertices - original, axis=1).max()),
              'material': 'KHR_materials_unlit', 'status': 'candidate-needs-visual-review',
              'hashes': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in [args.dxf, args.cockpit, glb, ply]}}
    (args.output / 'provenance.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
