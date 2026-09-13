"""
File: code/research/source_camera_fusion.py
Purpose:
 - Register per-person ICON/d-BiNI surfaces back into the original source camera.
 - Preserve pixel aspect ratio, vertex color, registration evidence, and local depth.
 - Keep relative inter-person depth explicitly unanchored until scene-depth fusion.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
import trimesh
from PIL import Image, ImageDraw


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--raw-dir", required=True, type=Path)
    parser.add_argument("--mesh-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--subject", action="append", dest="subjects")
    parser.add_argument("--ratio-threshold", type=float, default=0.70)
    parser.add_argument("--ransac-threshold-px", type=float, default=2.0)
    parser.add_argument("--minimum-inliers", type=int, default=40)
    parser.add_argument("--minimum-inlier-ratio", type=float, default=0.75)
    parser.add_argument("--maximum-median-error-px", type=float, default=0.75)
    parser.add_argument("--depth-anchor-percentile", type=float, default=1.0)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def icon_image_to_rgb(image_chw: np.ndarray) -> np.ndarray:
    """Convert ICON's CHW [-1, 1] image tensor to uint8 RGB."""

    image_hwc = np.transpose(image_chw, (1, 2, 0))
    return np.clip((image_hwc + 1.0) * 127.5, 0.0, 255.0).astype(np.uint8)


def estimate_similarity_registration(
    raw_rgb: np.ndarray,
    source_rgb: np.ndarray,
    ratio_threshold: float,
    ransac_threshold_px: float,
) -> tuple[np.ndarray, dict, np.ndarray, np.ndarray, np.ndarray]:
    """Estimate a raw-ICON-pixel to source-pixel similarity transform with SIFT."""

    sift = cv2.SIFT_create(nfeatures=8000)
    raw_gray = cv2.cvtColor(raw_rgb, cv2.COLOR_RGB2GRAY)
    source_gray = cv2.cvtColor(source_rgb, cv2.COLOR_RGB2GRAY)
    raw_keypoints, raw_descriptors = sift.detectAndCompute(raw_gray, None)
    source_keypoints, source_descriptors = sift.detectAndCompute(source_gray, None)
    if raw_descriptors is None or source_descriptors is None:
        raise RuntimeError("SIFT could not find descriptors in both images")

    pairs = cv2.BFMatcher(cv2.NORM_L2).knnMatch(raw_descriptors, source_descriptors, k=2)
    matches = [first for first, second in pairs if first.distance < ratio_threshold * second.distance]
    if len(matches) < 3:
        raise RuntimeError(f"Only {len(matches)} SIFT ratio-test matches were found")

    raw_points = np.float32([raw_keypoints[item.queryIdx].pt for item in matches])
    source_points = np.float32([source_keypoints[item.trainIdx].pt for item in matches])
    affine, inliers = cv2.estimateAffinePartial2D(
        raw_points,
        source_points,
        method=cv2.RANSAC,
        ransacReprojThreshold=ransac_threshold_px,
        maxIters=5000,
        confidence=0.999,
        refineIters=50,
    )
    if affine is None or inliers is None:
        raise RuntimeError("RANSAC could not estimate a similarity transform")

    projected = cv2.transform(raw_points[None, :, :], affine)[0]
    errors = np.linalg.norm(projected - source_points, axis=1)
    inlier_mask = inliers.ravel().astype(bool)
    linear = affine[:, :2]
    singular_values = np.linalg.svd(linear, compute_uv=False)
    scale = float(np.sqrt(abs(np.linalg.det(linear))))
    rotation_degrees = float(np.degrees(np.arctan2(linear[1, 0], linear[0, 0])))
    metrics = {
        "raw_keypoints": len(raw_keypoints),
        "source_keypoints": len(source_keypoints),
        "ratio_test_matches": len(matches),
        "inliers": int(inlier_mask.sum()),
        "inlier_ratio": float(inlier_mask.mean()),
        "median_reprojection_error_px": float(np.median(errors[inlier_mask])),
        "p95_reprojection_error_px": float(np.percentile(errors[inlier_mask], 95.0)),
        "similarity_scale_source_px_per_raw_px": scale,
        "rotation_degrees": rotation_degrees,
        "linear_singular_values": singular_values.tolist(),
    }
    return affine, metrics, raw_points, source_points, inlier_mask


