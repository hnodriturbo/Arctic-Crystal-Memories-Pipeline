"""
File: code/research/prepare_v35_reference.py
Purpose:
 - Register the supplied cutout to reference UVs and exclude unprinted background.
 - Preserve original Cockpit geometry; write a separate masked comparison artifact.
"""

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
import trimesh
from PIL import Image
from scipy.ndimage import map_coordinates

from build_glb_from_cockpit import load_decoded_mesh
from source_camera_fusion import estimate_similarity_registration


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error('Use a new output directory.')
    report = json.loads((args.reference / 'report.json').read_text())
    reference_image = Image.open(args.reference / 'source' / report['assets']['texture']).convert('RGB')
    source = Image.open(args.source).convert('RGBA')
    affine, metrics, *_ = estimate_similarity_registration(np.asarray(reference_image), np.asarray(source.convert('RGB')), .7, 2.)
    if metrics['inliers'] < 40 or metrics['inlier_ratio'] < .75 or metrics['median_reprojection_error_px'] > 1.:
        raise RuntimeError(f'Reference registration failed: {metrics}')
    metadata = json.loads((args.reference / 'decoded-ci-buffer.json').read_text(encoding='utf-8-sig'))
    v, uv, n, f = load_decoded_mesh(args.reference / 'decoded-ci-buffer.bin', metadata)
    ref_pixels = np.column_stack((uv[:, 0] * (reference_image.width - 1), (1 - uv[:, 1]) * (reference_image.height - 1)))
    pixels = cv2.transform(ref_pixels[None].astype('float32'), affine)[0]
    alpha = map_coordinates(np.asarray(source.getchannel('A'), dtype=float),
        [pixels[:, 1], pixels[:, 0]], order=1, mode='constant', cval=0)
    valid = alpha >= 128
    faces = f[valid[f].all(1)]
    used, inverse = np.unique(faces, return_inverse=True)
    mesh = trimesh.Trimesh(v[used], inverse.reshape(-1, 3), process=False)
    material = trimesh.visual.material.PBRMaterial(baseColorTexture=reference_image, metallicFactor=0, roughnessFactor=1, doubleSided=True)
    mesh.visual = trimesh.visual.texture.TextureVisuals(uv=uv[used], material=material)
    mesh.apply_translation(-mesh.bounds.mean(0))
    mesh.apply_scale(.08 / mesh.extents[1])
    args.output_dir.mkdir(parents=True)
    (args.output_dir / 'reference-masked.glb').write_bytes(trimesh.Scene(mesh).export(file_type='glb'))
    np.save(args.output_dir / 'valid-reference-vertices.npy', valid)
    result = {'source': str(args.source.resolve()), 'reference': str(args.reference.resolve()),
        'affine_reference_to_source': affine.tolist(), 'registration': metrics,
        'vertices_before': len(v), 'vertices_after': len(used), 'faces_after': len(faces),
        'depth_height_ratio_foreground': float(mesh.extents[2] / mesh.extents[1]),
        'note': 'Source alpha used only for comparison clipping; original reference buffers unchanged.'}
    (args.output_dir / 'registration.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
