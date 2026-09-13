"""
Purpose:
 - Preserve the user-selected E relief while testing narrow edge stretch and head repair.
 - Reuse source-registered ICON head depth only, keeping E body and fish geometry.
Context: Manual Pabbi-Bleikja experiment; no new network training or general face detector.
"""

import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
import trimesh
from PIL import Image
from scipy import ndimage
from scipy.interpolate import LinearNDInterpolator, NearestNDInterpolator

from build_portrait_v35 import export_surface, masked_smooth


def smoothstep(values):
    t = np.clip(values, 0, 1)
    return t * t * (3 - 2 * t)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline-dir', type=Path, required=True)
    parser.add_argument('--icon-mesh', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--extra-edge-mm', type=float, default=1.0)
    parser.add_argument('--edge-width', type=float, default=5.0)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    baseline_path = args.baseline_dir / 'D-transition/height-mm.npy'
    baseline_bytes = baseline_path.read_bytes()
    z = np.load(baseline_path).astype(float)
    mask = np.asarray(Image.open(args.baseline_dir / 'mesh-mask.png')) > 0
    texture = Image.open(args.source).convert('RGBA')
    h, w = z.shape
    yy, xx = np.mgrid[:h, :w]
    sx, sy = xx * (texture.width - 1) / (w - 1), yy * (texture.height - 1) / (h - 1)

    # Extend the existing inward Z transition, preserving the source silhouette and UVs.
    distance = ndimage.distance_transform_edt(mask)
    edge = -args.extra_edge_mm * (1 - smoothstep((distance - 1) / args.edge_width))
    edge[~mask] = 0
    edge_only = z + edge

    # Registration was already measured in the previous ICON run. Its head is a local
    # shape donor; the accepted E body must never be replaced by the ICON body.
    donor = trimesh.load(args.icon_mesh, force='mesh', process=False).vertices
    donor_x = donor[:, 0] * (texture.height - 1) / 2 + (texture.width - 1) / 2
    donor_y = (1 - donor[:, 1]) * (texture.height - 1) / 2
    selected = (donor_x > 325) & (donor_x < 700) & (donor_y < 525)
    points = np.column_stack((donor_x[selected], donor_y[selected]))
    values = donor[selected, 2] * 40
    head = LinearNDInterpolator(points, values)(sx, sy)
    missing = ~np.isfinite(head)
    head[missing] = NearestNDInterpolator(points, values)(sx[missing], sy[missing])

    # Manual source-image head region includes crown and face, tapering into the neck.
    polygon = np.array([[350, 170], [365, 70], [535, 60], [665, 120],
                        [665, 310], [620, 410], [575, 490], [410, 470], [350, 340]], float)
    polygon[:, 0] *= (w - 1) / (texture.width - 1)
    polygon[:, 1] *= (h - 1) / (texture.height - 1)
    region = np.zeros(z.shape, np.uint8)
    cv2.fillPoly(region, [np.round(polygon).astype(np.int32)], 1)
    weight = smoothstep(ndimage.distance_transform_edt(region) / 9)
    weight *= smoothstep((490 - sy) / 75)
    weight *= mask
    head_region = (weight > 0) & mask

    # Scale the donor to the E relief's depth range; no global depth/pose adjustment.
    core = (weight > .95) & (sy > 115) & (sy < 405) & ~missing
    source_span = np.ptp(np.percentile(head[core], [5, 95]))
    target_span = np.ptp(np.percentile(z[core], [5, 95]))
    scale = float(np.clip(target_span / source_span, .5, 1.2))
    aligned = head * scale
    offset = float(np.median(z[core] - aligned[core]))
    aligned += offset

    # Smooth crown depth only. Keep eyes, nose and mouth detail from the donor intact.
    crown = smoothstep((205 + .12 * (sx - 380) - sy) / 40) * head_region
    smooth_head = masked_smooth(aligned, head_region, 2.3)
    aligned = aligned * (1 - crown) + smooth_head * crown
    delta = np.clip(aligned - z, -4.0, 4.0) * weight
    combined = edge_only + delta

    # Exact preservation outside the declared edit support is part of this experiment.
    untouched = mask & (edge == 0) & (weight == 0)
    assert np.array_equal(combined[untouched], z[untouched])
    assert baseline_path.read_bytes() == baseline_bytes
    variants = {'E1-edge': edge_only, 'E2-head-edge': combined}
    metrics = {}
    baseline_mesh = trimesh.load(args.baseline_dir / 'D-transition/relief.glb', force='mesh', process=False)
    for name, depth in variants.items():
        metrics[name] = export_surface(depth, mask, texture, args.output_dir / name, 80.)
        restored = trimesh.load(args.output_dir / name / 'relief.glb', force='mesh', process=False)
        assert np.array_equal(restored.faces, baseline_mesh.faces)
        assert np.array_equal(restored.vertices[:, :2], baseline_mesh.vertices[:, :2])
        assert metrics[name]['finite_vertices'] and metrics[name]['nonmanifold_edges'] == 0
        assert metrics[name]['zero_area_triangles'] == 0
    np.save(args.output_dir / 'head-weight.npy', weight.astype('float32'))
    np.save(args.output_dir / 'extra-edge-mm.npy', edge.astype('float32'))
    report = {
        'status': 'RESEARCH_CANDIDATE_AWAITING_VISUAL_REVIEW',
        'selected_baseline': str(args.baseline_dir.resolve()),
        'baseline_depth_sha256': hashlib.sha256(baseline_bytes).hexdigest(),
        'head_donor': str(args.icon_mesh.resolve()), 'manual_image_specific_head_region': True,
        'extra_edge_mm': args.extra_edge_mm, 'edge_width_grid_px': args.edge_width,
        'head_depth_scale': scale, 'head_depth_offset_mm': offset,
        'head_delta_cap_mm': 4., 'head_changed_pixels': int(np.count_nonzero(delta[mask])),
        'head_max_change_mm': float(np.max(abs(delta[mask]))),
        'head_interpolator_fallback_pixels': int(np.count_nonzero(missing & head_region)),
        'body_interior_exactly_unchanged': True, 'xy_uv_topology_preserved': True,
        'metrics': metrics,
        'limitations': ['Manual head region; not an automatic general pipeline.',
                       'Extra stretch is inward Z displacement, not inferred hidden anatomy.',
                       'Head depth is reused from existing ICON inference, not new model training.'],
    }
    (args.output_dir / 'experiment.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
