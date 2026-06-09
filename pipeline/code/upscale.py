"""
upscale.py — AI upscale for the K9 Crystal Pipeline.
Path: pipeline/code/upscale.py

Called by the Next.js web interface via POST /api/process with operation="upscale".
Scales the long edge to TARGET_LONG_EDGE (default 1800px) while preserving aspect
ratio and alpha channel. Skips images already at or above the target size.

Engines: realesrgan (default) | realesrgan_face | lanczos (no AI, instant)
CLI:  python code/upscale.py --file <name> [--engine realesrgan] [--target 1800]
"""

import argparse
import shutil
from pathlib import Path

import cv2
import numpy as np
import torch
from PIL import Image

PIPELINE_ROOT = Path(__file__).resolve().parent.parent
INPUT_DIR = PIPELINE_ROOT / "input"
OUTPUT_DIR = PIPELINE_ROOT / "output/upscaled"
MODELS_DIR = PIPELINE_ROOT / "models"
TARGET_LONG_EDGE = 1800

REALESRGAN_URL = "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth"
REALESRGAN_FACE_URL = "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.2.4/RealESRGAN_x4plus_netD.pth"

ENGINES = ["realesrgan", "realesrgan_face", "swinir", "lanczos"]


def _build_realesrgan(model_name: str, url: str, device: str):
    from basicsr.archs.rrdbnet_arch import RRDBNet
    from realesrgan import RealESRGANer

    model_dir = MODELS_DIR / "realesrgan"
    model_dir.mkdir(parents=True, exist_ok=True)
    model_path = model_dir / f"{model_name}.pth"

    model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64,
                    num_block=23, num_grow_ch=32, scale=4)
    return RealESRGANer(
        scale=4,
        model_path=str(model_path) if model_path.exists() else url,
        model=model,
        tile=512,
        tile_pad=10,
        pre_pad=0,
        half=device == "cuda",
        device=device,
    )


def upscale_with_realesrgan(bgr: np.ndarray, device: str) -> np.ndarray:
    up = _build_realesrgan("RealESRGAN_x4plus", REALESRGAN_URL, device)
    result, _ = up.enhance(bgr, outscale=None)
    return result


def upscale_with_realesrgan_face(bgr: np.ndarray, device: str) -> np.ndarray:
    up = _build_realesrgan("RealESRGAN_x4plus_netD", REALESRGAN_FACE_URL, device)
    result, _ = up.enhance(bgr, outscale=None)
    return result


def upscale_with_swinir(bgr: np.ndarray, device: str) -> np.ndarray:
    # Requires: pip install spandrel
    # SwinIR is a transformer-based upscaler — very sharp edges, slower than RealESRGAN
    raise NotImplementedError(
        "SwinIR engine not yet implemented. Install spandrel and wire in the model loader."
    )


def upscale_with_lanczos(img_rgba: Image.Image, target: int) -> Image.Image:
    w, h = img_rgba.size
    scale = target / max(w, h)
    new_w = int(round(w * scale))
    new_h = int(round(h * scale))
    return img_rgba.resize((new_w, new_h), Image.Resampling.LANCZOS)


def process(src: Path, engine: str, target: int, device: str) -> None:
    img = Image.open(src).convert("RGBA")
    w, h = img.size

    if max(w, h) >= target:
        out = OUTPUT_DIR / f"{src.stem}_upscaled.png"
        shutil.copy2(src, out)
        print(f"  skip {src.name} — already {w}x{h}, copied as-is to output")
        return

    print(f"  {src.name} {w}x{h} [{engine}]")

    if engine == "lanczos":
        result_img = upscale_with_lanczos(img, target)
    else:
        # Split alpha — RealESRGAN/SwinIR are RGB-only models
        rgb = np.array(img.convert("RGB"))
        alpha = np.array(img.split()[-1])
        bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

        if engine == "realesrgan":
            up_bgr = upscale_with_realesrgan(bgr, device)
        elif engine == "realesrgan_face":
            up_bgr = upscale_with_realesrgan_face(bgr, device)
        elif engine == "swinir":
            up_bgr = upscale_with_swinir(bgr, device)
        else:
            raise ValueError(f"Unknown engine: {engine}")

        uh, uw = up_bgr.shape[:2]
        alpha_up = cv2.resize(alpha, (uw, uh), interpolation=cv2.INTER_LANCZOS4)
        up_rgb = cv2.cvtColor(up_bgr, cv2.COLOR_BGR2RGB)
        combined = np.dstack([up_rgb, alpha_up]).astype(np.uint8)

        # Scale down to target if 4x overshot
        rh, rw = combined.shape[:2]
        if max(rw, rh) > target:
            scale = target / max(rw, rh)
            nw, nh = int(round(rw * scale)), int(round(rh * scale))
            combined = cv2.resize(combined, (nw, nh), interpolation=cv2.INTER_LANCZOS4)

        result_img = Image.fromarray(combined, "RGBA")

    out = OUTPUT_DIR / f"{src.stem}_upscaled.png"
    result_img.save(out, "PNG")
    fw, fh = result_img.size
    print(f"  -> {out}  ({fw}x{fh})")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", help="Filename in input/ (or full path)")
    parser.add_argument("--engine", default="realesrgan", choices=ENGINES)
    parser.add_argument("--target", type=int, default=TARGET_LONG_EDGE,
                        help="Target long edge in pixels (default 1800)")
    parser.add_argument("--input-dir", default=str(INPUT_DIR))
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}")

    input_dir = Path(args.input_dir)

    if args.file:
        p = Path(args.file)
        targets = [p if p.is_absolute() else input_dir / p]
    else:
        exts = ("*.png", "*.jpg", "*.jpeg", "*.webp", "*.tiff", "*.bmp")
        targets = sorted(p for ext in exts for p in input_dir.glob(ext))
        targets = [p for p in targets if "_upscaled" not in p.stem]

    if not targets:
        print("No images found.")
        return

    for src in targets:
        process(src, args.engine, args.target, device)

    print("Done.")


if __name__ == "__main__":
    main()
