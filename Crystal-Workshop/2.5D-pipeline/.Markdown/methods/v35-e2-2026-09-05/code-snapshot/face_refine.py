"""
File: converter/2.5D-pipeline/code/face_refine.py
Purpose:
 - Detect every human face, or accept face boxes supplied by an upstream tool.
 - Re-run MoGe-2 ViT-L 9/9 on each enlarged face crop so the face receives far
   more effective model resolution than it receives in the complete scene.
 - Align each local prediction to the global depth and feather its anatomical
   shape/detail back into one refined 16-bit depth map.

This is the mandatory native 2.5D stage between depth_map.py and
depth_to_mesh.py whenever faces exist. It is deliberately outside Blender:
Blender receives a completed relief, plus provenance proving whether face
refinement ran.

Output convention remains unchanged: 16-bit PNG, BRIGHT = NEAR = raised.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))

from depth_map import MOGE_MODELS  # noqa: E402
from face_landmarks import (  # noqa: E402
    CORE_LANDMARK_COUNT,
    DEFAULT_CHECKPOINT as DENSE_LANDMARK_CHECKPOINT,
    DenseFaceLandmarks,
    detect_dense_faces_in_boxes,
    save_landmark_overlay,
)
from utils import fail, prepare_output, report, torch_device, use_local_model_cache  # noqa: E402


YUNET_CHECKPOINT = (
    Path(__file__).resolve().parent.parent
    / "Models"
    / "opencv-face-detector-yunet"
    / "face_detection_yunet_2023mar.onnx"
)


@dataclass(frozen=True)
class FaceBox:
    """One face rectangle in source-image pixels, with optional detector landmarks."""

    x1: int
    y1: int
    x2: int
    y2: int
    confidence: float
    landmarks: tuple[tuple[float, float], ...] = ()
    source: str = "auto"

    @property
    def width(self) -> int:
        return self.x2 - self.x1

    @property
    def height(self) -> int:
        return self.y2 - self.y1


def read_depth(path: Path, size: tuple[int, int]) -> np.ndarray:
    """Read a pipeline 16-bit depth map without Pillow's mode-conversion loss."""
    with Image.open(path) as image:
        image.load()
        if image.size != size:
            fail(f"Depth size {image.size} does not match photograph size {size}.")
        return np.asarray(image, dtype=np.float32) / 65535.0


def parse_face_box(value: str, width: int, height: int) -> FaceBox:
    """Parse x1,y1,x2,y2 in pixels, or normalized 0..1 coordinates."""
    try:
        coordinates = [float(item.strip()) for item in value.split(",")]
    except ValueError:
        fail(f"Invalid --face-box '{value}'. Expected x1,y1,x2,y2.")
    if len(coordinates) != 4:
        fail(f"Invalid --face-box '{value}'. Expected exactly four numbers.")
    if all(0.0 <= item <= 1.0 for item in coordinates):
        coordinates = [
            coordinates[0] * width,
            coordinates[1] * height,
            coordinates[2] * width,
            coordinates[3] * height,
        ]
    x1, y1, x2, y2 = (int(round(item)) for item in coordinates)
    x1, x2 = sorted((max(0, x1), min(width, x2)))
    y1, y2 = sorted((max(0, y1), min(height, y2)))
    if x2 - x1 < 16 or y2 - y1 < 16:
        fail(f"Face box '{value}' is empty or too small after clipping.")
    return FaceBox(x1, y1, x2, y2, 1.0, source="manual")


def detect_faces(image_rgb: np.ndarray, checkpoint: Path, score_threshold: float) -> list[FaceBox]:
    """Detect multiple faces with OpenCV YuNet and retain its five landmarks."""
    if not checkpoint.is_file():
        fail(
            f"Missing YuNet face detector: {checkpoint}. "
            "Run: python code/download_models.py --asset opencv-face-detector-yunet"
        )
    height, width = image_rgb.shape[:2]
    detector = cv2.FaceDetectorYN.create(
        str(checkpoint),
        "",
        (width, height),
        score_threshold,
        0.3,
        5000,
    )
    _status, detections = detector.detect(cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR))
    if detections is None:
        return []

    faces: list[FaceBox] = []
    for row in detections:
        x, y, box_width, box_height = row[:4]
        x1 = max(0, int(np.floor(x)))
        y1 = max(0, int(np.floor(y)))
        x2 = min(width, int(np.ceil(x + box_width)))
        y2 = min(height, int(np.ceil(y + box_height)))
        if x2 - x1 < 16 or y2 - y1 < 16:
            continue
        landmarks = tuple((float(row[index]), float(row[index + 1])) for index in range(4, 14, 2))
        faces.append(FaceBox(x1, y1, x2, y2, float(row[14]), landmarks, "yunet"))
    return sorted(faces, key=lambda face: (face.x1, face.y1))


