"""
File: converter/2.5D-pipeline/tests/test_head_depth_headroom.py
Purpose:
 - Verify that anatomy fitting receives free depth on both sides of the source.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

import numpy as np


MODULE_PATH = Path(__file__).resolve().parents[1] / "code" / "gnm_head_refine.py"
SPEC = importlib.util.spec_from_file_location("gnm_head_refine", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class HeadDepthHeadroomTests(unittest.TestCase):
    def test_centres_full_depth_range_inside_reserved_envelope(self) -> None:
        depth = np.asarray([[0.0, 0.5, 1.0]], dtype=np.float32)
        centred = MODULE.centre_depth_with_headroom(depth, 0.12, 0.12)
        np.testing.assert_allclose(centred, [[0.12, 0.5, 0.88]], atol=1e-6)

    def test_rejects_headroom_without_an_active_depth_span(self) -> None:
        with self.assertRaises(ValueError):
            MODULE.centre_depth_with_headroom(np.zeros((1, 1)), 0.5, 0.5)


if __name__ == "__main__":
    unittest.main()
