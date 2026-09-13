"""
Purpose:
 - Run a final face-only shape pass after body, hair and object geometry are complete.
 - Prefer a registered HRN front depth donor; use detected 3D face landmarks as fallback.
Context: No closed head is attached. Face edits stay on the original UV heightfield.
"""

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
import trimesh
from PIL import Image
from scipy import ndimage
from scipy.interpolate import LinearNDInterpolator

from build_portrait_v35 import export_surface, masked_smooth
from face_support_v35 import face_support


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--landmarks', type=Path, required=True)
    parser.add_argument('--hrn-assets', type=Path)
    parser.add_argument('--registration', type=Path)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--max-change-mm', type=float, default=3.)
    parser.add_argument('--boundary-width-px', type=float, help='Optional override; otherwise adapt the blend width to each face.')
    parser.add_argument('--broad-shape-retention', type=float, default=.2, help='Keep this fraction of broad donor depth disagreement; suppress patch seams.')
    parser.add_argument('--visibility-mask', type=Path, help='Optional source-sized grayscale mask; black protects occluded facial areas.')
    args = parser.parse_args()
    if bool(args.hrn_assets) != bool(args.registration):
        parser.error('HRN assets and measured registration must be supplied together')
    texture = Image.open(args.source).convert('RGBA')
    base = np.load(args.baseline / 'height-mm.npy').astype(float)
    mesh = trimesh.load(args.baseline / 'relief.glb', force='mesh', process=False)
    h, w = base.shape
    mask = np.zeros((h, w), bool)
    uv = mesh.visual.uv
    mask[np.rint((1-uv[:, 1])*(h-1)).astype(int), np.rint(uv[:, 0]*(w-1)).astype(int)] = True
    yy, xx = np.mgrid[:h, :w]
    source_x, source_y = xx*(texture.width-1)/(w-1), yy*(texture.height-1)/(h-1)
    faces = json.loads(args.landmarks.read_text())['faces']
    visibility_mask = None
    if args.visibility_mask:
        visible_image = Image.open(args.visibility_mask).convert('L')
        if visible_image.size != texture.size:
            raise ValueError('Visibility mask must match the source image dimensions')
        visibility_mask = np.asarray(visible_image.resize((w,h), Image.Resampling.NEAREST)) >= 128
    result, support = base.copy(), np.zeros(base.shape, bool)
    reports = []
    for face in faces:
        try:
            landmarks, face_mask, support_report = face_support(face, np.asarray(texture.getchannel('A')), base.shape)
        except ValueError as error:
            reports.append({'backend': 'unchanged-needs-review', 'reason': str(error)})
            continue
        face_mask &= mask
        if visibility_mask is not None:
            face_mask &= visibility_mask
            support_report['visibility_mask_supplied'] = True
        if face_mask.sum() < 20:
            reports.append({'backend': 'unchanged-needs-review', 'reason': 'Too little visible face surface after masking'})
            continue
        distance = ndimage.distance_transform_edt(face_mask)
        effective_boundary = args.boundary_width_px or support_report['boundary_width_grid_px']
        t = np.clip(distance/effective_boundary, 0, 1)
        weight = t*t*(3-2*t)
        backend = 'landmark-shape-fallback'
        registration_metrics = None
        if args.hrn_assets:
            if len(faces) != 1:
                raise ValueError('One HRN donor cannot be applied to multiple faces')
            registration = json.loads(args.registration.read_text())
            if Path(registration['source']).resolve() != args.source.resolve():
                raise ValueError('HRN registration belongs to a different source image')
            registration_metrics = registration['registration']
            if registration_metrics['inliers'] < 15 or registration_metrics['median_reprojection_error_px'] > 2.:
                raise ValueError('HRN registration does not meet the face-only gate')
            affine = np.asarray(registration_metrics['affine_hrn_to_source'])
            metadata = json.loads((args.hrn_assets / 'hrn-front-assets.json').read_text())
            rgba = cv2.imread(str(args.hrn_assets / 'hrn-front-depth.png'), cv2.IMREAD_UNCHANGED)
            srgb = rgba[..., 0].astype(float)/65535.
            linear = np.where(srgb <= .04045, srgb/12.92, ((srgb+.055)/1.055)**2.4)
            native_range = metadata['camera']['far_object_y']-metadata['camera']['near_object_y']
            native_to_source_pixels = np.sqrt(abs(np.linalg.det(affine[:, :2]))) * metadata['resolution']/metadata['camera']['ortho_scale']
            native_to_mm = native_to_source_pixels * 80/(texture.height-1)
            native = linear*native_range*native_to_mm
            grid_affine = affine * np.array([[(w-1)/(texture.width-1)], [(h-1)/(texture.height-1)]])
            donor = cv2.warpAffine(native, grid_affine, (w,h), flags=cv2.INTER_LINEAR)
            valid = cv2.warpAffine((rgba[..., 3]>0).astype(np.uint8), grid_affine, (w,h), flags=cv2.INTER_NEAREST) > 0
            weight *= valid
            backend = 'registered-HRN-visible-face-only'
        else:
            donor = LinearNDInterpolator(landmarks[:, :2], -landmarks[:, 2])(source_x, source_y)
            valid = np.isfinite(donor) & face_mask
            if valid.sum() < 20:
                raise ValueError('Insufficient landmark coverage for a final face pass')
            donor = np.nan_to_num(donor)
            span = np.ptp(np.percentile(donor[valid], [5,95]))
            face_width_mm = np.ptp(landmarks[:, 0])*80/(texture.height-1)
            donor *= face_width_mm*.22/max(span, 1e-8)
            donor = masked_smooth(donor, valid, .65)
            weight *= valid
        # Match boundary position and broad tilt, then replace only local face shape.
        ring = (weight > .02) & (weight < .85) & face_mask
        if ring.sum() < 20:
            raise ValueError('Face boundary cannot be aligned reliably')
        design = np.stack([np.ones_like(xx), (xx-xx[face_mask].mean())/w, (yy-yy[face_mask].mean())/h], -1)
        coefficients = np.linalg.lstsq(design[ring], (base-donor)[ring], rcond=None)[0]
        target = donor + design @ coefficients
        detail = np.clip(base-masked_smooth(base, face_mask, 2.), -.18, .18)
        disagreement = target+detail-base
        broad = masked_smooth(disagreement, face_mask & (weight>0), support_report['broad_smoothing_grid_px'])
        # Preserve the established broad face placement. Transfer the donor's local
        # eye/nose/mouth form while reducing a visible ridge at the patch perimeter.
        correction = disagreement - (1-args.broad_shape_retention)*broad
        delta = np.clip(correction, -args.max_change_mm, args.max_change_mm)*weight
        result += delta
        support |= weight > 0
        reports.append({'backend': backend, 'face_box': face.get('box'), 'modified_pixels': int(np.count_nonzero(delta)),
                        'support': support_report,
                        'max_change_mm': float(np.max(abs(delta))), 'registration': registration_metrics,
                        'boundary_plane_coefficients': coefficients.tolist(),
                        'limitation': 'Visible face only; fallback landmarks are lower-detail than dedicated reconstruction.'})
    assert np.array_equal(result[~support], base[~support])
    args.output_dir.mkdir(parents=True, exist_ok=False)
    output_mesh = args.output_dir / 'mesh'
    metrics = export_surface(result, mask, texture, output_mesh, 80.)
    restored = trimesh.load(output_mesh / 'relief.glb', force='mesh', process=False)
    assert np.array_equal(restored.faces, mesh.faces)
    assert np.array_equal(restored.vertices[:, :2], mesh.vertices[:, :2])
    assert metrics['nonmanifold_edges'] == 0 and metrics['zero_area_triangles'] == 0
    np.save(args.output_dir / 'face-support.npy', support)
    report = {'baseline': str(args.baseline.resolve()), 'source': str(args.source.resolve()),
              'status': 'FINAL_FACE_PASS_CANDIDATE', 'outside_faces_unchanged': True,
              'xy_uv_topology_unchanged': True, 'boundary_width_grid_px': args.boundary_width_px,
              'broad_shape_retention': args.broad_shape_retention, 'faces': reports, 'metrics': metrics}
    (args.output_dir / 'face-pass.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
