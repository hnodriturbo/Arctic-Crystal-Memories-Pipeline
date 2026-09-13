"""
File: converter/2.5D-pipeline/tests/test_face_landmarks.py
Purpose:
 - Verify the 468/10 landmark split and deterministic association with face boxes.
"""

from dataclasses import dataclass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))

from face_landmarks import (
    CORE_LANDMARK_COUNT,
    IRIS_LANDMARK_COUNT,
    DenseFaceLandmarks,
    match_landmarks_to_boxes,
    remap_dense_face,
)


@dataclass(frozen=True)
class Box:
    x1: float
    y1: float
    x2: float
    y2: float


def dense_face(center_x: float) -> DenseFaceLandmarks:
    core = tuple((center_x + (index % 3), 100.0 + (index % 5), 0.0) for index in range(CORE_LANDMARK_COUNT))
    iris = tuple((center_x, 100.0, 0.0) for _ in range(IRIS_LANDMARK_COUNT))
    return DenseFaceLandmarks(core=core, iris=iris)


def test_landmark_counts_remain_explicit() -> None:
    face = dense_face(50.0)
    assert len(face.core) == 468
    assert len(face.iris) == 10
    assert len(face.all_points) == 478


def test_landmarks_match_boxes_by_face_position() -> None:
    left = dense_face(50.0)
    right = dense_face(250.0)
    boxes = [Box(220, 50, 300, 150), Box(20, 50, 100, 150)]
    matched = match_landmarks_to_boxes(boxes, [left, right])
    assert matched == [right, left]


def test_crop_landmarks_are_remapped_to_source_pixels() -> None:
    face = dense_face(50.0)
    remapped = remap_dense_face(face, 100.0, 200.0)
    assert remapped.core[0] == (150.0, 300.0, 0.0)
    assert remapped.iris[0] == (150.0, 300.0, 0.0)