def validate_registration(metrics: dict, args: argparse.Namespace) -> None:
    failures = []
    if metrics["inliers"] < args.minimum_inliers:
        failures.append(f"inliers {metrics['inliers']} < {args.minimum_inliers}")
    if metrics["inlier_ratio"] < args.minimum_inlier_ratio:
        failures.append(
            f"inlier ratio {metrics['inlier_ratio']:.3f} < {args.minimum_inlier_ratio:.3f}"
        )
    if metrics["median_reprojection_error_px"] > args.maximum_median_error_px:
        failures.append(
            "median error "
            f"{metrics['median_reprojection_error_px']:.3f}px > "
            f"{args.maximum_median_error_px:.3f}px"
        )
    if failures:
        raise RuntimeError("Registration quality gate failed: " + "; ".join(failures))


def icon_xy_to_raw_pixels(vertices_xy: np.ndarray, raw_size: tuple[int, int]) -> np.ndarray:
    """Match ICON query_color/grid_sample coordinates exactly (align_corners=True)."""

    raw_width, raw_height = raw_size
    raw_x = (vertices_xy[:, 0] + 1.0) * 0.5 * (raw_width - 1)
    raw_y = (1.0 - vertices_xy[:, 1]) * 0.5 * (raw_height - 1)
    return np.column_stack((raw_x, raw_y))


def apply_affine(points_xy: np.ndarray, affine: np.ndarray) -> np.ndarray:
    homogeneous = np.column_stack((points_xy, np.ones(len(points_xy))))
    return homogeneous @ affine.T


def sample_source_colors(source_rgb: np.ndarray, source_pixels: np.ndarray) -> np.ndarray:
    """Bilinearly sample the original source so repaired vertices never inherit mask-black."""

    height, width = source_rgb.shape[:2]
    x = source_pixels[:, 0].astype(np.float64)
    y = source_pixels[:, 1].astype(np.float64)
    valid = (x >= 0.0) & (x <= width - 1) & (y >= 0.0) & (y <= height - 1)
    x = np.clip(x, 0.0, width - 1)
    y = np.clip(y, 0.0, height - 1)
    x0 = np.floor(x).astype(np.int64)
    y0 = np.floor(y).astype(np.int64)
    x1 = np.minimum(x0 + 1, width - 1)
    y1 = np.minimum(y0 + 1, height - 1)
    fraction_x = (x - x0)[:, None]
    fraction_y = (y - y0)[:, None]
    top = source_rgb[y0, x0] * (1.0 - fraction_x) + source_rgb[y0, x1] * fraction_x
    bottom = source_rgb[y1, x0] * (1.0 - fraction_x) + source_rgb[y1, x1] * fraction_x
    sampled = np.round(top * (1.0 - fraction_y) + bottom * fraction_y).astype(np.uint8)
    sampled[~valid] = 0
    alpha = np.full((len(sampled), 1), 255, dtype=np.uint8)
    return np.column_stack((sampled, alpha))


def source_pixels_to_scene(points_xy: np.ndarray, source_size: tuple[int, int]) -> np.ndarray:
    """Use source image height as unit scale so horizontal and vertical pixels stay square."""

    source_width, source_height = source_size
    half_height = (source_height - 1) * 0.5
    center_x = (source_width - 1) * 0.5
    center_y = (source_height - 1) * 0.5
    scene_x = (points_xy[:, 0] - center_x) / half_height
    scene_y = (center_y - points_xy[:, 1]) / half_height
    return np.column_stack((scene_x, scene_y))


