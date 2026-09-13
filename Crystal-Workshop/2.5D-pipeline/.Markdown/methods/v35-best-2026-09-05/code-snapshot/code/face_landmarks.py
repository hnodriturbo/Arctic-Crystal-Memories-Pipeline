"""
File: converter/2.5D-pipeline/code/face_landmarks.py
Purpose:
 - Detect the canonical 468 MediaPipe facial landmarks for every human face.
 - Preserve the optional 10 iris landmarks separately instead of confusing
   MediaPipe's 478-point output with the 468-point face-mesh definition.
 - Write machine-readable coordinates and a visual QA overlay for the relief
   pipeline and future parametric-head fitting.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


CORE_LANDMARK_COUNT = 468
IRIS_LANDMARK_COUNT = 10
TOTAL_LANDMARK_COUNT = CORE_LANDMARK_COUNT + IRIS_LANDMARK_COUNT
DEFAULT_CHECKPOINT = (
    Path(__file__).resolve().parent.parent
    / "Models"
    / "mediapipe-face-landmarker"
    / "face_landmarker.task"
)


@dataclass(frozen=True)
class DenseFaceLandmarks:
    """Pixel-space x/y plus MediaPipe's normalized relative z for one face."""

    core: tuple[tuple[float, float, float], ...]
    iris: tuple[tuple[float, float, float], ...]

    @property
    def all_points(self) -> tuple[tuple[float, float, float], ...]:
        return self.core + self.iris

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        points = np.asarray(self.core, dtype=np.float32)
        return (
            float(points[:, 0].min()),
            float(points[:, 1].min()),
            float(points[:, 0].max()),
            float(points[:, 1].max()),
        )

    @property
    def center(self) -> tuple[float, float]:
        x1, y1, x2, y2 = self.bounds
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


def detect_dense_faces(
    image_rgb: np.ndarray,
    checkpoint: Path = DEFAULT_CHECKPOINT,
    max_faces: int = 8,
    min_confidence: float = 0.45,
) -> list[DenseFaceLandmarks]:
    """Return left-to-right MediaPipe faces with 468 core + 10 iris points."""
    if not checkpoint.is_file():
        raise FileNotFoundError(
            f"Missing MediaPipe Face Landmarker model: {checkpoint}. "
            "Download face_landmarker.task into Models/mediapipe-face-landmarker/."
        )

    try:
        import mediapipe as mp
        from mediapipe.tasks import python
        from mediapipe.tasks.python import vision
    except ImportError as error:
        raise RuntimeError(
            "Dense face landmarks require mediapipe>=0.10.30 in .venv-geometry."
        ) from error

    options = vision.FaceLandmarkerOptions(
        base_options=python.BaseOptions(model_asset_path=str(checkpoint)),
        running_mode=vision.RunningMode.IMAGE,
        num_faces=max_faces,
        min_face_detection_confidence=min_confidence,
        min_face_presence_confidence=min_confidence,
        min_tracking_confidence=min_confidence,
        output_face_blendshapes=False,
        output_facial_transformation_matrixes=False,
    )
    height, width = image_rgb.shape[:2]
    image = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(image_rgb))
    with vision.FaceLandmarker.create_from_options(options) as detector:
        result = detector.detect(image)

    faces: list[DenseFaceLandmarks] = []
    for landmarks in result.face_landmarks:
        if len(landmarks) < CORE_LANDMARK_COUNT:
            continue
        points = tuple(
            (float(point.x * width), float(point.y * height), float(point.z))
            for point in landmarks[:TOTAL_LANDMARK_COUNT]
        )
        faces.append(
            DenseFaceLandmarks(
                core=points[:CORE_LANDMARK_COUNT],
                iris=points[CORE_LANDMARK_COUNT:TOTAL_LANDMARK_COUNT],
            )
        )
    return sorted(faces, key=lambda face: face.center[0])


def remap_dense_face(
    face: DenseFaceLandmarks,
    offset_x: float,
    offset_y: float,
) -> DenseFaceLandmarks:
    """Move crop-local landmark x/y coordinates into source-image space."""

    def remap(points: tuple[tuple[float, float, float], ...]) -> tuple[tuple[float, float, float], ...]:
        return tuple((x + offset_x, y + offset_y, z) for x, y, z in points)

    return DenseFaceLandmarks(core=remap(face.core), iris=remap(face.iris))


def _expanded_square_bounds(
    box: object,
    image_width: int,
    image_height: int,
    expansion: float,
) -> tuple[int, int, int, int]:
    """Return a clamped square-ish crop around a detector or manual face box."""
    center_x = (float(box.x1) + float(box.x2)) / 2.0
    center_y = (float(box.y1) + float(box.y2)) / 2.0
    side = max(float(box.x2) - float(box.x1), float(box.y2) - float(box.y1)) * expansion
    half_side = max(2.0, side / 2.0)
    x1 = max(0, int(np.floor(center_x - half_side)))
    y1 = max(0, int(np.floor(center_y - half_side)))
    x2 = min(image_width, int(np.ceil(center_x + half_side)))
    y2 = min(image_height, int(np.ceil(center_y + half_side)))
    return x1, y1, x2, y2


