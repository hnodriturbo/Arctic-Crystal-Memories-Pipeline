"""
File: code/research/integrate_icon_front_bni.py
Purpose:
 - Integrate exported ICON front/back normal tensors with ECON's d-BiNI solver.
 - Preserve only the source-facing front surface for the crystal 2.5D research path.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
import torch
from PIL import Image

from lib.common.BNI import BNI
from lib.common.render import query_color


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--raw-dir", required=True, type=Path)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--k", type=float, default=4.0)
    parser.add_argument("--lambda1", type=float, default=1e-4)
    parser.add_argument("--boundary-consist", type=float, default=1e-6)
    parser.add_argument("--keep-intersections", action="store_true")
    parser.add_argument("--keep-stretched-faces", action="store_true")
    parser.add_argument("--fillet-radius-fraction", type=float, default=0.0)
    parser.add_argument("--fillet-gradient-quantile", type=float, default=98.5)
    parser.add_argument(
        "--max-depth-width-fraction",
        type=float,
        default=0.0,
        help=(
            "Optionally compress the parametric depth prior so its robust front-depth span "
            "does not exceed this fraction of the visible subject width. Zero preserves "
            "the original ECON/ICON behavior."
        ),
    )
    parser.add_argument(
        "--depth-repair-radius-fraction",
        type=float,
        default=0.0,
        help=(
            "Optionally replace only anomalous screen-space depth jumps with masked, "
            "multi-pass Gaussian ramps. The radius is a fraction of the normal-map size; "
            "zero preserves the integrated d-BiNI surface exactly."
        ),
    )
    parser.add_argument(
        "--depth-repair-gradient-multiplier",
        type=float,
        default=6.0,
        help=(
            "Mark a local depth jump as anomalous when it exceeds this multiple of the "
            "robust depth span divided by the visible subject width in pixels."
        ),
    )
    parser.add_argument("--depth-repair-passes", type=int, default=3)
    return parser.parse_args()


def write_depth_preview(depth, output_path):
    valid = np.isfinite(depth)
    preview = np.zeros(depth.shape, dtype=np.uint8)
    if valid.any():
        low, high = np.percentile(depth[valid], [1.0, 99.0])
        if high > low:
            normalized = np.clip((depth - low) / (high - low), 0.0, 1.0)
            preview[valid] = np.round((1.0 - normalized[valid]) * 255.0).astype(np.uint8)
    Image.fromarray(preview, mode="L").save(output_path)


def repair_depth_discontinuities(
    depth: np.ndarray,
    radius: int,
    gradient_multiplier: float,
    passes: int,
) -> tuple[np.ndarray, dict]:
    """Turn unsupported pixel-to-pixel Z jumps into localized smooth 2.5D ramps."""

    repaired = np.asarray(depth, dtype=np.float32).copy()
    valid = np.isfinite(repaired)
    rows, columns = np.where(valid)
    if radius <= 0 or passes <= 0 or not len(columns):
        return repaired, {
            "enabled": False,
            "radius_px": int(radius),
            "passes": int(passes),
        }

    subject_width_px = max(int(columns.max() - columns.min()), 1)
    depth_low, depth_high = np.percentile(repaired[valid], [1.0, 99.0])
    robust_span = float(depth_high - depth_low)
    nominal_step = robust_span / subject_width_px
    threshold = max(float(nominal_step * gradient_multiplier), 1e-8)
    kernel_size = radius * 2 + 1
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
    sigma = max(radius * 0.5, 0.5)
    pass_stats = []

    for pass_index in range(passes):
        gradient = np.zeros_like(repaired, dtype=np.float32)
        horizontal_valid = valid[:, 1:] & valid[:, :-1]
        horizontal = np.abs(repaired[:, 1:] - repaired[:, :-1])
        gradient[:, 1:][horizontal_valid] = np.maximum(
            gradient[:, 1:][horizontal_valid], horizontal[horizontal_valid]
        )
        gradient[:, :-1][horizontal_valid] = np.maximum(
            gradient[:, :-1][horizontal_valid], horizontal[horizontal_valid]
        )
        vertical_valid = valid[1:, :] & valid[:-1, :]
        vertical = np.abs(repaired[1:, :] - repaired[:-1, :])
        gradient[1:, :][vertical_valid] = np.maximum(
            gradient[1:, :][vertical_valid], vertical[vertical_valid]
        )
        gradient[:-1, :][vertical_valid] = np.maximum(
            gradient[:-1, :][vertical_valid], vertical[vertical_valid]
        )

        anomaly = valid & (gradient > threshold)
        anomaly_count = int(anomaly.sum())
        if anomaly_count == 0:
            break
        band = cv2.dilate(anomaly.astype(np.uint8), kernel).astype(np.float32)
        values = np.where(valid, repaired, 0.0).astype(np.float32)
        weights = valid.astype(np.float32)
        blurred_values = cv2.GaussianBlur(values, (0, 0), sigmaX=sigma, sigmaY=sigma)
        blurred_weights = cv2.GaussianBlur(weights, (0, 0), sigmaX=sigma, sigmaY=sigma)
        smoothed = blurred_values / np.maximum(blurred_weights, 1e-8)
        blend = cv2.GaussianBlur(band, (0, 0), sigmaX=sigma, sigmaY=sigma)
        blend = np.clip(blend, 0.0, 1.0)
        repaired[valid] = (
            repaired[valid] * (1.0 - blend[valid]) + smoothed[valid] * blend[valid]
        )
        pass_stats.append(
            {
                "pass": pass_index + 1,
                "anomalous_pixels": anomaly_count,
                "band_pixels": int((band > 0.0).sum()),
            }
        )

    return repaired, {
        "enabled": True,
        "radius_px": int(radius),
        "passes_requested": int(passes),
        "passes_completed": len(pass_stats),
        "gradient_multiplier": float(gradient_multiplier),
        "gradient_threshold": float(threshold),
        "nominal_depth_step": float(nominal_step),
        "robust_depth_span_before": robust_span,
        "pass_stats": pass_stats,
    }


def main():
    args = parse_arguments()
    input_dir = args.input_dir.resolve()
    raw_dir = args.raw_dir.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    payload_paths = sorted(input_dir.glob("*_icon_BNI.npy"))
    if not payload_paths:
        raise FileNotFoundError(f"No *_icon_BNI.npy payloads found in {input_dir}")

    device = torch.device(args.device)
    first_payload = np.load(payload_paths[0], allow_pickle=True).item()
    image_size = max(first_payload["mask"].shape)
    fillet_radius = max(1, round(image_size * args.fillet_radius_fraction)) if args.fillet_radius_fraction > 0 else 0
    depth_repair_radius = (
        max(1, round(image_size * args.depth_repair_radius_fraction))
        if args.depth_repair_radius_fraction > 0
        else 0
    )
    config = {
        "k": args.k,
        "lambda1": args.lambda1,
        "boundary_consist": args.boundary_consist,
        "cut_intersection": not args.keep_intersections,
        "remove_stretched": not args.keep_stretched_faces,
        "fillet_radius": fillet_radius,
        "fillet_gradient_quantile": args.fillet_gradient_quantile,
    }
    all_stats = {}

    for payload_path in payload_paths:
        suffix = "_icon_BNI.npy"
        subject = payload_path.name[: -len(suffix)]
        raw_path = raw_dir / f"{subject}_icon_front_raw.npz"
        if not raw_path.exists():
            raise FileNotFoundError(f"Missing raw ICON tensor payload: {raw_path}")

        bni_payload = np.load(payload_path, allow_pickle=True).item()
        depth_prior_scale = 1.0
        depth_prior_span = None
        depth_prior_target = None
        if args.max_depth_width_fraction > 0.0:
            normal_mask = np.asarray(bni_payload["mask"], dtype=bool)
            depth_mask = np.asarray(bni_payload["depth_mask"], dtype=bool)
            rows, columns = np.where(normal_mask)
            if not len(columns) or not depth_mask.any():
                raise RuntimeError(f"Cannot measure the depth prior for {subject}")
            subject_width = float(columns.max() - columns.min()) / 256.0
            valid_front_depth = np.asarray(bni_payload["depth_F"], dtype=np.float32)[depth_mask]
            depth_low, depth_high = np.percentile(valid_front_depth, [1.0, 99.0])
            depth_prior_span = float(depth_high - depth_low)
            depth_prior_target = float(subject_width * args.max_depth_width_fraction)
            if depth_prior_span > depth_prior_target > 0.0:
                depth_prior_scale = depth_prior_target / depth_prior_span
                bni_payload = dict(bni_payload)
                bni_payload["depth_F"] = (
                    np.asarray(bni_payload["depth_F"], dtype=np.float32) * depth_prior_scale
                )
                bni_payload["depth_B"] = (
                    np.asarray(bni_payload["depth_B"], dtype=np.float32) * depth_prior_scale
                )
        raw_payload = np.load(raw_path)
        integrator = BNI(
            dir_path=str(output_dir),
            name=subject,
            BNI_dict=bni_payload,
            cfg=config,
            device=device,
        )
        integrator.extract_surface(False)

        front_mesh = integrator.F_trimesh.copy()
        repaired_depth, depth_repair_stats = repair_depth_discontinuities(
            integrator.F_depth.cpu().numpy(),
            depth_repair_radius,
            args.depth_repair_gradient_multiplier,
            args.depth_repair_passes,
        )
        if depth_repair_stats["enabled"]:
            repaired_mask = np.isfinite(repaired_depth)
            if int(repaired_mask.sum()) != len(front_mesh.vertices):
                raise RuntimeError(
                    f"Depth/mesh ordering changed for {subject}: "
                    f"{int(repaired_mask.sum())} depth pixels != {len(front_mesh.vertices)} vertices"
                )
            front_mesh.vertices[:, 2] = repaired_depth[repaired_mask]
            integrator.F_depth = torch.from_numpy(repaired_depth)
        image_tensor = torch.from_numpy(raw_payload["image"]).unsqueeze(0).float().to(device)
        colors = query_color(
            torch.from_numpy(front_mesh.vertices).float(),
            torch.from_numpy(front_mesh.faces).long(),
            image_tensor,
            device=device,
            paint_normal=False,
        )
        front_mesh.visual.vertex_colors = colors.numpy().astype(np.uint8)

        obj_path = output_dir / f"{subject}_icon_front_bni.obj"
        glb_path = output_dir / f"{subject}_icon_front_bni.glb"
        depth_path = output_dir / f"{subject}_icon_front_depth.npy"
        preview_path = output_dir / f"{subject}_icon_front_depth.png"
        front_mesh.export(obj_path)
        front_mesh.export(glb_path)
        np.save(depth_path, integrator.F_depth.cpu().numpy())
        write_depth_preview(integrator.F_depth.cpu().numpy(), preview_path)

        all_stats[subject] = {
            "vertices": int(len(front_mesh.vertices)),
            "triangles": int(len(front_mesh.faces)),
            "components": int(len(front_mesh.split(only_watertight=False))),
            "bounds": front_mesh.bounds.tolist(),
            "extents": front_mesh.extents.tolist(),
            "watertight": bool(front_mesh.is_watertight),
            "source_payload": str(payload_path),
            "raw_tensor_payload": str(raw_path),
            "depth_prior": {
                "robust_input_span": depth_prior_span,
                "target_span": depth_prior_target,
                "applied_scale": float(depth_prior_scale),
                "max_depth_width_fraction": float(args.max_depth_width_fraction),
            },
            "depth_discontinuity_repair": depth_repair_stats,
        }
        print(
            f"[ICON front d-BiNI] {subject}: "
            f"{len(front_mesh.vertices):,} vertices / {len(front_mesh.faces):,} triangles"
        )

    with (output_dir / "icon_front_bni_stats.json").open("w", encoding="utf-8") as handle:
        json.dump({"config": config, "subjects": all_stats}, handle, indent=2)


if __name__ == "__main__":
    main()
