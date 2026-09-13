"""
File: code/research/fuse_hrn_moge_portrait_depth.py
Purpose:
 - Fuse source-registered HRN head depth into a MoGe-2 portrait depth field.
 - Reject disconnected alpha objects and keep the original photograph as appearance.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--moge-depth", required=True, type=Path)
    parser.add_argument("--hrn-texture", required=True, type=Path)
    parser.add_argument("--hrn-depth", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--ratio-threshold", type=float, default=0.72)
    parser.add_argument("--ransac-threshold-px", type=float, default=3.0)
    parser.add_argument("--hrn-depth-span", type=float, default=0.34)
    parser.add_argument("--feather-fraction", type=float, default=0.035)
    parser.add_argument("--vertical-fade-start", type=float, default=0.72)
    parser.add_argument("--vertical-fade-end", type=float, default=0.87)
    return parser.parse_args()


def smoothstep(values: np.ndarray) -> np.ndarray:
    clipped = np.clip(values, 0.0, 1.0)
    return clipped * clipped * (3.0 - 2.0 * clipped)


def robust_normalize(values: np.ndarray, mask: np.ndarray, invert: bool = False) -> np.ndarray:
    low, high = np.percentile(values[mask], [1.0, 99.0])
    normalized = np.clip((values - low) / max(high - low, 1e-8), 0.0, 1.0)
    return 1.0 - normalized if invert else normalized


def largest_alpha_component(source_rgba: np.ndarray) -> tuple[np.ndarray, dict]:
    alpha = source_rgba[:, :, 3]
    binary = (alpha >= 128).astype(np.uint8)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(binary, 8)
    if count <= 1:
        raise RuntimeError("The source alpha contains no foreground component")
    component = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    mask = labels == component
    return mask, {
        "component_count": int(count - 1),
        "kept_area_px": int(stats[component, cv2.CC_STAT_AREA]),
        "kept_bbox_xywh": stats[component, :4].astype(int).tolist(),
        "discarded_area_px": int(binary.sum() - stats[component, cv2.CC_STAT_AREA]),
    }


def register_hrn_texture(
    hrn_rgba: np.ndarray,
    source_rgba: np.ndarray,
    ratio_threshold: float,
    ransac_threshold: float,
) -> tuple[np.ndarray, dict]:
    hrn_gray = cv2.cvtColor(hrn_rgba[:, :, :3], cv2.COLOR_RGB2GRAY)
    source_gray = cv2.cvtColor(source_rgba[:, :, :3], cv2.COLOR_RGB2GRAY)
    sift = cv2.SIFT_create(nfeatures=10000)
    hrn_keypoints, hrn_descriptors = sift.detectAndCompute(hrn_gray, None)
    source_keypoints, source_descriptors = sift.detectAndCompute(source_gray, None)
    pairs = cv2.BFMatcher(cv2.NORM_L2).knnMatch(
        hrn_descriptors, source_descriptors, k=2
    )
    matches = [
        first for first, second in pairs
        if first.distance < ratio_threshold * second.distance
    ]
    if len(matches) < 6:
        raise RuntimeError(f"Only {len(matches)} HRN/source SIFT matches survived")
    hrn_points = np.float32([hrn_keypoints[item.queryIdx].pt for item in matches])
    source_points = np.float32([source_keypoints[item.trainIdx].pt for item in matches])
    affine, inliers = cv2.estimateAffinePartial2D(
        hrn_points,
        source_points,
        method=cv2.RANSAC,
        ransacReprojThreshold=ransac_threshold,
        maxIters=10000,
        confidence=0.999,
        refineIters=100,
    )
    if affine is None or inliers is None:
        raise RuntimeError("RANSAC could not register HRN to the source portrait")
    projected = cv2.transform(hrn_points[None, :, :], affine)[0]
    errors = np.linalg.norm(projected - source_points, axis=1)
    accepted = inliers.ravel().astype(bool)
    return affine, {
        "hrn_keypoints": len(hrn_keypoints),
        "source_keypoints": len(source_keypoints),
        "ratio_test_matches": len(matches),
        "inliers": int(accepted.sum()),
        "inlier_ratio": float(accepted.mean()),
        "median_reprojection_error_px": float(np.median(errors[accepted])),
        "p95_reprojection_error_px": float(np.percentile(errors[accepted], 95.0)),
        "affine_hrn_to_source": affine.tolist(),
    }


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    source_rgba = np.asarray(Image.open(args.source).convert("RGBA"))
    source_height, source_width = source_rgba.shape[:2]
    subject_mask, alpha_stats = largest_alpha_component(source_rgba)

    moge_metric = np.load(args.moge_depth).astype(np.float32)
    if moge_metric.shape != subject_mask.shape:
        raise RuntimeError(
            f"MoGe shape {moge_metric.shape} does not match source {subject_mask.shape}"
        )
    moge_near = robust_normalize(moge_metric, subject_mask, invert=True)
    base_depth = 0.12 + moge_near * 0.50

    hrn_texture = np.asarray(Image.open(args.hrn_texture).convert("RGBA"))
    hrn_depth_rgba = cv2.imread(str(args.hrn_depth), cv2.IMREAD_UNCHANGED)
    if hrn_depth_rgba is None or hrn_depth_rgba.ndim != 3:
        raise RuntimeError(f"Could not read 16-bit HRN RGBA depth: {args.hrn_depth}")
    if hrn_depth_rgba.shape[2] == 4:
        hrn_mask = hrn_depth_rgba[:, :, 3] > 0
    else:
        hrn_mask = np.asarray(Image.open(args.hrn_depth).convert("RGBA"))[:, :, 3] > 0
    hrn_depth_native = hrn_depth_rgba[:, :, 0].astype(np.float32)
    hrn_depth_native /= float(np.iinfo(hrn_depth_rgba.dtype).max)

    affine, registration = register_hrn_texture(
        hrn_texture,
        source_rgba,
        args.ratio_threshold,
        args.ransac_threshold_px,
    )

    hrn_rows, hrn_columns = np.where(hrn_mask)
    hrn_top = int(hrn_rows.min())
    hrn_bottom = int(hrn_rows.max())
    normalized_y = (
        np.arange(hrn_mask.shape[0], dtype=np.float32)[:, None] - hrn_top
    ) / max(hrn_bottom - hrn_top, 1)
    vertical_weight = 1.0 - smoothstep(
        (normalized_y - args.vertical_fade_start)
        / max(args.vertical_fade_end - args.vertical_fade_start, 1e-6)
    )
    feather_px = max(2, round(max(hrn_mask.shape) * args.feather_fraction))
    distance = cv2.distanceTransform(hrn_mask.astype(np.uint8), cv2.DIST_L2, 5)
    native_weight = smoothstep(distance / feather_px) * vertical_weight * hrn_mask

    output_size = (source_width, source_height)
    aligned_depth = cv2.warpAffine(
        hrn_depth_native,
        affine,
        output_size,
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0.0,
    )
    aligned_weight = cv2.warpAffine(
        native_weight.astype(np.float32),
        affine,
        output_size,
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0.0,
    )
    aligned_weight *= subject_mask.astype(np.float32)
    aligned_valid = aligned_weight > 1e-4
    if not aligned_valid.any():
        raise RuntimeError("The registered HRN depth does not overlap the source subject")

    aligned_hrn_normalized = robust_normalize(aligned_depth, aligned_valid)
    seam = (aligned_weight > 0.02) & (aligned_weight < 0.35) & subject_mask
    if int(seam.sum()) < 100:
        seam = aligned_valid & (aligned_weight < 0.6)
    base_anchor = float(np.median(base_depth[seam]))
    hrn_anchor = float(np.median(aligned_hrn_normalized[seam]))
    hrn_field = base_anchor + (aligned_hrn_normalized - hrn_anchor) * args.hrn_depth_span

    fused = base_depth.copy()
    fused[subject_mask] = (
        base_depth[subject_mask] * (1.0 - aligned_weight[subject_mask])
        + hrn_field[subject_mask] * aligned_weight[subject_mask]
    )
    fused = np.clip(fused, 0.0, 1.0)
    fused[~subject_mask] = 0.0

    aligned_texture = cv2.warpAffine(
        cv2.cvtColor(hrn_texture, cv2.COLOR_RGBA2BGRA),
        affine,
        output_size,
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(0, 0, 0, 0),
    )
    source_bgr = cv2.cvtColor(source_rgba[:, :, :3], cv2.COLOR_RGB2BGR)
    overlay = source_bgr.astype(np.float32)
    preview_weight = np.clip(aligned_weight * 0.45, 0.0, 0.45)[:, :, None]
    overlay = overlay * (1.0 - preview_weight) + aligned_texture[:, :, :3] * preview_weight

    Image.fromarray((subject_mask.astype(np.uint8) * 255), mode="L").save(
        output_dir / "primary-subject-mask.png"
    )
    Image.fromarray(
        np.round(fused * 65535.0).astype(np.uint16), mode="I;16"
    ).save(output_dir / "hrn-moge-fused-depth.png")
    Image.fromarray(
        np.round(np.clip(aligned_hrn_normalized, 0.0, 1.0) * 65535.0).astype(np.uint16),
        mode="I;16",
    ).save(output_dir / "hrn-aligned-depth.png")
    Image.fromarray(
        np.round(np.clip(aligned_weight, 0.0, 1.0) * 255.0).astype(np.uint8), mode="L"
    ).save(output_dir / "hrn-fusion-weight.png")
    cv2.imwrite(output_dir / "hrn-registration-overlay.png", np.round(overlay).astype(np.uint8))

    stats = {
        "model_stack": [
            "MoGe-2 ViT-L exact-source metric depth",
            "Official ModelScope HRN Head (BFM+FLAME) native front depth",
        ],
        "source": str(args.source.resolve()),
        "moge_depth": str(args.moge_depth.resolve()),
        "hrn_texture": str(args.hrn_texture.resolve()),
        "hrn_depth": str(args.hrn_depth.resolve()),
        "alpha": alpha_stats,
        "registration": registration,
        "fusion": {
            "hrn_depth_span": args.hrn_depth_span,
            "feather_px_native": feather_px,
            "vertical_fade": [args.vertical_fade_start, args.vertical_fade_end],
            "base_anchor": base_anchor,
            "hrn_anchor": hrn_anchor,
            "hrn_weighted_pixels": int(aligned_valid.sum()),
            "final_depth_percentiles": np.percentile(
                fused[subject_mask], [1.0, 50.0, 99.0]
            ).tolist(),
        },
    }
    (output_dir / "hrn-moge-fusion-stats.json").write_text(
        json.dumps(stats, indent=2), encoding="utf-8"
    )
    print(
        f"HRN_MOGE_PORTRAIT_FUSION_OK {registration['inliers']} inliers, "
        f"median {registration['median_reprojection_error_px']:.3f}px"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
