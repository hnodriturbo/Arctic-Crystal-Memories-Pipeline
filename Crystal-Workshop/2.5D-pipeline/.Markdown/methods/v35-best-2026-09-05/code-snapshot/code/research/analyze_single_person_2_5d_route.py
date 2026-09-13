"""
File: code/research/analyze_single_person_2_5d_route.py
Purpose:
 - Measure what is visibly present in one single-person source photograph.
 - Write an auditable model-route record before 2.5D reconstruction starts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from PIL import Image


POSE_GROUPS = {
    "head": [0, 2, 5, 7, 8],
    "shoulders": [11, 12],
    "elbows": [13, 14],
    "wrists": [15, 16],
    "hips": [23, 24],
    "knees": [25, 26],
    "ankles": [27, 28],
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def model_sha256(path: Path) -> str | None:
    return sha256(path) if path.is_file() else None


def alpha_observations(rgba: np.ndarray) -> dict:
    binary = (rgba[:, :, 3] >= 128).astype(np.uint8)
    count, _, stats, _ = cv2.connectedComponentsWithStats(binary, 8)
    components = sorted(
        (int(stats[index, cv2.CC_STAT_AREA]) for index in range(1, count)),
        reverse=True,
    )
    if not components:
        return {"component_count": 0, "largest_area_fraction": 0.0}
    return {
        "component_count": len(components),
        "largest_area_px": components[0],
        "largest_area_fraction": components[0] / float(binary.size),
        "discarded_area_px": int(sum(components[1:])),
    }


def detect_faces(rgb: np.ndarray, model_path: Path, threshold: float) -> list[dict]:
    height, width = rgb.shape[:2]
    detector = cv2.FaceDetectorYN.create(
        str(model_path), "", (width, height), threshold, 0.3, 5000
    )
    _, detections = detector.detect(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
    faces = []
    for row in [] if detections is None else detections:
        x, y, face_width, face_height = (float(value) for value in row[:4])
        faces.append(
            {
                "box_xywh": [round(x, 3), round(y, 3), round(face_width, 3), round(face_height, 3)],
                "confidence": round(float(row[-1]), 6),
                "width_fraction": face_width / width,
                "height_fraction": face_height / height,
                "area_fraction": (face_width * face_height) / (width * height),
            }
        )
    return sorted(faces, key=lambda item: item["area_fraction"], reverse=True)


def detect_pose(rgb: np.ndarray, model_path: Path, visibility_threshold: float) -> dict:
    base_options = mp.tasks.BaseOptions(model_asset_path=str(model_path))
    options = mp.tasks.vision.PoseLandmarkerOptions(
        base_options=base_options,
        running_mode=mp.tasks.vision.RunningMode.IMAGE,
        num_poses=1,
        min_pose_detection_confidence=0.45,
        min_pose_presence_confidence=0.45,
    )
    with mp.tasks.vision.PoseLandmarker.create_from_options(options) as detector:
        result = detector.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))
    if not result.pose_landmarks:
        return {"pose_detected": False, "visible_groups": {name: False for name in POSE_GROUPS}}
    landmarks = result.pose_landmarks[0]
    groups = {}
    details = {}
    for name, indices in POSE_GROUPS.items():
        accepted = [
            index
            for index in indices
            if landmarks[index].visibility >= visibility_threshold
            and landmarks[index].presence >= visibility_threshold
            and 0.0 <= landmarks[index].x <= 1.0
            and 0.0 <= landmarks[index].y <= 1.0
        ]
        required = 1 if name == "head" else len(indices)
        groups[name] = len(accepted) >= required
        details[name] = {
            "accepted_landmarks": accepted,
            "required": required,
        }
    return {"pose_detected": True, "visible_groups": groups, "group_details": details}


def choose_route(faces: list[dict], pose: dict) -> dict:
    if len(faces) != 1:
        return {
            "selected_profile": "manual-review",
            "confidence": "low",
            "reasons": [f"Expected exactly one face; YuNet detected {len(faces)}."],
            "rejected_profiles": [],
        }

    face = faces[0]
    visible = pose["visible_groups"]
    legs_visible = visible["knees"] or visible["ankles"]
    close_face = face["height_fraction"] >= 0.18
    upper_body_only = visible["shoulders"] and not legs_visible

    if close_face and upper_body_only:
        reasons = [
            f"One dominant face occupies {face['height_fraction']:.1%} of image height.",
            "Shoulders/upper body are visible but knees/ankles are not confirmed.",
            "A full-body HPS prior can hallucinate hidden limbs in this framing.",
        ]
        return {
            "selected_profile": "single-person-close-portrait-hrn-moge",
            "confidence": "high",
            "reasons": reasons,
            "region_ownership": {
                "visible_head_face_ears": "Official ModelScope HRN Head v0.1 (BFM+FLAME)",
                "visible_neck_shoulders_torso_clothing": "MoGe-2 ViT-L exact-source depth",
                "outer_silhouette": "source alpha plus bounded multi-ring backfill",
                "appearance": "original source B/W luma vertex colour",
            },
            "rejected_profiles": [
                {
                    "profile": "PARE -> ICON -> ECON full-body",
                    "reason": "Hidden lower body and limbs are not source-observed; the prior may invent them.",
                }
            ],
        }

    if visible["shoulders"] and visible["hips"] and visible["knees"] and visible["ankles"]:
        return {
            "selected_profile": "single-person-full-body-pare-icon-econ-moge",
            "confidence": "medium",
            "reasons": ["Shoulders, hips, knees, and ankles are all source-visible."],
            "rejected_profiles": [],
        }

    return {
        "selected_profile": "single-person-ambiguous-medium-shot-ab-test",
        "confidence": "low",
        "reasons": [
            "The visible-body evidence does not safely select close-portrait or full-body reconstruction.",
            "Run HRN+MoGe and PARE/ICON/ECON as separate candidates, then record human QA.",
        ],
        "rejected_profiles": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--face-threshold", type=float, default=0.80)
    parser.add_argument("--pose-visibility-threshold", type=float, default=0.55)
    args = parser.parse_args()

    pipeline_root = Path(__file__).resolve().parents[2]
    face_model = pipeline_root / "Models/opencv-face-detector-yunet/face_detection_yunet_2023mar.onnx"
    pose_model = pipeline_root / "Models/mediapipe-pose-landmarker/pose_landmarker_heavy.task"
    for model in (face_model, pose_model):
        if not model.is_file():
            raise FileNotFoundError(f"Required route-analysis model is missing: {model}")

    source = args.source.resolve()
    rgba = np.asarray(Image.open(source).convert("RGBA"))
    rgb = np.ascontiguousarray(rgba[:, :, :3])
    faces = detect_faces(rgb, face_model, args.face_threshold)
    pose = detect_pose(rgb, pose_model, args.pose_visibility_threshold)
    route = choose_route(faces, pose)

    record = {
        "schema": "acm-2.5d-model-route/v1",
        "scope": "one source photograph, one person, source-facing 2.5D",
        "source": {
            "path": str(source),
            "sha256": sha256(source),
            "size_px": [int(rgb.shape[1]), int(rgb.shape[0])],
            "alpha": alpha_observations(rgba),
        },
        "detectors": {
            "face": {"name": "OpenCV YuNet 2023mar", "model_sha256": model_sha256(face_model)},
            "pose": {"name": "MediaPipe Pose Landmarker Heavy", "model_sha256": model_sha256(pose_model)},
        },
        "observed_source_evidence": {
            "faces": faces,
            "pose": pose,
        },
        "routing_decision": route,
        "human_review": {
            "status": "pending",
            "routing_was_correct": None,
            "accepted_artifact": None,
            "observed_failures": [],
            "notes": "Complete after neutral front/30-degree/profile QA.",
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(f"MODEL_ROUTE {route['selected_profile']} ({route['confidence']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
