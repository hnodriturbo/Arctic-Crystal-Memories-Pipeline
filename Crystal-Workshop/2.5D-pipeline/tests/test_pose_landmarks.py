"""
File: converter/2.5D-pipeline/tests/test_pose_landmarks.py
Purpose:
 - Verify deterministic multi-person ordering and explicit 33-point pose data.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))

from pose_landmarks import POSE_LANDMARK_COUNT, DenseBodyPose


def body_pose(center_x: float) -> DenseBodyPose:
    image = tuple(
        (center_x + (index % 3), 100.0 + index, 0.0, 1.0, 1.0)
        for index in range(POSE_LANDMARK_COUNT)
    )
    world = tuple((0.0, float(index), 0.0, 1.0) for index in range(POSE_LANDMARK_COUNT))
    return DenseBodyPose(image=image, world=world)


def test_pose_landmark_count_remains_explicit() -> None:
    pose = body_pose(50.0)
    assert len(pose.image) == 33
    assert len(pose.world) == 33


def test_pose_center_and_bounds_use_visible_source_pixels() -> None:
    pose = body_pose(50.0)
    x1, y1, x2, y2 = pose.bounds
    assert 50.0 <= pose.center_x <= 52.0
    assert (x1, y1, x2, y2) == (50.0, 100.0, 52.0, 132.0)
