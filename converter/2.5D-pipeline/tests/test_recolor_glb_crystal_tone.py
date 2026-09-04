"""
File: tests/test_recolor_glb_crystal_tone.py
Purpose:
 - Verify deterministic grayscale conversion without alpha loss.
"""

import sys
from pathlib import Path

import numpy as np

RESEARCH_DIR = Path(__file__).resolve().parents[1] / "code" / "research"
sys.path.insert(0, str(RESEARCH_DIR))

from recolor_glb_crystal_tone import crystal_tone  # noqa: E402


def test_crystal_tone_outputs_equal_rgb_channels_and_preserves_alpha() -> None:
    colors = np.array([[255, 0, 0, 17], [0, 255, 0, 93], [0, 0, 255, 255]], dtype=np.uint8)
    result = crystal_tone(colors, contrast=1.0, gamma=1.0)
    np.testing.assert_array_equal(result[:, 0], result[:, 1])
    np.testing.assert_array_equal(result[:, 1], result[:, 2])
    np.testing.assert_array_equal(result[:, 3], colors[:, 3])
    assert result[1, 0] > result[0, 0] > result[2, 0]
