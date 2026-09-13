"""
File: code/research/infer_v35_geometry.py
Purpose:
 - Preserve float MoGe depth, normals and camera intrinsics for v3.5 experiments.
 - Composite supplied cutouts on neutral grey without altering the source file.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from moge.model.v2 import MoGeModel


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--resolution-level', type=int, default=9)
    args = parser.parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        parser.error('Output directory must be new or empty.')
    args.output_dir.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()

    # Keep source colour and alpha independent from the input background hypothesis.
    source = Image.open(args.source).convert('RGBA')
    composite = Image.new('RGB', source.size, (127, 127, 127))
    composite.paste(source.convert('RGB'), mask=source.getchannel('A'))
    composite.save(args.output_dir / 'inference-input.png')
    source.getchannel('A').save(args.output_dir / 'source-alpha.png')
    tensor = torch.from_numpy(np.asarray(composite).copy()).permute(2, 0, 1).float().cuda() / 255
    model = MoGeModel.from_pretrained(args.checkpoint).cuda().eval()
    print('MoGe ViT-L inference starting', flush=True)
    with torch.inference_mode():
        result = model.infer(tensor, resolution_level=args.resolution_level, apply_mask=False, use_fp16=True)
    arrays = {k: result[k].detach().float().cpu().numpy() for k in ('depth', 'normal', 'intrinsics', 'mask') if k in result}
    np.savez_compressed(args.output_dir / 'geometry.npz', **arrays)
    Image.fromarray(((arrays['normal'] + 1) * 127.5).clip(0, 255).astype('uint8')).save(args.output_dir / 'normal.png')
    report = {
        'source': str(args.source.resolve()),
        'source_sha256': hashlib.sha256(args.source.read_bytes()).hexdigest(),
        'checkpoint': str(args.checkpoint.resolve()),
        'checkpoint_sha256': hashlib.sha256(args.checkpoint.read_bytes()).hexdigest(),
        'resolution_level': args.resolution_level,
        'torch': torch.__version__, 'gpu': torch.cuda.get_device_name(),
        'elapsed_seconds': time.perf_counter() - started,
        'background': 'neutral grey composite from supplied cutout; original background unavailable in this file',
        'shapes': {k: list(v.shape) for k, v in arrays.items()},
        'intrinsics_normalized': arrays['intrinsics'].tolist(),
    }
    (args.output_dir / 'inference.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
