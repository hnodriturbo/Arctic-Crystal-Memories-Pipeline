"""
Purpose:
 - Test the transferable E stages on another supplied cutout with frozen style parameters.
 - Refine its own detected face; never reuse Pabbi's manual head region on another image.
Context: The image-specific ICON head replacement in E2 is deliberately not generalized here.
"""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

from build_portrait_v35 import export_surface


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--calibration', type=Path, required=True)
    parser.add_argument('--calibration-mask', type=Path, required=True)
    parser.add_argument('--preserve-depth-range', action=argparse.BooleanOptionalAction, default=True, help='Avoid percentile clipping; use --no-preserve-depth-range only for the earlier comparison.')
    parser.add_argument('--hrn-assets', type=Path)
    parser.add_argument('--hrn-registration', type=Path)
    parser.add_argument('--visibility-mask', type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    geometry_python = root / 'Models/runtimes/.venv-geometry/Scripts/python.exe'
    standard_python = root / '.venv/Scripts/python.exe'
    source = args.source.resolve()
    inference = json.loads((args.run_dir / '01-moge/inference.json').read_text())
    assert inference['source_sha256'] == hashlib.sha256(source.read_bytes()).hexdigest()
    data = np.load(args.run_dir / '01-moge/geometry.npz')
    texture = Image.open(source).convert('RGBA')
    mask = np.asarray(texture.getchannel('A')) >= 128
    near = -data['depth']
    valid = mask & np.isfinite(near)
    low, high = np.percentile(near[valid], [0, 100] if args.preserve_depth_range else [1, 99])
    face_dir = args.run_dir / '02-face'
    face_dir.mkdir(exist_ok=False)
    Image.fromarray(np.round(np.clip((near-low)/(high-low), 0, 1)*65535).astype('uint16')).save(face_dir / 'baseline-depth.png')
    (face_dir / 'normalization.json').write_text(json.dumps({'near_low': float(low), 'near_high': float(high)}))
    subprocess.run([str(geometry_python), str(root / 'code/face_refine.py'),
                    '--input', str((args.run_dir / '01-moge/inference-input.png').resolve()),
                    '--depth', str((face_dir / 'baseline-depth.png').resolve()),
                    '--output', str((face_dir / 'refined-depth.png').resolve()),
                    '--aux-output', str((face_dir / 'qa').resolve()), '--device', 'cuda',
                    '--known-face-count', '1', '--moge-model', 'vitl', '--moge-resolution-level', '9', '--shape-mix', '.8'], cwd=root, check=True)
    variants = args.run_dir / '03-e-variants'
    subprocess.run([str(standard_python), str(root / 'code/research/build_portrait_v35.py'),
                    '--source', str(source), '--geometry', str((args.run_dir / '01-moge/geometry.npz').resolve()),
                    '--reference', str(args.calibration.resolve()), '--reference-mask', str(args.calibration_mask.resolve()),
                    '--refined-depth', str((face_dir / 'refined-depth.png').resolve()),
                    '--normalization-json', str((face_dir / 'normalization.json').resolve()),
                    '--coarse-sigma', '1.5', '--output-dir', str(variants.resolve())]
                   + (['--preserve-shape-tails'] if args.preserve_depth_range else []), cwd=root, check=True)
    z = np.load(variants / 'D-transition/height-mm.npy').astype(float)
    foreground = np.asarray(Image.open(variants / 'mesh-mask.png')) > 0
    distance = ndimage.distance_transform_edt(foreground)
    t = np.clip((distance - 1) / 5., 0, 1)
    extra = -(1 - t*t*(3-2*t))
    extra[~foreground] = 0
    final = z + extra
    assert np.array_equal(final[foreground & (extra == 0)], z[foreground & (extra == 0)])
    metrics = export_surface(final, foreground, texture, args.run_dir / '04-e-transfer-edge', 80.)
    # Every new transfer run finishes face geometry before sampling its stretch surfaces.
    face_output = args.run_dir / '05-final-face'
    face_command = [str(standard_python), str(root / 'code/research/finalize_v35_faces.py'),
                    '--baseline', str((args.run_dir / '04-e-transfer-edge').resolve()),
                    '--source', str(source), '--landmarks', str((face_dir / 'refined-depth.json').resolve()),
                    '--output-dir', str(face_output.resolve())]
    if args.hrn_assets or args.hrn_registration:
        if not args.hrn_assets or not args.hrn_registration:
            raise ValueError('Provide both HRN assets and their source registration')
        face_command += ['--hrn-assets', str(args.hrn_assets.resolve()), '--registration', str(args.hrn_registration.resolve())]
    if args.visibility_mask:
        face_command += ['--visibility-mask', str(args.visibility_mask.resolve())]
    subprocess.run(face_command, cwd=root, check=True)
    subprocess.run([str(standard_python), str(root / 'code/research/export_v35_point_review.py'),
                    '--mesh', str((face_output / 'mesh/relief.glb').resolve()),
                    '--output-dir', str((args.run_dir / '06-point-review').resolve()),
                    '--id', 'result', '--label', source.stem,
                    '--point-spacing-mm', '.08', '--layer-spacing-mm', '.09'], cwd=root, check=True)
    report = {'source': str(source), 'source_sha256': inference['source_sha256'],
              'status': 'TRANSFER_TEST_NOT_USER_APPROVED', 'extra_edge_mm': 1., 'extra_edge_width_grid_px': 5.,
              'preserve_depth_range': args.preserve_depth_range,
              'final_face_report': str((face_output / 'face-pass.json').resolve()),
              'final_point_review': str((args.run_dir / '06-point-review').resolve()),
              'point_spacing_mm': .08, 'layer_spacing_mm': .09,
              'calibration': str(args.calibration.resolve()),
              'calibration_note': 'Frozen dad-fish global tilt and relative depth span; style hypothesis, not pose ground truth.',
              'transferred': ['MoGe depth and normals', 'own detected face crop refinement', 'screened normal integration', 'single fixed-UV surface', 'narrow edge stretch'],
              'not_transferred': ['manual Pabbi ICON head replacement', 'manual bald scalp smoothing'], 'metrics': metrics}
    (args.run_dir / 'transfer.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
