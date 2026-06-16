"""
remove_bg.py — Background removal for the K9 Crystal Pipeline.
Path: pipeline/code/remove_bg.py

Called by the Next.js web interface via POST /api/process with operation="remove_bg".
Outputs RGBA PNG with transparent background to output/bg_removed/.
Runs independently — no upscale or enhance step required first.

Engines:
  rembg (default)  — GPU-accelerated, multiple sub-models
    models: isnet-general-use (default) | birefnet-portrait | birefnet-general |
            u2net_human_seg | u2net
  carvekit         — trimap-based, best edge quality (slower)

CLI:  python code/remove_bg.py --file <name> [--engine rembg] [--model isnet-general-use]
"""

import argparse
from pathlib import Path

from PIL import Image

PIPELINE_ROOT = Path(__file__).resolve().parent.parent
INPUT_DIR = PIPELINE_ROOT / "input"
OUTPUT_DIR = PIPELINE_ROOT / "output/bg_removed"

# rembg sub-models in order of general quality for portrait work
REMBG_MODELS = [
    "birefnet-portrait",    # best for people
    "birefnet-general",     # best general
    "isnet-general-use",    # good general
    "u2net_human_seg",      # people-specific
    "u2net",                # default general
]

ENGINES = ["rembg", "carvekit"]


def remove_with_rembg(img: Image.Image, model: str) -> Image.Image:
    from rembg import remove, new_session
    session = new_session(model)
    result = remove(img, session=session)
    if isinstance(result, Image.Image):
        return result
    import numpy as np
    if isinstance(result, np.ndarray):
        return Image.fromarray(result).convert("RGBA")
    import io
    return Image.open(io.BytesIO(result)).convert("RGBA")


def remove_with_carvekit(img: Image.Image) -> Image.Image:
    # carvekit: trimap-based, best edge quality, slow
    # pip install carvekit
    from carvekit.api.high import HiInterface
    interface = HiInterface(
        object_type="hairs-like",
        batch_size_seg=1,
        batch_size_matting=1,
        device="cuda",
        seg_mask_size=640,
        matting_mask_size=2048,
    )
    result = interface([img])
    return result[0]


def process(src: Path, engine: str, model: str) -> None:
    img = Image.open(src).convert("RGBA")
    print(f"  {src.name} [{engine}{'/' + model if engine == 'rembg' else ''}]")

    if engine == "rembg":
        result = remove_with_rembg(img, model)
    elif engine == "carvekit":
        result = remove_with_carvekit(img)
    else:
        raise ValueError(f"Unknown engine: {engine}")

    out = OUTPUT_DIR / f"{src.stem}-bg-removed.png"
    result.save(out, "PNG")
    print(f"  -> {out}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", help="Filename in input/ (or full path)")
    parser.add_argument("--engine", default="rembg", choices=ENGINES)
    parser.add_argument("--model", default="isnet-general-use",
                        help="rembg sub-model (only used with --engine rembg)")
    parser.add_argument("--input-dir", default=str(INPUT_DIR))
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    input_dir = Path(args.input_dir)

    if args.file:
        p = Path(args.file)
        targets = [p if p.is_absolute() else input_dir / p]
    else:
        exts = ("*.png", "*.jpg", "*.jpeg", "*.webp", "*.tiff", "*.bmp")
        targets = sorted(p for ext in exts for p in input_dir.glob(ext))
        targets = [p for p in targets if "-bg-removed" not in p.stem]

    if not targets:
        print("No images found.")
        return

    for src in targets:
        process(src, args.engine, args.model)

    print("Done.")


if __name__ == "__main__":
    main()
