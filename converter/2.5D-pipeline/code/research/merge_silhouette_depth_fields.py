"""
File: code/research/merge_silhouette_depth_fields.py
Purpose:
 - Smoothly merge a registered human depth field into a scene depth field.
 - Use a signed-distance transition instead of discrete silhouette walls.
 - Preserve explicitly protected natural gaps such as an arm beside a torso.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage


def smoothstep(values: np.ndarray) -> np.ndarray:
    """Return a clamped cubic transition with zero slope at both ends."""
    values = np.clip(values, 0.0, 1.0)
    return values * values * (3.0 - 2.0 * values)


def merge_depth_fields(
    human_depth: np.ndarray,
    scene_depth: np.ndarray,
    human_mask: np.ndarray,
    *,
    inner_width_px: float = 4.0,
    outer_width_px: float = 7.0,
    protected_gap_mask: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Blend human and scene depths across one monotonic silhouette band."""
    human = np.asarray(human_depth, dtype=np.float32)
    scene = np.asarray(scene_depth, dtype=np.float32)
    mask = np.asarray(human_mask, dtype=bool)
    if human.shape != scene.shape or human.shape != mask.shape:
        raise ValueError("human depth, scene depth and mask must have identical shapes")
    if human.ndim != 2:
        raise ValueError("depth fields must be two-dimensional")
    if not mask.any():
        raise ValueError("human mask cannot be empty")
    if inner_width_px <= 0.0 or outer_width_px <= 0.0:
        raise ValueError("merge widths must be positive")

    inside_distance = ndimage.distance_transform_edt(mask)
    outside_distance, nearest_inside = ndimage.distance_transform_edt(
        ~mask,
        return_indices=True,
    )
    signed_distance = inside_distance - outside_distance
    blend_position = (signed_distance + outer_width_px) / (
        inner_width_px + outer_width_px
    )
    human_weight = smoothstep(blend_position).astype(np.float32)

    extended_human = human[tuple(nearest_inside)]
    extended_human[mask] = human[mask]
    human_valid = np.isfinite(extended_human)
    scene_valid = np.isfinite(scene)
    human_weight[~human_valid] = 0.0
    human_weight[~scene_valid & human_valid] = 1.0

    if protected_gap_mask is not None:
        protected = np.asarray(protected_gap_mask, dtype=bool)
        if protected.shape != mask.shape:
            raise ValueError("protected gap mask must match the depth field shape")
        human_weight[protected] = 0.0

    safe_human = np.where(human_valid, extended_human, scene)
    safe_scene = np.where(scene_valid, scene, safe_human)
    merged = safe_human * human_weight + safe_scene * (1.0 - human_weight)
    return merged.astype(np.float32), human_weight


def load_depth(path: Path) -> np.ndarray:
    """Load a float NPY or normalized 8/16-bit depth image."""
    if path.suffix.lower() == ".npy":
        return np.load(path).astype(np.float32)
    pixels = np.asarray(Image.open(path))
    if pixels.ndim == 3:
        pixels = pixels[..., 0]
    scale = 65535.0 if pixels.dtype == np.uint16 else 255.0
    return pixels.astype(np.float32) / scale


def load_mask(path: Path) -> np.ndarray:
    """Load a binary mask from an image or boolean-compatible NPY."""
    if path.suffix.lower() == ".npy":
        return np.load(path).astype(bool)
    return np.asarray(Image.open(path).convert("L")) >= 128


def save_preview(path: Path, values: np.ndarray) -> None:
    """Write a robustly normalized 16-bit QA image without changing stored depth units."""
    finite = values[np.isfinite(values)]
    low, high = np.percentile(finite, [1.0, 99.0])
    normalized = np.clip((values - low) / max(high - low, 1e-8), 0.0, 1.0)
    Image.fromarray(np.round(normalized * 65535.0).astype(np.uint16), mode="I;16").save(path)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Merge registered human and scene depth fields at the silhouette."
    )
    parser.add_argument("--human-depth", required=True, type=Path)
    parser.add_argument("--scene-depth", required=True, type=Path)
    parser.add_argument("--human-mask", required=True, type=Path)
    parser.add_argument("--protected-gap-mask", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--preview", type=Path)
    parser.add_argument("--weight-output", type=Path)
    parser.add_argument("--stats", type=Path)
    parser.add_argument("--inner-width-px", type=float, default=4.0)
    parser.add_argument("--outer-width-px", type=float, default=7.0)
    return parser.parse_args()


def main() -> None:
    args = parse_arguments()
    protected = load_mask(args.protected_gap_mask) if args.protected_gap_mask else None
    merged, weight = merge_depth_fields(
        load_depth(args.human_depth),
        load_depth(args.scene_depth),
        load_mask(args.human_mask),
        inner_width_px=args.inner_width_px,
        outer_width_px=args.outer_width_px,
        protected_gap_mask=protected,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    np.save(args.output, merged)
    if args.weight_output:
        args.weight_output.parent.mkdir(parents=True, exist_ok=True)
        np.save(args.weight_output, weight)
    if args.preview:
        args.preview.parent.mkdir(parents=True, exist_ok=True)
        save_preview(args.preview, merged)
    if args.stats:
        args.stats.parent.mkdir(parents=True, exist_ok=True)
        transition = (weight > 0.0) & (weight < 1.0)
        args.stats.write_text(
            json.dumps(
                {
                    "method": "signed-distance silhouette depth-field merger",
                    "inner_width_px": args.inner_width_px,
                    "outer_width_px": args.outer_width_px,
                    "transition_pixels": int(transition.sum()),
                    "protected_gap_pixels": int(protected.sum()) if protected is not None else 0,
                    "natural_gaps_preserved": protected is not None,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    print(f"[silhouette-merger] {merged.shape[1]}x{merged.shape[0]} depth field ready")


if __name__ == "__main__":
    main()
