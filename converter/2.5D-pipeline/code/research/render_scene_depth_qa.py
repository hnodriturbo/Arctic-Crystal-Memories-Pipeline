"""
File: code/research/render_scene_depth_qa.py
Purpose:
 - Turn raw MoGe float depth into readable near/far color and source-overlay diagnostics.
 - Record robust percentiles without changing the raw scene-depth artifact.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--raw-depth", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--clip-percent", type=float, default=1.0)
    return parser.parse_args()


def annotate(image: np.ndarray, low: float, high: float) -> Image.Image:
    rendered = Image.fromarray(image)
    draw = ImageDraw.Draw(rendered)
    font = ImageFont.load_default(size=18)
    draw.rounded_rectangle((14, 14, 395, 74), radius=8, fill=(0, 0, 0, 190))
    draw.text((26, 23), "MoGe raw depth: red = near, blue = far", fill="white", font=font)
    draw.text((26, 48), f"robust range {low:.4f} .. {high:.4f}", fill="white", font=font)
    return rendered


def main() -> None:
    args = parse_arguments()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    source = np.array(Image.open(args.source).convert("RGB"))
    depth = np.load(args.raw_depth).astype(np.float32)
    if depth.shape != source.shape[:2]:
        raise RuntimeError(f"Depth {depth.shape} does not match source {source.shape[:2]}")
    valid = np.isfinite(depth)
    low, high = np.percentile(depth[valid], [args.clip_percent, 100.0 - args.clip_percent])
    near = 1.0 - np.clip((depth - low) / (high - low), 0.0, 1.0)
    near_u8 = np.round(near * 255.0).astype(np.uint8)
    color_bgr = cv2.applyColorMap(near_u8, cv2.COLORMAP_TURBO)
    color_rgb = cv2.cvtColor(color_bgr, cv2.COLOR_BGR2RGB)
    overlay = np.round(source * 0.42 + color_rgb * 0.58).astype(np.uint8)
    annotate(color_rgb, float(low), float(high)).save(output_dir / "raw_depth_color.png", optimize=True)
    annotate(overlay, float(low), float(high)).save(output_dir / "raw_depth_source_overlay.png", optimize=True)
    (output_dir / "scene_depth_qa_stats.json").write_text(
        json.dumps(
            {
                "shape": list(depth.shape),
                "dtype": str(depth.dtype),
                "finite_fraction": float(valid.mean()),
                "minimum": float(depth[valid].min()),
                "maximum": float(depth[valid].max()),
                "percentiles": {
                    "p01": float(np.percentile(depth[valid], 1.0)),
                    "p50": float(np.percentile(depth[valid], 50.0)),
                    "p99": float(np.percentile(depth[valid], 99.0)),
                },
                "convention": "smaller raw MoGe value is nearer",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"[scene-depth-qa] robust {low:.4f} .. {high:.4f} -> {output_dir}")


if __name__ == "__main__":
    main()