def expanded_square(face: FaceBox, width: int, height: int, expansion: float) -> tuple[int, int, int, int]:
    """Enlarge a face into a square crop that includes brow, jaw, ears and some hair."""
    center_x = (face.x1 + face.x2) / 2.0
    center_y = (face.y1 + face.y2) / 2.0
    side = max(face.width, face.height) * (1.0 + 2.0 * expansion)
    x1 = max(0, int(np.floor(center_x - side / 2.0)))
    y1 = max(0, int(np.floor(center_y - side / 2.0)))
    x2 = min(width, int(np.ceil(center_x + side / 2.0)))
    y2 = min(height, int(np.ceil(center_y + side / 2.0)))
    return x1, y1, x2, y2


def robust_normalise(values: np.ndarray, clip_percent: float = 1.0) -> np.ndarray:
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        raise RuntimeError("Face model returned no finite depth")
    low, high = np.percentile(finite, [clip_percent, 100.0 - clip_percent])
    if high - low < 1e-6:
        raise RuntimeError("Face model returned a flat depth patch")
    return np.clip((values - low) / (high - low), 0.0, 1.0)


class MoGeFaceBackend:
    """Load one MoGe checkpoint once and reuse it for every face in the image."""

    def __init__(self, model_size: str, device: str, resolution_level: int):
        import torch

        try:
            from moge.model.v2 import MoGeModel
        except ImportError:
            fail(
                "MoGe-2 face refinement requires Models/runtimes/.venv-geometry. "
                "Run face_refine.py with that environment's python.exe."
            )
        checkpoint = MOGE_MODELS[model_size]
        if not checkpoint.is_file():
            fail(f"Missing MoGe-2 checkpoint: {checkpoint}. Run download_models.py --baseline")
        report(f"[face] loading MoGe-2 {model_size}, resolution {resolution_level}/9 on {device}")
        self.torch = torch
        self.device = device
        self.resolution_level = resolution_level
        self.model = MoGeModel.from_pretrained(checkpoint).to(device).eval()
        self.checkpoint = checkpoint

    def infer_near_depth(self, crop_rgb: np.ndarray) -> np.ndarray:
        tensor = self.torch.from_numpy(crop_rgb.astype(np.float32) / 255.0).permute(2, 0, 1)
        tensor = tensor.to(self.device)
        output = self.model.infer(
            tensor,
            resolution_level=self.resolution_level,
            apply_mask=False,
            use_fp16=self.device == "cuda",
        )
        metric_depth = output["depth"].float().cpu().numpy().squeeze()
        # MoGe returns metric/true depth: low value is near. The pipeline uses
        # the opposite convention so nose/cheeks become raised in the relief.
        return 1.0 - robust_normalise(metric_depth)


def ellipse_weight(face: FaceBox, crop: tuple[int, int, int, int], feather: float) -> np.ndarray:
    """Soft anatomical oval: full weight centrally, zero outside the face/head edge."""
    crop_x1, crop_y1, crop_x2, crop_y2 = crop
    rows, columns = np.mgrid[crop_y1:crop_y2, crop_x1:crop_x2]
    center_x = (face.x1 + face.x2) / 2.0
    center_y = (face.y1 + face.y2) / 2.0 + face.height * 0.03
    radius_x = max(1.0, face.width * 0.64)
    radius_y = max(1.0, face.height * 0.76)
    radial = np.sqrt(((columns - center_x) / radius_x) ** 2 + ((rows - center_y) / radius_y) ** 2)
    inner = max(0.05, 1.0 - feather)
    transition = np.clip((1.0 - radial) / max(1e-6, 1.0 - inner), 0.0, 1.0)
    return transition * transition * (3.0 - 2.0 * transition)


