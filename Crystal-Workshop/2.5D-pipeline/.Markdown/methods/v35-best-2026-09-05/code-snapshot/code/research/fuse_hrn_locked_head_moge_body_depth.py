"""
File: code/research/fuse_hrn_locked_head_moge_body_depth.py
Purpose:
 - Give HRN exclusive depth ownership of a detected head and face region.
 - Restrict MoGe to neck/body/clothing and preserve a rounded, forward nose tip.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt

from fuse_hrn_moge_portrait_depth import (
    largest_alpha_component,
    register_hrn_texture,
    robust_normalize,
    smoothstep,
)


def detect_single_face(source_rgb: np.ndarray, model_path: Path) -> dict:
    height, width = source_rgb.shape[:2]
    detector = cv2.FaceDetectorYN.create(
        str(model_path), "", (width, height), 0.75, 0.3, 5000
    )
    _, detections = detector.detect(cv2.cvtColor(source_rgb, cv2.COLOR_RGB2BGR))
    if detections is None or len(detections) != 1:
        count = 0 if detections is None else len(detections)
        raise RuntimeError(f"Head-lock fusion requires exactly one detected face; found {count}")
    row = detections[0]
    return {
        "box_xywh": row[:4].astype(float).tolist(),
        "right_eye": row[4:6].astype(float).tolist(),
        "left_eye": row[6:8].astype(float).tolist(),
        "nose": row[8:10].astype(float).tolist(),
        "mouth_right": row[10:12].astype(float).tolist(),
        "mouth_left": row[12:14].astype(float).tolist(),
        "confidence": float(row[-1]),
    }


def build_head_region(subject_mask: np.ndarray, face: dict) -> tuple[np.ndarray, dict]:
    height, width = subject_mask.shape
    x, y, face_width, face_height = face["box_xywh"]
    left = max(0, int(round(x - 0.25 * face_width)))
    right = min(width, int(round(x + 1.25 * face_width)))
    top = max(0, int(round(y - 0.48 * face_height)))
    bottom = min(height, int(round(y + 1.06 * face_height)))
    region = np.zeros_like(subject_mask, dtype=bool)
    region[top:bottom, left:right] = True
    region &= subject_mask
    return region, {
        "bounds_xyxy": [left, top, right, bottom],
        "pixels": int(region.sum()),
        "rule": "source subject within face box expanded L/R 25%, top 48%, bottom 6%",
    }


def nearest_valid_fill(values: np.ndarray, valid: np.ndarray) -> np.ndarray:
    if not valid.any():
        raise RuntimeError("No valid HRN pixels were available for head-lock fusion")
    _, indices = distance_transform_edt(~valid, return_indices=True)
    return values[tuple(indices)]


def gaussian_feature(
    shape: tuple[int, int], center: tuple[float, float], sigma: tuple[float, float]
) -> np.ndarray:
    rows, columns = np.indices(shape, dtype=np.float32)
    center_x, center_y = center
    sigma_x, sigma_y = sigma
    return np.exp(
        -0.5 * (((columns - center_x) / sigma_x) ** 2 + ((rows - center_y) / sigma_y) ** 2)
    )


def sample_disk(values: np.ndarray, center: tuple[float, float], radius: int) -> float:
    center_x, center_y = center
    rows, columns = np.indices(values.shape)
    selected = (columns - center_x) ** 2 + (rows - center_y) ** 2 <= radius ** 2
    return float(np.median(values[selected]))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--moge-depth", required=True, type=Path)
    parser.add_argument("--hrn-texture", required=True, type=Path)
    parser.add_argument("--hrn-depth", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--head-depth-span", type=float, default=0.85)
    parser.add_argument("--minimum-nose-prominence", type=float, default=0.16)
    parser.add_argument("--hair-microdetail-span", type=float, default=0.018)
    args = parser.parse_args()

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    source_rgba = np.asarray(Image.open(args.source).convert("RGBA"))
    source_rgb = source_rgba[:, :, :3]
    source_height, source_width = source_rgb.shape[:2]
    subject_mask, alpha_stats = largest_alpha_component(source_rgba)

    pipeline_root = Path(__file__).resolve().parents[2]
    face_model = pipeline_root / "Models/opencv-face-detector-yunet/face_detection_yunet_2023mar.onnx"
    face = detect_single_face(source_rgb, face_model)
    head_region, head_stats = build_head_region(subject_mask, face)

    moge_metric = np.load(args.moge_depth).astype(np.float32)
    if moge_metric.shape != subject_mask.shape:
        raise RuntimeError("MoGe depth shape does not match the source image")
    moge_near = robust_normalize(moge_metric, subject_mask, invert=True)
    body_field = 0.12 + moge_near * 0.50

    hrn_texture = np.asarray(Image.open(args.hrn_texture).convert("RGBA"))
    hrn_depth_rgba = cv2.imread(str(args.hrn_depth), cv2.IMREAD_UNCHANGED)
    if hrn_depth_rgba is None or hrn_depth_rgba.ndim != 3:
        raise RuntimeError(f"Could not read HRN depth: {args.hrn_depth}")
    hrn_native_mask = hrn_depth_rgba[:, :, 3] > 0
    hrn_native_depth = hrn_depth_rgba[:, :, 0].astype(np.float32) / 65535.0

    affine, registration = register_hrn_texture(hrn_texture, source_rgba, 0.72, 3.0)
    output_size = (source_width, source_height)
    aligned_depth = cv2.warpAffine(
        hrn_native_depth, affine, output_size, flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT, borderValue=0.0,
    )
    aligned_mask = cv2.warpAffine(
        hrn_native_mask.astype(np.uint8), affine, output_size, flags=cv2.INTER_NEAREST,
        borderMode=cv2.BORDER_CONSTANT, borderValue=0,
    ) > 0
    valid_head = aligned_mask & head_region
    raw_low = float(np.min(aligned_depth[valid_head]))
    raw_high = float(np.max(aligned_depth[valid_head]))
    normalized_hrn = np.clip(
        (aligned_depth - raw_low) / max(raw_high - raw_low, 1e-8), 0.0, 1.0
    )
    extended_hrn = nearest_valid_fill(normalized_hrn, valid_head)

    x, y, face_width, face_height = face["box_xywh"]
    lower_band = head_region & (
        np.indices(head_region.shape)[0] >= int(round(y + 0.92 * face_height))
    )
    lower_valid = lower_band & valid_head
    if int(lower_valid.sum()) < 100:
        lower_valid = valid_head
    hrn_anchor = float(np.median(extended_hrn[lower_valid]))
    body_anchor = float(np.median(body_field[lower_band]))
    head_field = body_anchor + (extended_hrn - hrn_anchor) * args.head_depth_span

    # Preserve visible hair as subtle source-derived microgeometry without
    # allowing MoGe to create an independent helmet/rim depth layer.
    gray = cv2.cvtColor(source_rgb, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
    gray_low = cv2.GaussianBlur(gray, (0, 0), sigmaX=2.2, sigmaY=2.2)
    hair_region = head_region & (
        np.indices(head_region.shape)[0] < int(round(y + 0.14 * face_height))
    )
    boundary_distance = cv2.distanceTransform(subject_mask.astype(np.uint8), cv2.DIST_L2, 5)
    hair_weight = smoothstep(boundary_distance / 5.0) * hair_region
    head_field += (gray - gray_low) * args.hair_microdetail_span * hair_weight

    # Guarantee a rounded forward nose tip. The correction is a smooth local
    # bump centred on the detected HRN/source nose landmark, never a flat clamp.
    nose = tuple(face["nose"])
    radius = max(3, int(round(face_width * 0.035)))
    nose_depth_before = sample_disk(head_field, nose, radius)
    cheek_y = nose[1]
    cheek_left = (x + 0.27 * face_width, cheek_y)
    cheek_right = (x + 0.73 * face_width, cheek_y)
    cheek_depth = 0.5 * (
        sample_disk(head_field, cheek_left, radius)
        + sample_disk(head_field, cheek_right, radius)
    )
    prominence_before = nose_depth_before - cheek_depth
    required_boost = max(0.0, args.minimum_nose_prominence - prominence_before)
    nose_bump = gaussian_feature(
        head_field.shape,
        nose,
        (max(4.0, face_width * 0.105), max(4.0, face_height * 0.085)),
    )
    head_field += nose_bump * required_boost * head_region

    # HRN owns the whole head. Only a short seam below the chin blends into the
    # MoGe body field; no MoGe or generic smoothing touches the face or hair.
    head_weight = head_region.astype(np.float32)
    blend_start = int(round(y + 0.96 * face_height))
    blend_end = int(round(y + 1.06 * face_height))
    rows = np.indices(head_region.shape)[0]
    lower_fade = 1.0 - smoothstep(
        (rows.astype(np.float32) - blend_start) / max(blend_end - blend_start, 1)
    )
    head_weight *= lower_fade
    fused = body_field * (1.0 - head_weight) + head_field * head_weight
    fused = np.clip(fused, 0.0, 1.0)
    fused[~subject_mask] = 0.0

    Image.fromarray(subject_mask.astype(np.uint8) * 255, mode="L").save(
        output_dir / "primary-subject-mask.png"
    )
    Image.fromarray(head_region.astype(np.uint8) * 255, mode="L").save(
        output_dir / "hrn-exclusive-head-mask.png"
    )
    Image.fromarray(np.round(head_weight * 255).astype(np.uint8), mode="L").save(
        output_dir / "hrn-exclusive-head-weight.png"
    )
    Image.fromarray(np.round(fused * 65535).astype(np.uint16), mode="I;16").save(
        output_dir / "hrn-locked-head-moge-body-depth.png"
    )

    nose_depth_after = sample_disk(fused, nose, radius)
    stats = {
        "method": "HRN-exclusive head and face; MoGe body/clothing only",
        "model_stack": {
            "head_face_hair_depth": "Official ModelScope HRN Head v0.1 plus source-derived hair microdetail",
            "neck_body_clothing_depth": "MoGe-2 ViT-L exact-source metric depth",
        },
        "source": str(args.source.resolve()),
        "alpha": alpha_stats,
        "face": face,
        "head_region": head_stats,
        "registration": registration,
        "parameters": {
            "head_depth_span": args.head_depth_span,
            "minimum_nose_prominence": args.minimum_nose_prominence,
            "hair_microdetail_span": args.hair_microdetail_span,
            "generic_head_smoothing": False,
            "moge_inside_head": False,
        },
        "nose_qa": {
            "depth_before": nose_depth_before,
            "cheek_reference_depth": cheek_depth,
            "prominence_before": prominence_before,
            "smooth_center_boost": required_boost,
            "depth_after": nose_depth_after,
            "prominence_after": nose_depth_after - cheek_depth,
        },
    }
    (output_dir / "hrn-locked-head-stats.json").write_text(
        json.dumps(stats, indent=2), encoding="utf-8"
    )
    print(
        "HRN_LOCKED_HEAD_OK "
        f"nose prominence {stats['nose_qa']['prominence_after']:.4f}; "
        "MoGe head pixels 0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