def detect_dense_faces_in_boxes(
    image_rgb: np.ndarray,
    boxes: list[object],
    checkpoint: Path = DEFAULT_CHECKPOINT,
    min_confidence: float = 0.45,
    crop_expansion: float = 1.65,
) -> list[DenseFaceLandmarks]:
    """Measure one high-resolution 478-point mesh inside every known face box.

    Full-frame MediaPipe can omit a smaller face in a group photo. Detector-
    guided crops preserve every known face and give each mesh more source
    pixels. Results remain in exactly the same order as ``boxes``.
    """
    image_height, image_width = image_rgb.shape[:2]
    matches: list[DenseFaceLandmarks] = []
    attempts = (
        (crop_expansion, min_confidence),
        (max(2.0, crop_expansion * 1.2), max(0.25, min_confidence * 0.75)),
    )

    for box_index, box in enumerate(boxes, start=1):
        match: DenseFaceLandmarks | None = None
        for expansion, confidence in attempts:
            x1, y1, x2, y2 = _expanded_square_bounds(
                box,
                image_width,
                image_height,
                expansion,
            )
            crop_rgb = image_rgb[y1:y2, x1:x2]
            if crop_rgb.size == 0:
                continue
            crop_faces = detect_dense_faces(
                crop_rgb,
                checkpoint=checkpoint,
                max_faces=1,
                min_confidence=confidence,
            )
            if crop_faces:
                match = remap_dense_face(crop_faces[0], x1, y1)
                break

        if match is None:
            raise ValueError(
                f"MediaPipe could not measure dense landmarks for face box {box_index}/{len(boxes)}."
            )
        matches.append(match)

    return matches


def match_landmarks_to_boxes(boxes: list[object], dense_faces: list[DenseFaceLandmarks]) -> list[DenseFaceLandmarks]:
    """Greedily associate dense landmarks with face boxes by normalized centre distance."""
    if len(boxes) != len(dense_faces):
        raise ValueError(f"Face boxes total {len(boxes)}, dense landmark faces total {len(dense_faces)}.")

    remaining = list(dense_faces)
    matches: list[DenseFaceLandmarks] = []
    for box in boxes:
        box_center_x = (float(box.x1) + float(box.x2)) / 2.0
        box_center_y = (float(box.y1) + float(box.y2)) / 2.0
        box_scale = max(1.0, float(box.x2) - float(box.x1), float(box.y2) - float(box.y1))
        best = min(
            remaining,
            key=lambda face: (
                ((face.center[0] - box_center_x) / box_scale) ** 2
                + ((face.center[1] - box_center_y) / box_scale) ** 2
            ),
        )
        matches.append(best)
        remaining.remove(best)
    return matches


def save_landmark_overlay(
    image_rgb: np.ndarray,
    faces: list[DenseFaceLandmarks],
    output: Path,
) -> None:
    """Draw 468 core points in cyan and the optional iris points in orange."""
    canvas = Image.fromarray(image_rgb).convert("RGB")
    drawing = ImageDraw.Draw(canvas)
    for face_index, face in enumerate(faces, start=1):
        for x, y, _z in face.core:
            drawing.ellipse((x - 1, y - 1, x + 1, y + 1), fill=(0, 235, 255))
        for x, y, _z in face.iris:
            drawing.ellipse((x - 2, y - 2, x + 2, y + 2), fill=(255, 145, 0))
        x1, y1, x2, y2 = face.bounds
        drawing.rectangle((x1, y1, x2, y2), outline=(255, 255, 255), width=2)
        drawing.text((x1 + 3, max(0, y1 - 18)), f"face {face_index}: 468 + 10 iris", fill=(255, 255, 255))
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output)


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract 468 core facial landmarks per face.")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output-json", required=True, type=Path)
    parser.add_argument("--output-overlay", required=True, type=Path)
    parser.add_argument("--model", type=Path, default=DEFAULT_CHECKPOINT)
    parser.add_argument("--max-faces", type=int, default=8)
    parser.add_argument("--min-confidence", type=float, default=0.45)
    parser.add_argument("--known-face-count", type=int, default=0)
    args = parser.parse_args()

    with Image.open(args.input) as source:
        source.load()
        image_rgb = np.asarray(source.convert("RGB"))
    faces = detect_dense_faces(image_rgb, args.model, args.max_faces, args.min_confidence)
    if args.known_face_count and len(faces) != args.known_face_count:
        raise SystemExit(f"Expected {args.known_face_count} face(s), detected {len(faces)}.")

    payload = {
        "input": str(args.input.resolve()),
        "model": str(args.model.resolve()),
        "face_count": len(faces),
        "core_landmarks_per_face": CORE_LANDMARK_COUNT,
        "iris_landmarks_per_face": IRIS_LANDMARK_COUNT,
        "coordinate_system": "x/y source pixels; z MediaPipe normalized relative depth",
        "faces": [
            {
                "index": index,
                "bounds": list(face.bounds),
                "core_468": [list(point) for point in face.core],
                "iris_10": [list(point) for point in face.iris],
            }
            for index, face in enumerate(faces, start=1)
        ],
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    save_landmark_overlay(image_rgb, faces, args.output_overlay)
    print(f"FACE_LANDMARKS_OK faces={len(faces)} core={CORE_LANDMARK_COUNT} iris={IRIS_LANDMARK_COUNT}")
    print(args.output_json)
    print(args.output_overlay)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