def transform_vertices(
    vertices: np.ndarray,
    affine: np.ndarray,
    raw_size: tuple[int, int],
    source_size: tuple[int, int],
    depth_anchor_percentile: float,
) -> tuple[np.ndarray, dict]:
    raw_pixels = icon_xy_to_raw_pixels(vertices[:, :2], raw_size)
    source_pixels = apply_affine(raw_pixels, affine)
    scene_xy = source_pixels_to_scene(source_pixels, source_size)

    source_height = source_size[1]
    raw_span = max(raw_size) - 1
    similarity_scale = float(np.sqrt(abs(np.linalg.det(affine[:, :2]))))
    isotropic_scene_scale = similarity_scale * raw_span / (source_height - 1)
    depth_anchor = float(np.percentile(vertices[:, 2], depth_anchor_percentile))
    scene_z = (vertices[:, 2] - depth_anchor) * isotropic_scene_scale
    transformed = np.column_stack((scene_xy, scene_z))
    return transformed, {
        "depth_anchor_percentile": depth_anchor_percentile,
        "depth_anchor_native": depth_anchor,
        "isotropic_scene_scale": isotropic_scene_scale,
        "source_pixel_bounds": [source_pixels.min(axis=0).tolist(), source_pixels.max(axis=0).tolist()],
        "scene_bounds": [transformed.min(axis=0).tolist(), transformed.max(axis=0).tolist()],
    }


def create_registration_overlay(
    source_rgb: np.ndarray,
    subject_masks: list[tuple[str, np.ndarray]],
    output_path: Path,
) -> None:
    overlay = source_rgb.copy()
    palette = [(38, 203, 255), (255, 88, 166), (255, 209, 64), (89, 238, 136)]
    for index, (_, mask) in enumerate(subject_masks):
        color = np.array(palette[index % len(palette)], dtype=np.float32)
        selected = mask > 0
        overlay[selected] = np.round(overlay[selected] * 0.72 + color * 0.28).astype(np.uint8)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(overlay, contours, -1, tuple(int(v) for v in color), 3, cv2.LINE_AA)

    image = Image.fromarray(overlay)
    draw = ImageDraw.Draw(image)
    legend_y = 14
    for index, (subject, _) in enumerate(subject_masks):
        color = palette[index % len(palette)]
        draw.rounded_rectangle((14, legend_y, 170, legend_y + 29), radius=5, fill=(0, 0, 0, 185))
        draw.rectangle((22, legend_y + 8, 35, legend_y + 21), fill=color)
        draw.text((43, legend_y + 6), f"{subject} registration", fill=(255, 255, 255))
        legend_y += 36
    image.save(output_path, optimize=True)


