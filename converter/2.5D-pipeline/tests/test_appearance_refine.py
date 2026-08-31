"""
File: converter/2.5D-pipeline/tests/test_appearance_refine.py
Purpose:
 - Verify that crystal appearance enhancement preserves size/masks and adds
   useful high-frequency contrast without changing physical depth.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

CODE_DIR = Path(__file__).resolve().parents[1] / "code"
sys.path.insert(0, str(CODE_DIR))

from appearance_refine import build_appearance  # noqa: E402


def test_appearance_shape_and_range() -> None:
    rows, columns = 96, 128
    x = np.linspace(0.0, 1.0, columns, dtype=np.float32)
    stripes = (np.sin(x * np.pi * 30.0) * 0.08 + 0.5)[None, :]
    rgb = np.repeat(np.repeat(stripes[..., None], rows, axis=0), 3, axis=2)
    alpha = np.ones((rows, columns), dtype=np.float32)
    _luma, detail, tone = build_appearance(rgb, alpha, 18.0, 0.7, 3.2, 0.55, 1.35, 1.8, 0.5)

    assert detail.shape == (rows, columns)
    assert tone.shape == (rows, columns)
    assert float(tone.min()) >= 0.0
    assert float(tone.max()) <= 1.0
    assert float(np.std(detail)) > 0.001


def test_transparent_pixels_stay_black() -> None:
    rgb = np.full((64, 64, 3), 0.7, dtype=np.float32)
    rgb[20:44, 20:44] = 0.25
    alpha = np.ones((64, 64), dtype=np.float32)
    alpha[:, :8] = 0.0
    _luma, _detail, tone = build_appearance(rgb, alpha, 12.0, 0.7, 2.4, 0.4, 1.0, 1.8, 0.5)

    assert np.allclose(tone[:, :8], 0.0)
