"""
File: converter/2.5D-pipeline/code/detail_refine.py
Purpose:
 - Convert MoGe surface normals into a conservative medium/high-frequency
   height correction and fuse it into an already refined 16-bit depth map.
 - Preserve macro scene depth while recovering subtle surface form such as
   eyelids, facial planes, fur direction, cloth folds and object relief.

This stage deliberately does not infer shape from RGB brightness. Colour,
make-up and shadows are not geometry. It only borrows orientation predicted by
the geometry model and caps the physical correction before meshing.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))

from utils import fail, prepare_output, report  # noqa: E402


def read_depth(path: Path) -> np.ndarray:
    """Read a pipeline 16-bit bright=near depth map as 0..1 float data."""
    with Image.open(path) as image:
        image.load()
        plane = np.asarray(image, dtype=np.float32)
    if plane.ndim != 2:
        fail(f"Depth map must be one-channel, got shape {plane.shape} from {path}.")
    maximum = 65535.0 if plane.max(initial=0.0) > 255.0 else 255.0
    return np.clip(plane / maximum, 0.0, 1.0)


def read_normals(path: Path, size: tuple[int, int]) -> np.ndarray:
    """Decode MoGe's RGB normal output from 0..255 back to unit vectors."""
    with Image.open(path) as image:
        image.load()
        if image.size != size:
            fail(f"Normal size {image.size} does not match depth size {size}.")
        normals = np.asarray(image.convert("RGB"), dtype=np.float32) / 127.5 - 1.0
    lengths = np.linalg.norm(normals, axis=2, keepdims=True)
    return normals / np.maximum(lengths, 1e-6)


def read_weight(path: Path | None, size: tuple[int, int]) -> np.ndarray:
    """Load an optional subject mask and soften its boundary to prevent seams."""
    if path is None:
        return np.ones((size[1], size[0]), dtype=np.float32)
    with Image.open(path) as image:
        image.load()
        if image.size != size:
            fail(f"Mask size {image.size} does not match depth size {size}.")
        mask = np.asarray(image.convert("L"), dtype=np.float32) / 255.0
    # The correction should be zero before the uncertain silhouette, not on it.
    inset = cv2.erode((mask > 0.35).astype(np.uint8), np.ones((5, 5), np.uint8))
    return cv2.GaussianBlur(inset.astype(np.float32), (0, 0), sigmaX=3.0, sigmaY=3.0)


def integrate_normals(normals: np.ndarray, slope_limit: float) -> np.ndarray:
    """Integrate a normal field into the closest height field in Fourier space."""
    nx, ny, nz = (normals[..., index] for index in range(3))
    # MoGe camera-facing normals point toward -Z. Flip that convention to the
    # +Z height-field normal N=(-dz/dx,-dz/dy,1) before deriving slopes.
    denominator = np.maximum(np.abs(nz), 0.16)
    slope_x = np.clip(nx / denominator, -slope_limit, slope_limit)
    slope_y = np.clip(ny / denominator, -slope_limit, slope_limit)

    rows, columns = slope_x.shape
    frequency_x = 2.0 * np.pi * np.fft.fftfreq(columns)
    frequency_y = 2.0 * np.pi * np.fft.fftfreq(rows)
    omega_x, omega_y = np.meshgrid(frequency_x, frequency_y)
    denominator_frequency = omega_x * omega_x + omega_y * omega_y

    transform_x = np.fft.fft2(slope_x)
    transform_y = np.fft.fft2(slope_y)
    height_transform = np.zeros_like(transform_x, dtype=np.complex128)
    valid = denominator_frequency > 0
    height_transform[valid] = (
        -1j * omega_x[valid] * transform_x[valid]
        - 1j * omega_y[valid] * transform_y[valid]
    ) / denominator_frequency[valid]
    return np.fft.ifft2(height_transform).real.astype(np.float32)


def band_limited_detail(height: np.ndarray, fine_sigma: float, coarse_sigma: float) -> np.ndarray:
    """Retain useful relief-scale shape while rejecting pixel noise and macro warp."""
    fine = cv2.GaussianBlur(height, (0, 0), sigmaX=fine_sigma, sigmaY=fine_sigma)
    coarse = cv2.GaussianBlur(height, (0, 0), sigmaX=coarse_sigma, sigmaY=coarse_sigma)
    return fine - coarse


def edge_guard(depth: np.ndarray, percentile: float) -> np.ndarray:
    """Suppress normal corrections at large depth jumps where ringing causes walls."""
    gradient_x = cv2.Sobel(depth, cv2.CV_32F, 1, 0, ksize=3)
    gradient_y = cv2.Sobel(depth, cv2.CV_32F, 0, 1, ksize=3)
    magnitude = np.hypot(gradient_x, gradient_y)
    threshold = float(np.percentile(magnitude, percentile))
    if threshold <= 1e-8:
        return np.ones_like(depth, dtype=np.float32)
    guard = 1.0 - np.clip(magnitude / (threshold * 2.0), 0.0, 1.0)
    return cv2.GaussianBlur(guard, (0, 0), sigmaX=1.5, sigmaY=1.5)


def robust_scale(detail: np.ndarray, weight: np.ndarray, percentile: float) -> tuple[np.ndarray, float]:
    """Scale symmetrically so outliers cannot consume the allowed micro-depth."""
    sample = np.abs(detail[weight > 0.25])
    if sample.size == 0:
        fail("Detail mask contains no usable pixels.")
    scale = float(np.percentile(sample, percentile))
    if scale <= 1e-8:
        fail("Normal map produced a flat detail field.")
    return np.clip(detail / scale, -1.0, 1.0), scale


