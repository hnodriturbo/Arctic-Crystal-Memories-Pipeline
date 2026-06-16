"""
enhance.py — AI face restoration and color enhancement for the K9 Crystal Pipeline.
Path: pipeline/code/enhance.py

Called by the Next.js web interface via POST /api/process with operation="enhance".
Supports three independent engines — choose one per run, any order, no prerequisites.

Engines:
  gfpgan (default)  — face restoration, natural skin tones (group shots)
  codeformer        — face restoration, sharper results, fidelity slider (0=max AI, 1=faithful)
  pillow            — brightness/contrast/sharpness/color, no AI, instant

CLI:  python code/enhance.py --file <name> [--engine gfpgan] [--fidelity 0.7]
"""

import argparse
from pathlib import Path

import cv2
import numpy as np
import torch
from PIL import Image, ImageEnhance

PIPELINE_ROOT = Path(__file__).resolve().parent.parent
INPUT_DIR = PIPELINE_ROOT / "input"
OUTPUT_DIR = PIPELINE_ROOT / "output/enhanced"
MODELS_DIR = PIPELINE_ROOT / "models"

GFPGAN_URL = "https://github.com/TencentARC/GFPGAN/releases/download/v1.3.4/GFPGANv1.4.pth"
CODEFORMER_URL = "https://github.com/sczhou/CodeFormer/releases/download/v0.1.0/codeformer.pth"

ENGINES = ["gfpgan", "codeformer", "pillow"]


def enhance_with_gfpgan(img_bgr: np.ndarray, device: str) -> np.ndarray:
    from gfpgan import GFPGANer

    model_dir = MODELS_DIR / "gfpgan"
    model_dir.mkdir(parents=True, exist_ok=True)
    model_path = model_dir / "GFPGANv1.4.pth"

    restorer = GFPGANer(
        model_path=str(model_path) if model_path.exists() else GFPGAN_URL,
        upscale=1,
        arch="clean",
        channel_multiplier=2,
        bg_upsampler=None,
    )
    _, _, restored_img = restorer.enhance(
        img_bgr,
        has_aligned=False,
        only_center_face=False,
        paste_back=True,
    )
    if restored_img is None:
        raise RuntimeError("GFPGAN returned no output")
    return restored_img


def enhance_with_codeformer(img_bgr: np.ndarray, fidelity: float, device: str) -> np.ndarray:
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from basicsr.utils import img2tensor, tensor2img
    from basicsr.utils.download_util import load_file_from_url
    from basicsr.utils.registry import ARCH_REGISTRY
    from torchvision.transforms.functional import normalize as tv_normalize
    from facexlib.utils.face_restoration_helper import FaceRestoreHelper
    import codeformer_arch  # noqa: F401 — registers CodeFormer into ARCH_REGISTRY

    model_dir = MODELS_DIR / "codeformer"
    model_dir.mkdir(parents=True, exist_ok=True)
    model_path = model_dir / "codeformer.pth"

    if not model_path.exists():
        print("  Downloading CodeFormer weights...")
        load_file_from_url(CODEFORMER_URL, model_dir=str(model_dir),
                           progress=True, file_name="codeformer.pth")

    net = ARCH_REGISTRY.get('CodeFormer')(
        dim_embd=512, codebook_size=1024, n_head=8, n_layers=9,
        connect_list=['32', '64', '128', '256'],
    ).to(device)
    checkpoint = torch.load(str(model_path), map_location=device)
    net.load_state_dict(checkpoint['params_ema'])
    net.eval()

    face_helper = FaceRestoreHelper(
        upscale_factor=1,
        face_size=512,
        crop_ratio=(1, 1),
        det_model='retinaface_resnet50',
        save_ext='png',
        use_parse=True,
        device=device,
    )
    face_helper.read_image(img_bgr)
    num_faces = face_helper.get_face_landmarks_5(only_center_face=False, resize=640, eye_dist_threshold=5)
    print(f"  CodeFormer: {num_faces} face(s) detected")
    face_helper.align_warp_face()

    for cropped_face in face_helper.cropped_faces:
        face_t: torch.Tensor = img2tensor(cropped_face / 255., bgr2rgb=True, float32=True)  # type: ignore[assignment]
        tv_normalize(face_t, [0.5, 0.5, 0.5], [0.5, 0.5, 0.5], inplace=True)
        face_t = face_t.unsqueeze(0).to(device)
        with torch.no_grad():
            output = net(face_t, w=fidelity, adain=True)[0]
            restored: np.ndarray = tensor2img(output, rgb2bgr=True, min_max=(-1, 1))  # type: ignore[assignment]
        torch.cuda.empty_cache()
        face_helper.add_restored_face(restored.astype('uint8'))

    face_helper.get_inverse_affine(None)
    restored_img = face_helper.paste_faces_to_input_image(upsample_img=None)
    return restored_img


def enhance_with_pillow(img: Image.Image, brightness: float, contrast: float,
                        sharpness: float, color: float) -> Image.Image:
    img = ImageEnhance.Brightness(img).enhance(brightness)
    img = ImageEnhance.Contrast(img).enhance(contrast)
    img = ImageEnhance.Sharpness(img).enhance(sharpness)
    img = ImageEnhance.Color(img).enhance(color)
    return img


def process(src: Path, engine: str, fidelity: float,
            brightness: float, contrast: float, sharpness: float,
            color: float, device: str) -> None:
    img = Image.open(src).convert("RGBA")
    print(f"  {src.name} [{engine}]")

    if engine == "pillow":
        result_img: Image.Image = enhance_with_pillow(img, brightness, contrast, sharpness, color)
    else:
        # AI engines work on RGB — split and reattach alpha
        rgb = np.array(img.convert("RGB"))
        alpha = np.array(img.split()[-1])
        bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

        if engine == "gfpgan":
            out_bgr = enhance_with_gfpgan(bgr, device)
        elif engine == "codeformer":
            out_bgr = enhance_with_codeformer(bgr, fidelity, device)
        else:
            raise ValueError(f"Unknown engine: {engine}")

        out_rgb = cv2.cvtColor(out_bgr, cv2.COLOR_BGR2RGB)
        oh, ow = out_rgb.shape[:2]
        alpha_r = cv2.resize(alpha, (ow, oh), interpolation=cv2.INTER_LANCZOS4)
        combined = np.dstack([out_rgb, alpha_r]).astype(np.uint8)
        result_img = Image.fromarray(combined, "RGBA")

    out = OUTPUT_DIR / f"{src.stem}-enhanced.png"
    result_img.save(out, "PNG")
    print(f"  -> {out}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", help="Filename in input/ (or full path)")
    parser.add_argument("--engine", default="gfpgan", choices=ENGINES)
    parser.add_argument("--fidelity", type=float, default=0.7,
                        help="CodeFormer fidelity (0.0=max enhance, 1.0=max faithful)")
    parser.add_argument("--brightness", type=float, default=1.0)
    parser.add_argument("--contrast", type=float, default=1.0)
    parser.add_argument("--sharpness", type=float, default=1.0)
    parser.add_argument("--color", type=float, default=1.0)
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
        targets = [p for p in targets if "_enhanced" not in p.stem]

    if not targets:
        print("No images found.")
        return

    for src in targets:
        process(src, args.engine, args.fidelity,
                args.brightness, args.contrast, args.sharpness,
                args.color, device)

    print("Done.")


if __name__ == "__main__":
    main()
