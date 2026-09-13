"""
File: converter/2.5D-pipeline/code/appearance_refine.py
Purpose:
 - Preserve photograph-derived beard, hair, eyelid, wrinkle and skin detail as
   a dedicated monochrome appearance map for crystal-style relief previews.
 - Keep tonal/pigment information separate from physical depth so make-up,
   shadows and beard colour cannot become false geometric bumps.

The resulting PNG is not a printer command file. It is a deterministic visual
and downstream sampling input whose bright/dark structure can later be mapped
to dot density once the real laser calibration is available.
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


def read_photo(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """Return RGB 0..1 data and the source alpha/matte as a separate plane."""
    with Image.open(path) as source:
        source.load()
        rgba = np.asarray(source.convert("RGBA"), dtype=np.float32) / 255.0
    return rgba[..., :3], rgba[..., 3]


def perceptual_luma(rgb: np.ndarray) -> np.ndarray:
    """Use Lab lightness so coloured make-up/hair retain human-visible contrast."""
    rgb_u8 = np.rint(np.clip(rgb, 0.0, 1.0) * 255.0).astype(np.uint8)
    return cv2.cvtColor(rgb_u8, cv2.COLOR_RGB2LAB)[..., 0].astype(np.float32) / 255.0


def robust_tone_range(tone: np.ndarray, alpha: np.ndarray, clip_percent: float) -> np.ndarray:
    """Stretch only foreground percentiles; transparent/black padding cannot steal range."""
    sample = tone[alpha > 0.1]
    if sample.size < 64:
        sample = tone.reshape(-1)
    low, high = np.percentile(sample, [clip_percent, 100.0 - clip_percent])
    if high - low < 1e-6:
        fail("The photograph has no usable tonal range for an appearance map.")
    return np.clip((tone - float(low)) / float(high - low), 0.0, 1.0)


def build_appearance(
    rgb: np.ndarray,
    alpha: np.ndarray,
    illumination_sigma: float,
    detail_fine_sigma: float,
    detail_coarse_sigma: float,
    local_contrast: float,
    detail_strength: float,
    toning: float,
    clip_percent: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Build base lightness, signed micro-detail and final crystal-tone planes."""
    luma = perceptual_luma(rgb)

    illumination = cv2.GaussianBlur(
        luma,
        (0, 0),
        sigmaX=illumination_sigma,
        sigmaY=illumination_sigma,
        borderType=cv2.BORDER_REFLECT,
    )
    fine = cv2.GaussianBlur(
        luma,
        (0, 0),
        sigmaX=detail_fine_sigma,
        sigmaY=detail_fine_sigma,
        borderType=cv2.BORDER_REFLECT,
    )
    coarse = cv2.GaussianBlur(
        luma,
        (0, 0),
        sigmaX=detail_coarse_sigma,
        sigmaY=detail_coarse_sigma,
        borderType=cv2.BORDER_REFLECT,
    )

    broad_local = luma - illumination
    micro_detail = fine - coarse
    enhanced = luma + local_contrast * broad_local + detail_strength * micro_detail
    enhanced = robust_tone_range(enhanced, alpha, clip_percent)

    # Preserve the source face shading while borrowing a controlled amount of
    # the locally enhanced signal. Toning is a contrast slope around middle
    # grey, matching the visible Cockpit3D behaviour more closely than a gamma
    # curve that would wash every skin highlight toward white.
    tone = luma * 0.65 + enhanced * 0.35
    tone = np.clip(0.5 + (tone - 0.5) * toning, 0.0, 1.0)
    tone *= np.clip(alpha, 0.0, 1.0)
    return luma, micro_detail, np.clip(tone, 0.0, 1.0)


