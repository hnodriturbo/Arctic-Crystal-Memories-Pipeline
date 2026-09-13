"""
File: code/research/extract_icon_normal_maps.py
Purpose:
 - Extract the exact 512x512 predicted front/back normal cells from ICON's SMPL QA grid.
 - Preserve the normal maps that precede implicit full-3D reconstruction.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


CELL_SIZE = 512
GRID_PADDING = 2
PREDICTED_NORMAL_COLUMN = 2


def cell_box(column: int, row: int) -> tuple[int, int, int, int]:
    """Return the Pillow crop box for a torchvision make_grid cell."""

    left = GRID_PADDING + column * (CELL_SIZE + GRID_PADDING)
    top = GRID_PADDING + row * (CELL_SIZE + GRID_PADDING)
    return left, top, left + CELL_SIZE, top + CELL_SIZE


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("grid", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--subject", required=True)
    args = parser.parse_args()

    grid = Image.open(args.grid).convert("RGB")
    expected_size = (2572, 1030)
    if grid.size != expected_size:
        raise ValueError(f"Expected ICON 5x2 grid {expected_size}, received {grid.size}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "normal_F": grid.crop(cell_box(PREDICTED_NORMAL_COLUMN, 0)),
        "normal_B": grid.crop(cell_box(PREDICTED_NORMAL_COLUMN, 1)),
    }

    for suffix, image in outputs.items():
        output_path = args.output_dir / f"{args.subject}_{suffix}.png"
        image.save(output_path, optimize=True)
        print(f"{suffix}: size={image.size} output={output_path}")


if __name__ == "__main__":
    main()
