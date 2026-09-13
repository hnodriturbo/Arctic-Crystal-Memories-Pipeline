"""
File: converter/2.5D-pipeline/code/pose_landmarks.py
Purpose:
 - Detect 33 MediaPipe body landmarks for every visible person in a photo.
 - Preserve image-space and world-space coordinates for source-aligned 2.5D
   body refinement without creating a hidden or 360-degree human mesh.
 - Write a machine-readable manifest and a visual QA overlay before any depth
   values are allowed to change.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


POSE_LANDMARK_COUNT = 33
DEFAULT_CHECKPOINT = (
    Path(__file__).resolve().parent.parent
    / "Models"
    / "mediapipe-pose-landmarker"
    / "pose_landmarker_heavy.task"
)

# MediaPipe Pose landmark connections used only for visual QA.
POSE_CONNECTIONS = (
    (0, 1), (1, 2), (2, 3), (3, 7),
    (0, 4), (4, 5), (5, 6), (6, 8),
    (9, 10),
    (11, 12), (11, 13), (13, 15), (15, 17), (15, 19), (15, 21),
    (12, 14), (14, 16), (16, 18), (16, 20), (16, 22),
    (11, 23), (12, 24), (23, 24),
    (23, 25), (25, 27), (27, 29), (29, 31),
    (24, 26), (26, 28), (28, 30), (30, 32),
)


@dataclass(frozen=True)
class DenseBodyPose:
    """One source-aligned body pose with 33 image and world landmarks."""

    image: tuple[tuple[float, float, float, float, float], ...]
    world: tuple[tuple[float, float, float, float], ...]

    @property
    def center_x(self) -> float:
        visible = [point[0] for point in self.image if point[3] >= 0.2]
        if not visible:
            visible = [point[0] for point in self.image]
        return float(np.median(visible))

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        visible = np.asarray(
            [(point[0], point[1]) for point in self.image if point[3] >= 0.2],
            dtype=np.float32,
        )
        if visible.size == 0:
            visible = np.asarray([(point[0], point[1]) for point in self.image], dtype=np.float32)
        return (
            float(visible[:, 0].min()),
            float(visible[:, 1].min()),
            float(visible[:, 0].max()),
            float(visible[:, 1].max()),
        )


def detect_body_poses(
    image_rgb: np.ndarray,
    checkpoint: Path = DEFAULT_CHECKPOINT,
    max_poses: int = 8,
    min_confidence: float = 0.2,
) -> list[DenseBodyPose]:
    """Return left-to-right 33-point body poses in source pixel coordinates."""
    if not checkpoint.is_file():
        raise FileNotFoundError(
            f"Missing MediaPipe Pose Landmarker model: {checkpoint}. "
            "Download pose_landmarker_heavy.task into Models/mediapipe-pose-landmarker/."
        )

    try:
        import mediapipe as mp
        from mediapipe.tasks import python
        from mediapipe.tasks.python import vision
    except ImportError as error:
        raise RuntimeError(
            "Body pose landmarks require mediapipe>=0.10.30 in .venv-geometry."
        ) from error

    options = vision.PoseLandmarkerOptions(
        base_options=python.BaseOptions(model_asset_path=str(checkpoint)),
        running_mode=vision.RunningMode.IMAGE,
        num_poses=max_poses,
        min_pose_detection_confidence=min_confidence,
        min_pose_presence_confidence=min_confidence,
        min_tracking_confidence=min_confidence,
        # The current Windows MediaPipe build aborts in native code while
        # materialising IMAGE-mode segmentation masks. Landmarks remain stable;
        # body regions are therefore constructed from measured limb capsules.
        output_segmentation_masks=False,
    )
    height, width = image_rgb.shape[:2]
    image = mp.Image(
        image_format=mp.ImageFormat.SRGB,
        data=np.ascontiguousarray(image_rgb[:, :, :3], dtype=np.uint8),
    )
    with vision.PoseLandmarker.create_from_options(options) as detector:
        result = detector.detect(image)

    poses: list[DenseBodyPose] = []
    for image_landmarks, world_landmarks in zip(
        result.pose_landmarks,
        result.pose_world_landmarks,
        strict=True,
    ):
        if len(image_landmarks) != POSE_LANDMARK_COUNT:
            continue
        image_points = tuple(
            (
                float(point.x * width),
                float(point.y * height),
                float(point.z),
                float(point.visibility),
                float(point.presence),
            )
            for point in image_landmarks
        )
        world_points = tuple(
            (
                float(point.x),
                float(point.y),
                float(point.z),
                float(point.visibility),
            )
            for point in world_landmarks
        )
        poses.append(DenseBodyPose(image=image_points, world=world_points))
    return sorted(poses, key=lambda pose: pose.center_x)


def save_pose_overlay(
    image_rgb: np.ndarray,
    poses: list[DenseBodyPose],
    output: Path,
) -> None:
    """Draw source-aligned pose skeletons and per-person bounds for QA."""
    canvas = Image.fromarray(image_rgb).convert("RGB")
    drawing = ImageDraw.Draw(canvas)
    palette = ((0, 235, 255), (255, 145, 0), (123, 255, 88), (255, 87, 176))

    for pose_index, pose in enumerate(poses, start=1):
        colour = palette[(pose_index - 1) % len(palette)]
        for start_index, end_index in POSE_CONNECTIONS:
            start = pose.image[start_index]
            end = pose.image[end_index]
            if min(start[3], end[3], start[4], end[4]) < 0.2:
                continue
            drawing.line((start[0], start[1], end[0], end[1]), fill=colour, width=3)
        for x, y, _z, visibility, presence in pose.image:
            if min(visibility, presence) < 0.2:
                continue
            drawing.ellipse((x - 3, y - 3, x + 3, y + 3), fill=colour, outline=(15, 15, 15))
        x1, y1, x2, y2 = pose.bounds
        drawing.rectangle((x1, y1, x2, y2), outline=colour, width=2)
        drawing.text(
            (x1 + 4, max(0, y1 - 18)),
            f"person {pose_index}: 33 body landmarks",
            fill=colour,
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract 33 source-aligned body landmarks per visible person."
    )
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output-json", required=True, type=Path)
    parser.add_argument("--output-overlay", required=True, type=Path)
    parser.add_argument("--model", type=Path, default=DEFAULT_CHECKPOINT)
    parser.add_argument("--max-poses", type=int, default=8)
    parser.add_argument("--min-confidence", type=float, default=0.2)
    parser.add_argument("--known-person-count", type=int, default=0)
    args = parser.parse_args()

    with Image.open(args.input) as source:
        source.load()
        image_rgb = np.asarray(source.convert("RGB"))
    poses = detect_body_poses(
        image_rgb,
        checkpoint=args.model,
        max_poses=args.max_poses,
        min_confidence=args.min_confidence,
    )
    if args.known_person_count and len(poses) != args.known_person_count:
        raise SystemExit(
            f"Expected {args.known_person_count} person(s), detected {len(poses)}."
        )

    payload = {
        "input": str(args.input.resolve()),
        "model": str(args.model.resolve()),
        "person_count": len(poses),
        "landmarks_per_person": POSE_LANDMARK_COUNT,
        "image_coordinate_system": (
            "x/y source pixels; z MediaPipe normalized relative depth; "
            "visibility/presence confidence"
        ),
        "world_coordinate_system": "MediaPipe metric-like pose world coordinates in metres",
        "purpose": "source-aligned 2.5D body prior; not a 360-degree body reconstruction",
        "people": [
            {
                "index": index,
                "bounds": list(pose.bounds),
                "image_33": [list(point) for point in pose.image],
                "world_33": [list(point) for point in pose.world],
            }
            for index, pose in enumerate(poses, start=1)
        ],
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    save_pose_overlay(image_rgb, poses, args.output_overlay)
    print(f"POSE_LANDMARKS_OK people={len(poses)} landmarks={POSE_LANDMARK_COUNT}")
    print(args.output_json)
    print(args.output_overlay)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