def landmark_weight(
    face: FaceBox,
    dense: DenseFaceLandmarks,
    crop: tuple[int, int, int, int],
    feather: float,
) -> np.ndarray:
    """Constrain refinement to the measured face silhouette instead of a generic oval."""
    crop_x1, crop_y1, crop_x2, crop_y2 = crop
    mask = np.zeros((crop_y2 - crop_y1, crop_x2 - crop_x1), dtype=np.uint8)
    points = np.asarray(
        [(x - crop_x1, y - crop_y1) for x, y, _z in dense.core],
        dtype=np.float32,
    )
    hull = cv2.convexHull(np.rint(points).astype(np.int32))
    cv2.fillConvexPoly(mask, hull, 255)

    # A small expansion includes the anatomical boundary without bleeding into
    # neighbouring faces or background. The Gaussian edge is the blend zone.
    dilation = max(3, int(round(min(face.width, face.height) * 0.035)))
    if dilation % 2 == 0:
        dilation += 1
    mask = cv2.dilate(mask, np.ones((dilation, dilation), np.uint8))
    sigma = max(1.0, min(face.width, face.height) * feather * 0.12)
    measured = cv2.GaussianBlur(mask.astype(np.float32) / 255.0, (0, 0), sigmaX=sigma, sigmaY=sigma)
    measured /= max(1e-6, float(measured.max()))
    return np.minimum(measured, ellipse_weight(face, crop, feather)).astype(np.float32)


def align_local_depth(local: np.ndarray, global_patch: np.ndarray, weight: np.ndarray) -> tuple[np.ndarray, float, float]:
    """Fit local relative depth to the global map on a soft ring near the face edge."""
    ring = (weight > 0.03) & (weight < 0.45)
    if ring.sum() < 64:
        ring = weight > 0.03
    design = np.column_stack([local[ring], np.ones(int(ring.sum()), dtype=np.float32)])
    target = global_patch[ring]
    slope, offset = np.linalg.lstsq(design, target, rcond=None)[0]
    slope = float(np.clip(slope, 0.15, 4.0))
    offset = float(np.median(target - slope * local[ring]))
    return np.clip(local * slope + offset, 0.0, 1.0), slope, offset


def refinement_delta(
    local_aligned: np.ndarray,
    global_patch: np.ndarray,
    detail_sigma: float,
    shape_mix: float,
    max_delta: float,
) -> np.ndarray:
    """Keep global scene ordering while borrowing facial shape and high-frequency anatomy."""
    sigma = max(0.5, detail_sigma)
    local_blur = cv2.GaussianBlur(local_aligned, (0, 0), sigmaX=sigma, sigmaY=sigma)
    global_blur = cv2.GaussianBlur(global_patch, (0, 0), sigmaX=sigma, sigmaY=sigma)
    shape = local_aligned - global_patch
    detail = (local_aligned - local_blur) - (global_patch - global_blur)
    delta = shape_mix * shape + (1.0 - shape_mix) * detail
    return np.clip(delta, -max_delta, max_delta)


def save_previews(
    aux_output: Path,
    image_rgb: np.ndarray,
    before: np.ndarray,
    after: np.ndarray,
    faces: list[FaceBox],
    dense_faces: list[DenseFaceLandmarks] | None = None,
) -> None:
    aux_output.mkdir(parents=True, exist_ok=True)
    detection = Image.fromarray(image_rgb).convert("RGB")
    drawing = ImageDraw.Draw(detection)
    for index, face in enumerate(faces, start=1):
        drawing.rectangle((face.x1, face.y1, face.x2, face.y2), outline=(255, 145, 0), width=3)
        drawing.text((face.x1 + 3, max(0, face.y1 - 18)), f"face {index} {face.confidence:.2f}", fill=(255, 145, 0))
        for x, y in face.landmarks:
            drawing.ellipse((x - 2, y - 2, x + 2, y + 2), fill=(0, 255, 255))
    detection.save(aux_output / "faces-detected.png")
    if dense_faces:
        save_landmark_overlay(image_rgb, dense_faces, aux_output / "faces-468-landmarks.png")

    before_image = (np.clip(before, 0, 1) * 255).astype(np.uint8)
    after_image = (np.clip(after, 0, 1) * 255).astype(np.uint8)
    difference = np.clip((after - before) / 0.2, -1.0, 1.0)
    heat = np.zeros((*difference.shape, 3), dtype=np.uint8)
    heat[..., 0] = (np.clip(difference, 0, 1) * 255).astype(np.uint8)
    heat[..., 2] = (np.clip(-difference, 0, 1) * 255).astype(np.uint8)
    heat[..., 1] = (255 - np.maximum(heat[..., 0], heat[..., 2])).astype(np.uint8) // 4

    panel = np.concatenate(
        [
            np.repeat(before_image[..., None], 3, axis=2),
            np.repeat(after_image[..., None], 3, axis=2),
            heat,
        ],
        axis=1,
    )
    Image.fromarray(panel, mode="RGB").save(aux_output / "before-after-difference.png")