def main() -> None:
    args = parse_arguments()
    subjects = args.subjects or ["man", "woman"]
    source_path = args.source.resolve()
    raw_dir = args.raw_dir.resolve()
    mesh_dir = args.mesh_dir.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    source_rgb = np.array(Image.open(source_path).convert("RGB"))
    source_height, source_width = source_rgb.shape[:2]
    stats = {
        "source": str(source_path),
        "source_sha256": sha256(source_path),
        "source_size": [source_width, source_height],
        "coordinate_system": {
            "x": "right in source image",
            "y": "up in source image",
            "z": "toward source camera",
            "xy_scale": "source image height is 2.0 scene units; pixels remain square",
            "relative_subject_depth": (
                "not yet measured; each subject uses its own robust back-depth anchor until MoGe fusion"
            ),
        },
        "quality_gates": {
            "minimum_inliers": args.minimum_inliers,
            "minimum_inlier_ratio": args.minimum_inlier_ratio,
            "maximum_median_error_px": args.maximum_median_error_px,
        },
        "subjects": {},
    }
    transformed_meshes = {}
    warped_masks = []

    for subject in subjects:
        raw_path = raw_dir / f"{subject}_icon_front_raw.npz"
        mesh_path = mesh_dir / f"{subject}_icon_front_bni.obj"
        if not raw_path.exists() or not mesh_path.exists():
            raise FileNotFoundError(f"Missing raw payload or front mesh for subject '{subject}'")

        raw_payload = np.load(raw_path)
        raw_rgb = icon_image_to_rgb(raw_payload["image"])
        raw_height, raw_width = raw_rgb.shape[:2]
        affine, metrics, _, _, _ = estimate_similarity_registration(
            raw_rgb,
            source_rgb,
            args.ratio_threshold,
            args.ransac_threshold_px,
        )
        validate_registration(metrics, args)

        mesh = trimesh.load(mesh_path, force="mesh", process=False, maintain_order=True)
        original_vertices = np.asarray(mesh.vertices).copy()
        transformed_vertices, transform_stats = transform_vertices(
            original_vertices,
            affine,
            (raw_width, raw_height),
            (source_width, source_height),
            args.depth_anchor_percentile,
        )
        mesh.vertices = transformed_vertices
        raw_pixels = icon_xy_to_raw_pixels(original_vertices[:, :2], (raw_width, raw_height))
        source_pixels = apply_affine(raw_pixels, affine)
        mesh.visual.vertex_colors = sample_source_colors(source_rgb, source_pixels)
        transformed_meshes[subject] = mesh

        subject_obj = output_dir / f"{subject}_source_camera.obj"
        subject_glb = output_dir / f"{subject}_source_camera.glb"
        mesh.export(subject_obj)
        mesh.export(subject_glb)

        warped_mask = cv2.warpAffine(
            raw_payload["mask"].astype(np.uint8) * 255,
            affine,
            (source_width, source_height),
            flags=cv2.INTER_NEAREST,
        )
        warped_masks.append((subject, warped_mask))

        stats["subjects"][subject] = {
            "raw_payload": str(raw_path),
            "raw_payload_sha256": sha256(raw_path),
            "input_mesh": str(mesh_path),
            "input_mesh_sha256": sha256(mesh_path),
            "raw_size": [raw_width, raw_height],
            "affine_raw_px_to_source_px": affine.tolist(),
            "registration": metrics,
            "transform": transform_stats,
            "vertices": int(len(mesh.vertices)),
            "triangles": int(len(mesh.faces)),
            "output_obj": subject_obj.name,
            "output_glb": subject_glb.name,
        }
        print(
            f"[source-camera] {subject}: {metrics['inliers']}/{metrics['ratio_test_matches']} "
            f"inliers, median={metrics['median_reprojection_error_px']:.3f}px, "
            f"scale={metrics['similarity_scale_source_px_per_raw_px']:.6f}"
        )

    combined = trimesh.util.concatenate(list(transformed_meshes.values()))
    combined_obj = output_dir / "both_source_camera.obj"
    combined.export(combined_obj)
    combined_scene = trimesh.Scene()
    for subject, mesh in transformed_meshes.items():
        combined_scene.add_geometry(mesh, node_name=subject, geom_name=subject)
    combined_glb = output_dir / "both_source_camera.glb"
    combined_scene.export(combined_glb)
    stats["combined"] = {
        "vertices": int(len(combined.vertices)),
        "triangles": int(len(combined.faces)),
        "components": len(transformed_meshes),
        "bounds": combined.bounds.tolist(),
        "obj": combined_obj.name,
        "glb": combined_glb.name,
    }

    overlay_path = output_dir / "source_camera_registration_overlay.png"
    create_registration_overlay(source_rgb, warped_masks, overlay_path)
    stats["registration_overlay"] = overlay_path.name
    with (output_dir / "source_camera_fusion_stats.json").open("w", encoding="utf-8") as handle:
        json.dump(stats, handle, indent=2)


if __name__ == "__main__":
    main()
