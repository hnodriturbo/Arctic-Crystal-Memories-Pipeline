"""
File: code/research/prepare_icon_person_inputs.py
Purpose:
 - Create deterministic, aspect-ratio-preserving person canvases for official ICON.
 - Keep detector boxes and padding reproducible for multi-person source images.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


def parse_subject(value: str) -> tuple[str, tuple[int, int, int, int]]:
    """Parse NAME:X1,Y1,X2,Y2 into a named integer bounding box."""

    try:
        name, raw_box = value.split(":", maxsplit=1)
        box = tuple(int(round(float(part))) for part in raw_box.split(","))
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "Subject must use NAME:X1,Y1,X2,Y2, for example man:3,2,585,1175"
        ) from error

    if not name or len(box) != 4:
        raise argparse.ArgumentTypeError("Subject must use NAME:X1,Y1,X2,Y2")

    x1, y1, x2, y2 = box
    if x2 <= x1 or y2 <= y1:
        raise argparse.ArgumentTypeError("Subject bounding box must have positive width and height")

    return name, (x1, y1, x2, y2)


def clamp_box(
    box: tuple[int, int, int, int],
    image_size: tuple[int, int],
    margin: int,
) -> tuple[int, int, int, int]:
    """Expand a detector box by a fixed margin without leaving the source image."""

    x1, y1, x2, y2 = box
    width, height = image_size
    return (
        max(0, x1 - margin),
        max(0, y1 - margin),
        min(width, x2 + margin),
        min(height, y2 + margin),
    )


def place_on_square_canvas(crop: Image.Image) -> Image.Image:
    """Center a crop on a transparent square without resizing its pixels."""

    side = max(crop.width, crop.height)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    offset = ((side - crop.width) // 2, (side - crop.height) // 2)
    canvas.alpha_composite(crop, dest=offset)
    return canvas


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument(
        "--subject",
        action="append",
        required=True,
        type=parse_subject,
        help="Repeatable NAME:X1,Y1,X2,Y2 detector box.",
    )
    parser.add_argument("--margin", type=int, default=64)
    args = parser.parse_args()

    source = Image.open(args.source).convert("RGBA")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    for name, detector_box in args.subject:
        crop_box = clamp_box(detector_box, source.size, args.margin)
        crop = source.crop(crop_box)
        canvas = place_on_square_canvas(crop)
        output_path = args.output_dir / f"{name}.png"
        canvas.save(output_path, optimize=True)
        print(
            f"{name}: detector_box={detector_box} crop_box={crop_box} "
            f"canvas={canvas.size} output={output_path}"
        )


if __name__ == "__main__":
    main()
