"""
File: converter/2.5D-pipeline/tests/test_detail_refine.py
Purpose:
 - Verify normal integration recovers a known height field and that frequency
   filtering removes broad tilt without erasing useful surface structure.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))

from detail_refine import band_limited_detail, integrate_normals  # noqa: E402


class DetailRefinementTests(unittest.TestCase):
    """Small deterministic geometry tests; no model/checkpoint is loaded."""

    def test_integrates_periodic_height_field(self) -> None:
        rows = columns = 128
        y, x = np.mgrid[0:rows, 0:columns]
        height = 0.8 * np.sin(2 * np.pi * x / 32) + 0.45 * np.cos(2 * np.pi * y / 21)
        slope_y, slope_x = np.gradient(height)

        # MoGe camera-facing convention is the negative of the usual +Z
        # height-field normal: (dz/dx, dz/dy, -1).
        normals = np.stack([slope_x, slope_y, -np.ones_like(height)], axis=2)
        normals /= np.linalg.norm(normals, axis=2, keepdims=True)
        recovered = integrate_normals(normals.astype(np.float32), slope_limit=3.0)

        correlation = float(np.corrcoef(height.ravel(), recovered.ravel())[0, 1])
        self.assertGreater(correlation, 0.985)

    def test_band_filter_rejects_broad_tilt(self) -> None:
        rows = columns = 128
        y, x = np.mgrid[0:rows, 0:columns]
        tilt = x * 0.02 + y * 0.01
        wrinkle = np.sin(2 * np.pi * x / 10) * 0.2
        filtered_tilt = band_limited_detail(tilt.astype(np.float32), 1.0, 18.0)
        filtered_combined = band_limited_detail((tilt + wrinkle).astype(np.float32), 1.0, 18.0)

        interior = np.s_[24:-24, 24:-24]
        tilt_energy = float(np.std(filtered_tilt[interior]))
        detail_energy = float(np.std(filtered_combined[interior]))
        # The Gaussian difference attenuates the broad plane by more than an
        # order of magnitude while retaining the 10 px wrinkle band.
        self.assertGreater(detail_energy, tilt_energy * 8.0)


if __name__ == "__main__":
    unittest.main()