def main() -> int:
    parser = argparse.ArgumentParser(description="Detect and refine facial depth before relief meshing.")
    parser.add_argument("--input", required=True, type=Path, help="Original RGB/RGBA photograph.")
    parser.add_argument("--depth", required=True, type=Path, help="Global 16-bit bright=near depth map.")
    parser.add_argument("--output", required=True, type=Path, help="Refined 16-bit bright=near depth map.")
    parser.add_argument("--aux-output", type=Path, help="Preview and QA folder.")
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    parser.add_argument("--moge-model", choices=sorted(MOGE_MODELS), default="vitl")
    parser.add_argument("--moge-resolution-level", type=int, choices=range(10), default=9)
    parser.add_argument("--detector-model", type=Path, default=YUNET_CHECKPOINT)
    parser.add_argument("--score-threshold", type=float, default=0.65)
    parser.add_argument("--dense-landmark-model", type=Path, default=DENSE_LANDMARK_CHECKPOINT)
    parser.add_argument("--dense-landmark-confidence", type=float, default=0.45)
    parser.add_argument(
        "--face-box",
        action="append",
        default=[],
        help="Known x1,y1,x2,y2 face box in pixels or normalized 0..1. Repeatable; overrides auto detection.",
    )
    parser.add_argument(
        "--known-face-count",
        type=int,
        default=0,
        help="Fail instead of silently continuing if exactly this many faces are not available.",
    )
    parser.add_argument("--crop-expansion", type=float, default=0.35)
    parser.add_argument("--feather", type=float, default=0.30)
    parser.add_argument("--strength", type=float, default=0.85)
    parser.add_argument("--shape-mix", type=float, default=0.45)
    parser.add_argument("--max-delta", type=float, default=0.18)
    args = parser.parse_args()

    if args.known_face_count < 0:
        fail("--known-face-count cannot be negative.")
    if not 0.0 <= args.crop_expansion <= 1.5:
        fail("--crop-expansion must be between 0 and 1.5.")
    if not 0.05 <= args.feather <= 0.95:
        fail("--feather must be between 0.05 and 0.95.")
    if not 0.0 <= args.strength <= 1.5:
        fail("--strength must be between 0 and 1.5.")
    if not 0.0 <= args.shape_mix <= 1.0:
        fail("--shape-mix must be between 0 and 1.")
    if not 0.01 <= args.max_delta <= 0.5:
        fail("--max-delta must be between 0.01 and 0.5.")

    use_local_model_cache()
    device = torch_device(args.device)
    with Image.open(args.input) as source:
        source.load()
        image_rgb = np.asarray(source.convert("RGB"))
    height, width = image_rgb.shape[:2]
    global_depth = read_depth(args.depth, (width, height))

    if args.face_box:
        faces = [parse_face_box(value, width, height) for value in args.face_box]
        report(f"[face] using {len(faces)} known face box(es)")
    else:
        faces = detect_faces(image_rgb, args.detector_model, args.score_threshold)
        report(f"[face] YuNet detected {len(faces)} face(s)")

    if args.known_face_count and len(faces) != args.known_face_count:
        fail(f"Expected {args.known_face_count} face(s), but available face boxes total {len(faces)}.")

    aux_output = args.aux_output or args.output.parent / "face-refinement"
    if not faces:
        prepare_output(args.output)
        Image.fromarray((global_depth * 65535).astype(np.uint16)).save(args.output)
        metadata = {
            "face_count": 0,
            "face_refinement_required": False,
            "face_refinement_complete": True,
            "backend": None,
            "output": str(args.output),
        }
        prepare_output(args.output.with_suffix(".json"))
        args.output.with_suffix(".json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        save_previews(aux_output, image_rgb, global_depth, global_depth, [])
        report("[face] no faces found; wrote unchanged depth with explicit no-face provenance")
        return 0

    try:
        dense_matches = detect_dense_faces_in_boxes(
            image_rgb,
            faces,
            checkpoint=args.dense_landmark_model,
            min_confidence=args.dense_landmark_confidence,
        )
    except ValueError as error:
        fail(str(error))
    report(
        f"[face] MediaPipe measured {CORE_LANDMARK_COUNT} core landmarks on "
        "a high-resolution crop for each face"
    )

    backend = MoGeFaceBackend(args.moge_model, device, args.moge_resolution_level)
    weighted_delta = np.zeros_like(global_depth, dtype=np.float32)
    total_weight = np.zeros_like(global_depth, dtype=np.float32)
    face_records: list[dict[str, object]] = []

    for index, (face, dense) in enumerate(zip(faces, dense_matches, strict=True), start=1):
        crop = expanded_square(face, width, height, args.crop_expansion)
        x1, y1, x2, y2 = crop
        crop_rgb = image_rgb[y1:y2, x1:x2]
        global_patch = global_depth[y1:y2, x1:x2]
        report(
            f"[face] {index}/{len(faces)} box {face.x1},{face.y1},{face.x2},{face.y2} "
            f"crop {crop_rgb.shape[1]}x{crop_rgb.shape[0]}"
        )
        local = backend.infer_near_depth(crop_rgb)
        if local.shape != global_patch.shape:
            local = cv2.resize(local, (global_patch.shape[1], global_patch.shape[0]), interpolation=cv2.INTER_CUBIC)
        weight = landmark_weight(face, dense, crop, args.feather)
        aligned, slope, offset = align_local_depth(local, global_patch, weight)
        detail_sigma = max(1.0, min(face.width, face.height) * 0.025)
        delta = refinement_delta(aligned, global_patch, detail_sigma, args.shape_mix, args.max_delta)
        contribution = weight * float(args.strength)
        weighted_delta[y1:y2, x1:x2] += delta * contribution
        total_weight[y1:y2, x1:x2] += contribution
        mean_change = float(np.sum(np.abs(delta) * weight) / max(1e-6, np.sum(weight)))
        face_records.append(
            {
                "index": index,
                "source": face.source,
                "confidence": face.confidence,
                "box": [face.x1, face.y1, face.x2, face.y2],
                "crop": [x1, y1, x2, y2],
                "landmarks": [list(point) for point in face.landmarks],
                "dense_landmark_count": len(dense.core),
                "dense_landmarks_468": [list(point) for point in dense.core],
                "iris_landmark_count": len(dense.iris),
                "iris_landmarks_10": [list(point) for point in dense.iris],
                "alignment_slope": slope,
                "alignment_offset": offset,
                "mean_absolute_depth_change": mean_change,
            }
        )

    combined_delta = np.divide(
        weighted_delta,
        np.maximum(total_weight, 1e-6),
        out=np.zeros_like(weighted_delta),
        where=total_weight > 0,
    )
    blend_weight = np.clip(total_weight, 0.0, 1.0)
    refined = np.clip(global_depth + combined_delta * blend_weight, 0.0, 1.0)

    prepare_output(args.output)
    Image.fromarray((refined * 65535).astype(np.uint16)).save(args.output)
    save_previews(aux_output, image_rgb, global_depth, refined, faces, dense_matches)

    metadata = {
        "face_count": len(faces),
        "known_face_count": args.known_face_count or None,
        "face_refinement_required": True,
        "face_refinement_complete": True,
        "backend": "moge-2-face-crops",
        "dense_landmark_backend": "mediapipe-face-landmarker",
        "dense_landmark_strategy": "one-high-resolution-crop-per-detected-face",
        "dense_landmarks_per_face": CORE_LANDMARK_COUNT,
        "model": str(backend.checkpoint),
        "resolution_level": args.moge_resolution_level,
        "device": device,
        "input_depth": str(args.depth),
        "output": str(args.output),
        "convention": "16-bit PNG, bright = near = raised",
        "settings": {
            "crop_expansion": args.crop_expansion,
            "feather": args.feather,
            "strength": args.strength,
            "shape_mix": args.shape_mix,
            "max_delta": args.max_delta,
        },
        "faces": face_records,
    }
    sidecar = args.output.with_suffix(".json")
    sidecar.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    report(f"[face] wrote {args.output}")
    report(f"[face] wrote {sidecar}")
    report(f"[face] previews {aux_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
