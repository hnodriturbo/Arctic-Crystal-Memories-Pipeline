"""
File: tests/test_detect_and_prepare_icon_people.py
Purpose:
 - Verify deterministic crop and alpha fallback helpers for self-service v3 runs.
"""

import sys
from pathlib import Path

from PIL import Image

RESEARCH_DIR = Path(__file__).resolve().parents[1] / "code" / "research"
sys.path.insert(0, str(RESEARCH_DIR))

from detect_and_prepare_icon_people import alpha_fallback_box, expand_box, square_canvas  # noqa: E402


def test_expand_box_clamps_margin_to_source() -> None:
    assert expand_box((2.4, 4.2, 90.1, 98.8), (100, 100), 10) == (0, 0, 100, 100)


def test_alpha_fallback_uses_visible_subject_bounds() -> None:
    image = Image.new("RGBA", (12, 10), (0, 0, 0, 0))
    for x in range(3, 9):
        for y in range(2, 8):
            image.putpixel((x, y), (255, 255, 255, 255))
    assert alpha_fallback_box(image) == (3, 2, 9, 8)


def test_square_canvas_preserves_native_pixels() -> None:
    crop = Image.new("RGBA", (4, 8), (20, 30, 40, 255))
    canvas = square_canvas(crop)
    assert canvas.size == (8, 8)
    assert canvas.getpixel((2, 0)) == (20, 30, 40, 255)
    assert canvas.getpixel((0, 0))[3] == 0
