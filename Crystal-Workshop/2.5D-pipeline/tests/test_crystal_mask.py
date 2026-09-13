"""
File: converter/2.5D-pipeline/tests/test_crystal_mask.py
Purpose:
 - Verify that border-connected print-empty black is removed without deleting
   enclosed black subject detail.
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))

from crystal_mask import build_crystal_mask


def test_top_black_padding_is_removed_but_internal_black_is_kept() -> None:
    tone = np.full((12, 12), 180, dtype=np.uint8)
    tone[:3, :] = 0
    tone[7:9, 5:7] = 0
    alpha = np.full_like(tone, 255)

    mask, removed = build_crystal_mask(tone, alpha, threshold=8, edges=("top",))

    assert np.all(mask[:3, :] == 0)
    assert np.all(removed[:3, :])
    assert np.all(mask[7:9, 5:7] == 255)
    assert not np.any(removed[7:9, 5:7])


def test_existing_transparency_is_always_preserved() -> None:
    tone = np.full((6, 6), 180, dtype=np.uint8)
    alpha = np.full_like(tone, 255)
    alpha[:, 0] = 0

    mask, _removed = build_crystal_mask(tone, alpha, threshold=8, edges=("top",))

    assert np.all(mask[:, 0] == 0)
    assert np.all(mask[:, 1:] == 255)
