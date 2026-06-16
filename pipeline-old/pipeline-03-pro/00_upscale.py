"""
00_upscale.py — AI upscale input images to 1800px long edge using Real-ESRGAN.

Only upscales images whose long edge is below TARGET_LONG_EDGE.
Alpha channel is preserved. Output written to input/ alongside the originals
as <name>_upscaled.png.

Usage:
    python 00_upscale.py                     # upscale all PNGs in input/
    python 00_upscale.py --file image_01.png # upscale a specific file
"""

import argparse
import os
from pathlib import Path

import cv2
import numpy as np
import torch
from basicsr.archs.rrdbnet_arch import RRDBNet
from realesrgan import RealESRGANer
from PIL import Image

INPUT_DIR = Path("input")
TARGET_LONG_EDGE = 1800
MODEL_NAME = "RealESRGAN_x4plus"
MODEL_URL = "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth"
WEIGHTS_DIR = Path("models/realesrgan")


def build_upsampler(device: str) -> RealESRGANer:
    WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)
    model_path = WEIGHTS_DIR / f"{MODEL_NAME}.pth"

    model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64,
                    num_block=23, num_grow_ch=32, scale=4)

    upsampler = RealESRGANer(
        scale=4,
        model_path=str(model_path) if model_path.exists() else MODEL_URL,
        model=model,
        tile=512,
        tile_pad=10,
        pre_pad=0,
        half=device == "cuda",
        device=device,
    )
    return upsampler


def upscale_image(src: Path, upsampler: RealESRGANer) -> None:
    img = Image.open(src).convert("RGBA")
    w, h = img.size
    long_edge = max(w, h)

    if long_edge >= TARGET_LONG_EDGE:
        print(f"  skip {src.name} — already {w}x{h}")
        return

    # Split alpha before passing to Real-ESRGAN (RGB model)
    rgb = np.array(img.convert("RGB"))
    alpha = np.array(img.split()[-1])  # L mode

    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    upscaled_bgr, _ = upsampler.enhance(bgr, outscale=None)

    # Upscale alpha with same ratio using bicubic
    uh, uw = upscaled_bgr.shape[:2]
    alpha_up = cv2.resize(alpha, (uw, uh), interpolation=cv2.INTER_LANCZOS4)

    upscaled_rgb = cv2.cvtColor(upscaled_bgr, cv2.COLOR_BGR2RGB)
    result = np.dstack([upscaled_rgb, alpha_up]).astype(np.uint8)

    # Resize down to TARGET_LONG_EDGE if the 4x result overshoots
    rh, rw = result.shape[:2]
    if max(rw, rh) > TARGET_LONG_EDGE:
        scale = TARGET_LONG_EDGE / max(rw, rh)
        new_w = int(round(rw * scale))
        new_h = int(round(rh * scale))
        result = cv2.resize(result, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)

    out_path = src.with_stem(src.stem + "_upscaled")
    Image.fromarray(result, "RGBA").save(out_path, "PNG")
    fh, fw = result.shape[:2]
    print(f"  {src.name} {w}x{h} -> {fw}x{fh}  saved: {out_path.name}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", help="Specific filename in input/ to upscale")
    args = parser.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}")

    print("Loading Real-ESRGAN model...")
    upsampler = build_upsampler(device)

    if args.file:
        targets = [INPUT_DIR / args.file]
    else:
        targets = sorted(INPUT_DIR.glob("*.png"))
        # Skip already-upscaled outputs
        targets = [p for p in targets if "_upscaled" not in p.stem]

    if not targets:
        print("No PNG files found in input/")
        return

    for src in targets:
        print(f"Processing {src.name}...")
        upscale_image(src, upsampler)

    print("Done.")


if __name__ == "__main__":
    main()
