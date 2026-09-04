"""
File: tests/test_silhouette_depth_merger.py
Purpose:
 - Verify the monotonic body-to-scene blend and protected natural-gap behavior.
"""

import sys
from pathlib import Path

import numpy as np
import pytest

RESEARCH_DIR = Path(__file__).resolve().parents[1] / "code" / "research"
sys.path.insert(0, str(RESEARCH_DIR))

from merge_silhouette_depth_fields import merge_depth_fields  # noqa: E402


def sample_fields() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    scene = np.zeros((17, 17), dtype=np.float32)
    human = np.ones((17, 17), dtype=np.float32)
    mask = np.zeros((17, 17), dtype=bool)
    mask[4:13, 4:13] = True
    return human, scene, mask


def test_far_scene_and_human_core_keep_their_depths() -> None:
    human, scene, mask = sample_fields()
    merged, weight = merge_depth_fields(
        human,
        scene,
        mask,
        inner_width_px=2,
        outer_width_px=2,
    )
    assert merged[0, 0] == pytest.approx(0.0)
    assert merged[8, 8] == pytest.approx(1.0)
    assert weight[0, 0] == pytest.approx(0.0)
    assert weight[8, 8] == pytest.approx(1.0)


def test_transition_never_overshoots_either_depth_field() -> None:
    human, scene, mask = sample_fields()
    merged, weight = merge_depth_fields(human, scene, mask)
    assert np.all((weight >= 0.0) & (weight <= 1.0))
    assert np.all((merged >= 0.0) & (merged <= 1.0))
    assert np.any((weight > 0.0) & (weight < 1.0))


def test_protected_natural_gap_remains_scene_depth() -> None:
    human, scene, mask = sample_fields()
    protected = np.zeros_like(mask)
    protected[6:11, 8] = True
    merged, weight = merge_depth_fields(
        human,
        scene,
        mask,
        protected_gap_mask=protected,
    )
    np.testing.assert_allclose(merged[protected], scene[protected])
    np.testing.assert_allclose(weight[protected], 0.0)


def test_nonfinite_samples_fall_back_to_the_available_depth_field() -> None:
    human, scene, mask = sample_fields()
    human[8, 8] = np.nan
    scene[8, 8] = 0.25
    scene[7, 7] = np.nan
    merged, _ = merge_depth_fields(human, scene, mask)
    assert merged[8, 8] == pytest.approx(0.25)
    assert np.isfinite(merged[7, 7])


def test_rejects_mismatched_shapes_and_empty_masks() -> None:
    human, scene, mask = sample_fields()
    with pytest.raises(ValueError, match="identical shapes"):
        merge_depth_fields(human[:-1], scene, mask)
    with pytest.raises(ValueError, match="cannot be empty"):
        merge_depth_fields(human, scene, np.zeros_like(mask))