def save_outputs(
    output: Path,
    aux_output: Path,
    rgb: np.ndarray,
    alpha: np.ndarray,
    luma: np.ndarray,
    detail: np.ndarray,
    tone: np.ndarray,
) -> None:
    """Write reusable RGBA tone data and a readable three-panel QA image."""
    prepare_output(output)
    tone_u8 = np.rint(tone * 255.0).astype(np.uint8)
    alpha_u8 = np.rint(np.clip(alpha, 0.0, 1.0) * 255.0).astype(np.uint8)
    rgba = np.dstack([tone_u8, tone_u8, tone_u8, alpha_u8])
    Image.fromarray(rgba, mode="RGBA").save(output)

    aux_output.mkdir(parents=True, exist_ok=True)
    foreground = alpha > 0.1
    magnitude = float(np.percentile(np.abs(detail[foreground]), 99.0)) if foreground.any() else 1.0
    detail_preview = np.clip(detail / max(magnitude, 1e-6) * 0.5 + 0.5, 0.0, 1.0)
    Image.fromarray(np.rint(detail_preview * 255.0).astype(np.uint8), mode="L").save(
        aux_output / "appearance-microdetail.png"
    )

    rgb_panel = np.rint(np.clip(rgb, 0.0, 1.0) * 255.0).astype(np.uint8)
    luma_u8 = np.rint(np.clip(luma, 0.0, 1.0) * 255.0).astype(np.uint8)
    luma_panel = np.repeat(luma_u8[..., None], 3, axis=2)
    tone_panel = np.repeat(tone_u8[..., None], 3, axis=2)
    panel = np.concatenate([rgb_panel, luma_panel, tone_panel], axis=1)
    Image.fromarray(panel, mode="RGB").save(aux_output / "rgb-luma-crystal-tone.png")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a crystal-style monochrome appearance map.")
    parser.add_argument("--input", required=True, type=Path, help="Original RGB/RGBA photograph.")
    parser.add_argument("--output", required=True, type=Path, help="RGBA crystal-tone PNG.")
    parser.add_argument("--aux-output", type=Path, help="QA image folder.")
    parser.add_argument("--illumination-sigma", type=float, default=48.0)
    parser.add_argument("--detail-fine-sigma", type=float, default=0.7)
    parser.add_argument("--detail-coarse-sigma", type=float, default=3.2)
    parser.add_argument("--local-contrast", type=float, default=0.55)
    parser.add_argument("--detail-strength", type=float, default=1.35)
    parser.add_argument("--toning", type=float, default=1.8)
    parser.add_argument("--clip-percent", type=float, default=0.5)
    args = parser.parse_args()

    if args.illumination_sigma < 2.0:
        fail("--illumination-sigma must be at least 2 pixels.")
    if not 0.2 <= args.detail_fine_sigma < args.detail_coarse_sigma:
        fail("--detail-fine-sigma must be >= 0.2 and smaller than --detail-coarse-sigma.")
    if not 0.0 <= args.local_contrast <= 3.0:
        fail("--local-contrast must be between 0 and 3.")
    if not 0.0 <= args.detail_strength <= 5.0:
        fail("--detail-strength must be between 0 and 5.")
    if not 0.2 <= args.toning <= 5.0:
        fail("--toning must be between 0.2 and 5.")
    if not 0.0 <= args.clip_percent < 25.0:
        fail("--clip-percent must be between 0 and 25.")

    rgb, alpha = read_photo(args.input)
    report(f"[appearance] source {args.input.name} {rgb.shape[1]}x{rgb.shape[0]}")
    luma, detail, tone = build_appearance(
        rgb,
        alpha,
        args.illumination_sigma,
        args.detail_fine_sigma,
        args.detail_coarse_sigma,
        args.local_contrast,
        args.detail_strength,
        args.toning,
        args.clip_percent,
    )
    aux_output = args.aux_output or args.output.parent / "appearance-refinement"
    save_outputs(args.output, aux_output, rgb, alpha, luma, detail, tone)

    metadata = {
        "appearance_refinement_complete": True,
        "backend": "perceptual-luma-multiscale-detail",
        "input": str(args.input),
        "output": str(args.output),
        "semantics": "monochrome appearance/tonal input; not physical depth and not calibrated laser power",
        "settings": {
            "illumination_sigma": args.illumination_sigma,
            "detail_fine_sigma": args.detail_fine_sigma,
            "detail_coarse_sigma": args.detail_coarse_sigma,
            "local_contrast": args.local_contrast,
            "detail_strength": args.detail_strength,
            "toning": args.toning,
            "clip_percent": args.clip_percent,
        },
        "measured": {
            "foreground_fraction": float(np.mean(alpha > 0.1)),
            "mean_tone": float(np.mean(tone[alpha > 0.1])) if np.any(alpha > 0.1) else 0.0,
            "mean_absolute_microdetail": float(np.mean(np.abs(detail[alpha > 0.1])))
            if np.any(alpha > 0.1)
            else 0.0,
        },
    }
    sidecar = args.output.with_suffix(".json")
    sidecar.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    report(f"[appearance] wrote {args.output}")
    report(f"[appearance] wrote {sidecar}")
    report(f"[appearance] QA previews {aux_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
