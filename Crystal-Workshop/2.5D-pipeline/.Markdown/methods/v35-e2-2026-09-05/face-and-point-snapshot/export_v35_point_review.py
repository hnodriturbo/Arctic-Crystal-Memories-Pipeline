"""
Purpose:
 - Export the exact vertices of a textured relief as coloured and grayscale PLY points.
 - Package a local Three.js viewer without remote services or geometry deformation.
"""

import argparse
import base64
import hashlib
import json
import shutil
from pathlib import Path

import numpy as np
import trimesh
from scipy.ndimage import map_coordinates
from sample_relief_surface import sample_surface


def encoded(array, dtype):
    return base64.b64encode(np.ascontiguousarray(array, dtype=dtype).tobytes()).decode('ascii')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mesh', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--id', required=True)
    parser.add_argument('--label', required=True)
    parser.add_argument('--surface-spacing-mm', '--point-spacing-mm', type=float, default=.08)
    parser.add_argument('--layer-spacing-mm', type=float, default=.09)
    parser.add_argument('--vertex-only', action='store_true', help='Diagnostic legacy export without the default dense sampling profile.')
    parser.add_argument('--minimum-points', type=int, default=0)
    args = parser.parse_args()
    if args.vertex_only:
        args.surface_spacing_mm = args.layer_spacing_mm = None
    root = Path(__file__).resolve().parents[2]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    item_dir = args.output_dir / args.id
    item_dir.mkdir(exist_ok=False)
    original_bytes = args.mesh.read_bytes()
    mesh = trimesh.load(args.mesh, force='mesh', process=False)
    point_positions = mesh.vertices
    point_uv = mesh.visual.uv if mesh.visual.kind == 'texture' else None
    sampling = None
    if args.surface_spacing_mm is not None:
        if point_uv is None:
            raise ValueError('Dense surface review currently requires a UV-textured mesh')
        point_positions, point_uv, sampling = sample_surface(mesh.vertices, mesh.faces, point_uv, args.surface_spacing_mm*.001)
    if args.layer_spacing_mm is not None:
        if not sampling or not np.isfinite(args.layer_spacing_mm) or args.layer_spacing_mm <= 0:
            raise ValueError('Positive layer spacing requires dense surface sampling')
        point_positions = point_positions.copy()
        original_z = point_positions[:, 2].copy()
        layer_step = args.layer_spacing_mm*.001
        point_positions[:, 2] = np.rint(point_positions[:, 2]/layer_step)*layer_step
        sampling['layer_spacing_mm'] = args.layer_spacing_mm
        sampling['layer_axis'] = 'source-camera Z (near/far)'
        sampling['max_z_quantization_mm'] = float(np.max(abs(point_positions[:, 2]-original_z))*1000)
        assert np.max(abs(point_positions[:, 2]-original_z)) <= layer_step*.5+1e-12
        # Quantization can merge adjacent samples; remove duplicate XYZ points rather
        # than inflate the count with coincident points. Keep original ordering.
        _, retained = np.unique(np.round(point_positions/1e-9).astype(np.int64), axis=0, return_index=True)
        retained.sort()
        point_positions, point_uv = point_positions[retained], point_uv[retained]
        sampling['points_after_layer_deduplication'] = len(point_positions)
    if len(point_positions) < args.minimum_points:
        raise ValueError(f'Point count {len(point_positions)} is below required minimum {args.minimum_points}')
    # GLB coordinates are metres. Sample the actual material texture at each source UV.
    if mesh.visual.kind == 'texture':
        texture = np.asarray(mesh.visual.material.baseColorTexture.convert('RGB'))
        uv = point_uv
        def sample_colors(texcoords):
            coordinates = [(1 - texcoords[:, 1]) * (texture.shape[0] - 1), texcoords[:, 0] * (texture.shape[1] - 1)]
            sampled = np.column_stack([map_coordinates(texture[..., c].astype(float), coordinates, order=1, mode='nearest') for c in range(3)])
            return np.round(sampled).clip(0, 255).astype('uint8')
        rgb, mesh_rgb = sample_colors(uv), sample_colors(mesh.visual.uv)
    else:
        rgb = np.asarray(mesh.visual.vertex_colors[:, :3], dtype='uint8')
        mesh_rgb = rgb
    gray = np.round(rgb @ np.array([.2126, .7152, .0722])).astype('uint8')
    for name, color in [('points-color-mm.ply', rgb), ('points-gray-mm.ply', np.repeat(gray[:, None], 3, axis=1))]:
        cloud = trimesh.points.PointCloud(point_positions * 1000, colors=color)
        cloud.export(item_dir / name)
        restored = trimesh.load(item_dir / name, process=False)
        assert len(restored.vertices) == len(point_positions)
        assert np.allclose(restored.vertices, point_positions * 1000, atol=5e-6)
        assert np.array_equal(restored.colors[:, :3], color)
    (item_dir / 'relief.glb').write_bytes(original_bytes)
    payload = {'positions': encoded(mesh.vertices, '<f4'), 'normals': encoded(mesh.vertex_normals, '<f4'),
               'colors': encoded(mesh_rgb, 'u1'), 'triangles': encoded(mesh.faces, '<u4')}
    if sampling:
        payload.update({'pointPositions': encoded(point_positions, '<f4'), 'pointColors': encoded(rgb, 'u1')})
    (item_dir / 'geometry.json').write_text(json.dumps(payload), encoding='utf-8')
    report = {'id': args.id, 'label': args.label, 'vertices': len(mesh.vertices), 'point_count': len(point_positions), 'triangles': len(mesh.faces),
              'source_mesh': str(args.mesh.resolve()), 'source_sha256': hashlib.sha256(original_bytes).hexdigest(),
              'size_mm': (mesh.extents * 1000).tolist(), 'ply_units': 'millimetres', 'glb_units': 'metres',
              'sampling': sampling or 'one point per original vertex; bilinear source texture RGB at its UV',
              'geometry_unchanged': args.layer_spacing_mm is None, 'mesh_geometry_unchanged': True,
              'minimum_points': args.minimum_points, 'ply_roundtrip_verified': True}
    (item_dir / 'manifest.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    catalog_path = args.output_dir / 'catalog.json'
    catalog = json.loads(catalog_path.read_text()) if catalog_path.exists() else []
    if any(item['id'] == args.id for item in catalog):
        raise ValueError('Duplicate review id')
    catalog.append(report)
    catalog_path.write_text(json.dumps(catalog, indent=2, ensure_ascii=False), encoding='utf-8')
    template = Path(__file__).with_name('v35_point_review.html')
    shutil.copy2(template, args.output_dir / 'index.html')
    vendor = args.output_dir / 'vendor'
    vendor.mkdir(exist_ok=True)
    three = root / 'local-workbench/node_modules/three'
    for file in ['three.module.js', 'three.core.js']:
        shutil.copy2(three / 'build' / file, vendor / file)
    shutil.copy2(three / 'examples/jsm/controls/OrbitControls.js', vendor / 'OrbitControls.js')
    shutil.copy2(three / 'LICENSE', vendor / 'THREE-LICENSE.txt')
    assert args.mesh.read_bytes() == original_bytes
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