def save_qa(aux_output: Path, before: np.ndarray, after: np.ndarray, detail: np.ndarray) -> None:
    """Write a readable three-panel image for every refinement batch."""
    aux_output.mkdir(parents=True, exist_ok=True)
    before_u8 = (np.clip(before, 0.0, 1.0) * 255).astype(np.uint8)
    after_u8 = (np.clip(after, 0.0, 1.0) * 255).astype(np.uint8)
    positive = np.clip(detail, 0.0, 1.0)
    negative = np.clip(-detail, 0.0, 1.0)
    heat = np.zeros((*detail.shape, 3), dtype=np.uint8)
    heat[..., 0] = (positive * 255).astype(np.uint8)
    heat[..., 2] = (negative * 255).astype(np.uint8)
    heat[..., 1] = ((1.0 - np.maximum(positive, negative)) * 44).astype(np.uint8)
    panel = np.concatenate(
        [
            np.repeat(before_u8[..., None], 3, axis=2),
            np.repeat(after_u8[..., None], 3, axis=2),
            heat,
        ],
        axis=1,
    )
    Image.fromarray(panel, mode="RGB").save(aux_output / "before-after-microdetail.png")
    preview = ((detail * 0.5 + 0.5).clip(0, 1) * 255).astype(np.uint8)
    Image.fromarray(preview, mode="L").save(aux_output / "microdetail-height.png")


def main() -> int:
    parser = argparse.ArgumentParser(description="Fuse MoGe normals into fine relief depth.")
    parser.add_argument("--depth", required=True, type=Path, help="Refined 16-bit bright=near depth map.")
    parser.add_argument("--normal", required=True, type=Path, help="MoGe RGB normal.png.")
    parser.add_argument("--output", required=True, type=Path, help="Final 16-bit bright=near depth map.")
    parser.add_argument("--mask", type=Path, help="Optional MoGe/subject mask.")
    parser.add_argument("--aux-output", type=Path, help="QA image folder.")
    parser.add_argument("--strength", type=float, default=0.018, help="Maximum added depth range (0..1).")
    parser.add_argument("--fine-sigma", type=float, default=1.2, help="Suppress detail smaller than this pixel sigma.")
    parser.add_argument("--coarse-sigma", type=float, default=24.0, help="Reject macro shape larger than this pixel sigma.")
    parser.add_argument("--slope-limit", type=float, default=3.0)
    parser.add_argument("--scale-percentile", type=float, default=98.5)
    parser.add_argument("--edge-percentile", type=float, default=94.0)
    args = parser.parse_args()

    if not 0.0 <= args.strength <= 0.10:
        fail("--strength must be between 0 and 0.10.")
    if not 0.2 <= args.fine_sigma < args.coarse_sigma:
        fail("--fine-sigma must be >= 0.2 and smaller than --coarse-sigma.")
    if not 0.5 <= args.slope_limit <= 10.0:
        fail("--slope-limit must be between 0.5 and 10.")
    if not 90.0 <= args.scale_percentile <= 100.0:
        fail("--scale-percentile must be between 90 and 100.")
    if not 80.0 <= args.edge_percentile <= 100.0:
        fail("--edge-percentile must be between 80 and 100.")

    depth = read_depth(args.depth)
    size = (depth.shape[1], depth.shape[0])
    normals = read_normals(args.normal, size)
    subject_weight = read_weight(args.mask, size)
    geometry_weight = subject_weight * edge_guard(depth, args.edge_percentile)

    report(f"[detail] integrating normals {size[0]}x{size[1]}")
    integrated = integrate_normals(normals, args.slope_limit)
    band = band_limited_detail(integrated, args.fine_sigma, args.coarse_sigma)
    normalized, raw_scale = robust_scale(band, geometry_weight, args.scale_percentile)
    correction = normalized * geometry_weight * float(args.strength)
    final_depth = np.clip(depth + correction, 0.0, 1.0)

    prepare_output(args.output)
    Image.fromarray((final_depth * 65535).astype(np.uint16)).save(args.output)
    aux_output = args.aux_output or args.output.parent / "detail-refinement"
    save_qa(aux_output, depth, final_depth, correction / max(args.strength, 1e-8))

    metadata = {
        "detail_refinement_complete": True,
        "backend": "moge-normal-fourier-integration",
        "input_depth": str(args.depth),
        "normal": str(args.normal),
        "mask": str(args.mask) if args.mask else None,
        "output": str(args.output),
        "convention": "16-bit PNG, bright = near = raised",
        "settings": {
            "strength": args.strength,
            "fine_sigma": args.fine_sigma,
            "coarse_sigma": args.coarse_sigma,
            "slope_limit": args.slope_limit,
            "scale_percentile": args.scale_percentile,
            "edge_percentile": args.edge_percentile,
        },
        "measured": {
            "raw_detail_scale": raw_scale,
            "mean_absolute_correction": float(np.mean(np.abs(correction))),
            "maximum_absolute_correction": float(np.max(np.abs(correction))),
        },
    }
    sidecar = args.output.with_suffix(".json")
    sidecar.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    report(f"[detail] wrote {args.output}")
    report(f"[detail] wrote {sidecar}")
    report(f"[detail] QA previews {aux_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
