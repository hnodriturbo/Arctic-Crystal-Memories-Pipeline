"""
File: code/research/build_portrait_v35.py
Purpose:
 - Build controlled source-aligned relief variants with screened normal integration.
 - Measure reference shape independently and preserve every variant and its evidence.
Context:
 - Research only; a source heightfield is not a complete head or a trained ACM network.
 - Internal coordinates are millimetres; GLB exports convert them to standard metres.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
import trimesh
from PIL import Image
from scipy import ndimage, sparse
from scipy.sparse.linalg import cg
from scipy.spatial import cKDTree

from build_glb_from_cockpit import load_decoded_mesh


def measure_references(paths, masks=None):
    """Measure source-space form, independent of crystal transforms and vertex order."""
    reports, meshes = [], []
    for index, path in enumerate(paths):
        metadata = json.loads((path / 'decoded-ci-buffer.json').read_text(encoding='utf-8-sig'))
        vertices, uv, normals, faces = load_decoded_mesh(path / 'decoded-ci-buffer.bin', metadata)
        if masks:
            selected = np.load(masks[index]).astype(bool)
            faces = faces[selected[faces].all(1)]
            vertices, uv = vertices[selected], uv[selected]
        height = np.ptp(vertices[:, 1])
        y = (vertices[:, 1] - vertices[:, 1].min()) / height
        z = vertices[:, 2] / height
        samples = []
        for center in np.linspace(.05, .95, 19):
            selected = z[abs(y - center) < .025]
            if len(selected):
                samples.append([float(center), *np.percentile(selected, [10, 50, 90]).tolist()])
        bins = np.asarray(samples)
        slope, intercept = np.polyfit(bins[:, 0], bins[:, 2], 1)
        residual = z - (slope * y + intercept)
        report = {
            'path': str(path), 'vertices': len(vertices), 'triangles': len(faces),
            'depth_height_ratio': float(np.ptp(z)), 'z_per_y_slope': float(slope),
            'residual_p99_p1_per_height': float(np.ptp(np.percentile(residual, [1, 99]))),
            'row_quantiles_y_p10_p50_p90': samples,
            'xy_uv_correlation': [float(np.corrcoef(vertices[:, i], uv[:, i])[0, 1]) for i in (0, 1)],
        }
        reports.append(report)
        meshes.append((vertices, uv))
    if len(meshes) == 2:
        distance, index = cKDTree(meshes[1][1]).query(meshes[0][1])
        delta = meshes[0][0][:, 2] - meshes[1][0][index, 2]
        reports[0]['pair_uv_nearest_p99'] = float(np.percentile(distance, 99))
        reports[0]['pair_aligned_z_difference_p50_p99'] = np.percentile(abs(delta), [50, 99]).tolist()
    return reports


def normal_near_gradients(depth, normals, intrinsics):
    """Convert perspective camera normals to near-positive depth gradients per pixel."""
    height, width = depth.shape
    yy, xx = np.mgrid[:height, :width]
    # MoGe intrinsics are normalized to image width/height; sample pixel centres.
    fx, fy = intrinsics[0, 0] * width, intrinsics[1, 1] * height
    cx, cy = intrinsics[0, 2] * width, intrinsics[1, 2] * height
    rays = np.stack(((xx + .5 - cx) / fx, (yy + .5 - cy) / fy, np.ones_like(xx)), -1)
    dot = np.sum(normals * rays, -1)
    valid = np.isfinite(depth) & (abs(dot) > .15)
    denominator = np.where(valid, dot, 1)
    gx = np.where(valid, depth * normals[..., 0] / (fx * denominator), 0)
    gy = np.where(valid, depth * normals[..., 1] / (fy * denominator), 0)
    return gx, gy, valid


def screened_integration(gx, gy, mask, anchor_weight=.12, edge_x=None, edge_y=None):
    """Integrate gradients within the mask; gaps have no graph edges or periodic wrap."""
    ids = np.full(mask.shape, -1, dtype=np.int64)
    ids[mask] = np.arange(mask.sum())
    if not mask.any():
        raise ValueError('Cannot integrate an empty mask')
    horizontal = mask[:, :-1] & mask[:, 1:]
    vertical = mask[:-1] & mask[1:]
    left = np.concatenate((ids[:, :-1][horizontal], ids[:-1][vertical]))
    right = np.concatenate((ids[:, 1:][horizontal], ids[1:][vertical]))
    gradient = np.concatenate((((gx[:, :-1] + gx[:, 1:]) * .5)[horizontal], ((gy[:-1] + gy[1:]) * .5)[vertical]))
    weight = np.concatenate((np.ones(horizontal.sum()) if edge_x is None else edge_x[horizontal],
                             np.ones(vertical.sum()) if edge_y is None else edge_y[vertical]))
    count = int(mask.sum())
    diagonal = np.full(count, anchor_weight) + np.bincount(left, weight, minlength=count) + np.bincount(right, weight, minlength=count)
    matrix = sparse.coo_matrix((np.concatenate((diagonal, -weight, -weight)),
        (np.concatenate((np.arange(count), left, right)), np.concatenate((np.arange(count), right, left)))), shape=(count, count)).tocsr()
    rhs = np.bincount(right, gradient * weight, minlength=count) - np.bincount(left, gradient * weight, minlength=count)
    preconditioner = sparse.diags(1 / diagonal)
    solution, status = cg(matrix, rhs, M=preconditioner, rtol=1e-5, atol=1e-8, maxiter=250)
    if status != 0:
        raise RuntimeError(f'Normal integration did not converge: {status}')
    result = np.zeros(mask.shape)
    result[mask] = solution
    return result


def masked_smooth(values, mask, sigma):
    weights = ndimage.gaussian_filter(mask.astype(float), sigma)
    return ndimage.gaussian_filter(np.where(mask, values, 0), sigma) / np.maximum(weights, 1e-9)


def export_surface(z, mask, texture, path, height_mm):
    """Export a single cut grid with fixed UVs; no generic closure or invented anatomy."""
    rows, cols = z.shape
    pixel_mm = height_mm / (rows - 1)
    yy, xx = np.mgrid[:rows, :cols]
    vertices = np.stack(((xx - (cols - 1) / 2) * pixel_mm,
        ((rows - 1) / 2 - yy) * pixel_mm, z), -1).reshape(-1, 3)
    indices = np.arange(rows * cols).reshape(rows, cols)
    a, b, c, d = indices[:-1, :-1], indices[:-1, 1:], indices[1:, :-1], indices[1:, 1:]
    # Winding faces +Z in the source-facing orthographic coordinate convention.
    faces = np.concatenate((np.stack((a, c, b), -1).reshape(-1, 3), np.stack((b, c, d), -1).reshape(-1, 3)))
    faces = faces[mask.ravel()[faces].all(1)]
    used, inverse = np.unique(faces, return_inverse=True)
    faces = inverse.reshape(-1, 3)
    uv = np.stack((xx / (cols - 1), 1 - yy / (rows - 1)), -1).reshape(-1, 2)[used]
    material = trimesh.visual.material.PBRMaterial(name='Original source', baseColorTexture=texture, metallicFactor=0., roughnessFactor=1., doubleSided=True)
    mesh = trimesh.Trimesh(vertices=vertices[used], faces=faces, process=False,
        visual=trimesh.visual.texture.TextureVisuals(uv=uv, material=material))
    mesh.metadata.update({'units': 'mm', 'status': 'RESEARCH_CANDIDATE', 'method': 'v35_single_surface'})
    path.mkdir(parents=True, exist_ok=False)
    mesh.export(path / 'relief-mm.obj')
    glb_mesh = mesh.copy()
    glb_mesh.apply_scale(.001)
    glb_mesh.metadata['units'] = 'm'
    (path / 'relief.glb').write_bytes(trimesh.Scene(glb_mesh).export(file_type='glb'))
    np.save(path / 'height-mm.npy', z.astype('float32'))
    edges, counts = np.unique(mesh.edges_sorted, axis=0, return_counts=True)
    metrics = {'vertices': len(mesh.vertices), 'triangles': len(mesh.faces),
        'bounds_mm': mesh.bounds.tolist(), 'size_mm': mesh.extents.tolist(),
        'depth_height_ratio': float(mesh.extents[2] / mesh.extents[1]),
        'boundary_edges': int((counts == 1).sum()), 'nonmanifold_edges': int((counts > 2).sum()),
        'zero_area_triangles': int((mesh.area_faces < 1e-12).sum()),
        'finite_vertices': bool(np.isfinite(mesh.vertices).all()),
        'front_projection': 'Fixed source UV grid, orthographic; relief approximation to source perspective',
        'glb_units': 'metres', 'obj_units': 'millimetres'}
    (path / 'metrics.json').write_text(json.dumps(metrics, indent=2), encoding='utf-8')
    return metrics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--geometry', type=Path, required=True)
    parser.add_argument('--reference', action='append', type=Path, required=True)
    parser.add_argument('--reference-mask', action='append', type=Path)
    parser.add_argument('--refined-depth', type=Path)
    parser.add_argument('--normalization-json', type=Path)
    parser.add_argument('--coarse-sigma', type=float, default=1.5)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--grid', type=int, default=640)
    parser.add_argument('--height-mm', type=float, default=80.)
    parser.add_argument('--normal-cap-mm', type=float, default=.6)
    parser.add_argument('--transition-mm', type=float, default=.6)
    parser.add_argument('--preserve-shape-tails', action='store_true', help='Use robust quantiles for scale only; avoid flattening the depth tails.')
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error('Use a new output directory for each experiment.')
    if args.reference_mask and len(args.reference_mask) != len(args.reference):
        parser.error('Supply one mask per reference.')
    if bool(args.refined_depth) != bool(args.normalization_json):
        parser.error('Refined depth and normalization metadata must be supplied together.')
    references = measure_references(args.reference, args.reference_mask)
    texture = Image.open(args.source).convert('RGBA')
    ratio = args.grid / max(texture.size)
    size = (round(texture.width * ratio), round(texture.height * ratio))
    alpha = np.asarray(texture.getchannel('A').resize(size, Image.Resampling.LANCZOS))
    mask = alpha >= 128
    # Remove only tiny disconnected alpha specks; retain legitimate larger components.
    labels, count = ndimage.label(mask)
    areas = np.bincount(labels.ravel())
    small = areas < max(4, mask.sum() * .00005)
    small[0] = True
    mask &= ~small[labels]
    data = np.load(args.geometry)
    depth = cv2.resize(data['depth'], size, interpolation=cv2.INTER_LINEAR).astype(float)
    if args.refined_depth:
        normalization = json.loads(args.normalization_json.read_text())
        refined = np.asarray(Image.open(args.refined_depth), dtype=float) / 65535
        refined_near = normalization['near_low'] + refined * (normalization['near_high'] - normalization['near_low'])
        depth = -cv2.resize(refined_near, size, interpolation=cv2.INTER_LINEAR)
    normal = cv2.resize(data['normal'], size, interpolation=cv2.INTER_LINEAR).astype(float)
    normal /= np.maximum(np.linalg.norm(normal, axis=-1, keepdims=True), 1e-8)
    mask &= np.isfinite(depth) & (depth > 0)
    if not mask.any():
        raise ValueError('No valid foreground')
    yy, xx = np.mgrid[:size[1], :size[0]]
    y = 1 - yy / (size[1] - 1)
    near = -depth
    coarse = masked_smooth(near, mask, args.coarse_sigma)
    source_trend = np.polyfit(y[mask], coarse[mask], 1)
    residual = coarse - np.polyval(source_trend, y)
    low, high = np.percentile(residual[mask], [1, 99])
    if high - low < 1e-6:
        raise ValueError('Foreground depth is effectively flat')
    target_span = float(np.mean([r['residual_p99_p1_per_height'] for r in references])) * args.height_mm
    metric_scale = target_span / (high - low)
    tilt = float(np.mean([r['z_per_y_slope'] for r in references]))
    base = tilt * (y - .5) * args.height_mm
    scaled_residual = residual if args.preserve_shape_tails else np.clip(residual, low, high)
    shape = (scaled_residual - (high + low) / 2) * metric_scale
    before = base + shape

    # Screen normal integration around the depth baseline and stop at occlusion jumps.
    gx, gy, normal_valid = normal_near_gradients(depth, normal, data['intrinsics'])
    inner = mask & normal_valid
    gx = (gx - masked_smooth(gx, inner, 10)) * metric_scale
    gy = (gy - masked_smooth(gy, inner, 10)) * metric_scale
    jump = max(float(np.percentile(abs(np.diff(depth, axis=1))[mask[:, :-1] & mask[:, 1:]], 95)), .002)
    wx = np.exp(-(np.diff(depth, axis=1) / jump) ** 2)
    wy = np.exp(-(np.diff(depth, axis=0) / jump) ** 2)
    correction = screened_integration(gx, gy, inner, edge_x=wx, edge_y=wy)
    correction = np.clip(correction, -args.normal_cap_mm, args.normal_cap_mm)
    distance = ndimage.distance_transform_edt(mask)
    correction *= np.clip((distance - 1) / 3, 0, 1)
    transition = -args.transition_mm * np.clip(1 - (distance - 1) / 3, 0, 1) ** 2
    variants = {'A-base': base, 'B-depth': before, 'C-normals': before + correction,
                'D-transition': before + correction + transition}
    args.output_dir.mkdir(parents=True)
    Image.fromarray((mask * 255).astype('uint8')).save(args.output_dir / 'mesh-mask.png')
    metrics = {}
    for name, z in variants.items():
        z = z - (z[mask].min() + z[mask].max()) / 2
        metrics[name] = export_surface(z, mask, texture, args.output_dir / name, args.height_mm)
    report = {'status': 'RESEARCH_CANDIDATE', 'reference_measurements': references,
        'source': str(args.source.resolve()), 'geometry': str(args.geometry.resolve()),
        'settings': {'grid': size, 'height_mm': args.height_mm, 'reference_tilt': tilt,
            'original_depth_trend': source_trend.tolist(), 'mm_per_predicted_m': metric_scale,
            'normal_cap_mm': args.normal_cap_mm, 'normal_mean_abs_mm': float(abs(correction[mask]).mean()),
            'transition_mm': args.transition_mm, 'transition_width_grid_px': 3},
        'face_refinement': str(args.refined_depth) if args.refined_depth else None,
        'coarse_sigma_grid_px': args.coarse_sigma, 'preserve_shape_tails': args.preserve_shape_tails,
        'limitations': ['Reference-derived tilt is a controlled hypothesis for this photograph, not a general pose rule.',
            'Selected source is an existing cutout; neutral-grey inference is an explicit background hypothesis.',
            'Normals supply screened medium/fine shape; no ground-truth depth or new neural model is trained.',
            'Generic full-head, hair shell and hidden anatomy are absent.'], 'variants': metrics}
    (args.output_dir / 'experiment.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
