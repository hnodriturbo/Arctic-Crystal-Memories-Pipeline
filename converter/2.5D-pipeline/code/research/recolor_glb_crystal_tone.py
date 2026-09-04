"""
File: code/research/recolor_glb_crystal_tone.py
Purpose:
 - Convert an existing vertex-coloured GLB to a contrast-preserving monochrome crystal preview.
 - Keep geometry, scene nodes and alpha unchanged while removing RGB colour distraction.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import trimesh


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--contrast", type=float, default=1.28)
    parser.add_argument("--gamma", type=float, default=0.92)
    return parser.parse_args()


def crystal_tone(colors: np.ndarray, contrast: float, gamma: float) -> np.ndarray:
    """Return RGBA grayscale while preserving the input alpha channel."""
    rgba = np.asarray(colors, dtype=np.float64)
    if rgba.ndim != 2 or rgba.shape[1] not in (3, 4):
        raise ValueError("Expected RGB or RGBA vertex colors")
    rgb = rgba[:, :3] / 255.0
    luma = rgb @ np.array([0.2126, 0.7152, 0.0722])
    tone = np.clip(0.5 + (luma - 0.5) * contrast, 0.0, 1.0)
    tone = np.power(tone, gamma)
    gray = np.rint(tone[:, None] * 255.0).astype(np.uint8)
    alpha = (
        np.rint(rgba[:, 3:4]).astype(np.uint8)
        if rgba.shape[1] == 4
        else np.full((len(rgba), 1), 255, dtype=np.uint8)
    )
    return np.column_stack((gray, gray, gray, alpha))


def main() -> None:
    args = parse_arguments()
    if args.contrast <= 0.0 or args.gamma <= 0.0:
        raise ValueError("contrast and gamma must be positive")
    source = trimesh.load(args.input, force="scene", process=False)
    geometry_stats = {}
    for name, mesh in source.geometry.items():
        original = np.asarray(mesh.visual.vertex_colors)
        converted = crystal_tone(original, args.contrast, args.gamma)
        mesh.visual.vertex_colors = converted
        geometry_stats[name] = {
            "vertices": int(len(mesh.vertices)),
            "triangles": int(len(mesh.faces)),
            "tone_min": int(converted[:, 0].min()),
            "tone_median": float(np.median(converted[:, 0])),
            "tone_max": int(converted[:, 0].max()),
        }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    source.export(args.output)
    stats = {
        "method": "perceptual vertex-color luma with bounded contrast and gamma",
        "input": str(args.input.resolve()),
        "output": str(args.output.resolve()),
        "geometry_modified": False,
        "contrast": args.contrast,
        "gamma": args.gamma,
        "geometries": geometry_stats,
    }
    args.output.with_suffix(".json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print(f"[crystal-tone] {len(geometry_stats)} geometries -> {args.output}")


if __name__ == "__main__":
    main()
