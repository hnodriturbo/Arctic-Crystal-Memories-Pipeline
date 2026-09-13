"""
enhance.py — clean a photograph up before it becomes geometry.
Path: converter/image-pipeline/code/enhance.py

Engines:
  auto        GFPGAN on CUDA, Pillow on CPU. Routine VPS jobs stay fast.
  gfpgan      Face restoration. Rebuilds eyes, mouth and skin on an old or
              soft portrait. Runs on CPU when explicitly selected.
  pillow      Brightness, contrast, sharpness and saturation. No GPU, no
              model download, and it never invents a face that was not there.

Why bother when Meshy has its own image_enhancement: because Meshy's pass
optimises for a pleasing render, and this one optimises for the thing that
actually drives geometry - edges the generator can find. Sharpening a soft
photograph here shows up as crisper folds in the mesh.

  python code/enhance.py --input photo.jpg --output better.png
  python code/enhance.py --input photo.jpg --output better.png --engine pillow --sharpness 1.4
"""

from __future__ import annotations

from contextlib import chdir

from PIL import Image, ImageEnhance

from utils import base_parser, fail, prepare_output, report, torch_device

ENGINES = ["auto", "gfpgan", "pillow"]


def enhance_pillow(source: Image.Image, args) -> Image.Image:
    """Straight tone and sharpness adjustment, applied in a fixed order."""
    result = source
    for label, factor, enhancer in (
        ("brightness", args.brightness, ImageEnhance.Brightness),
        ("contrast", args.contrast, ImageEnhance.Contrast),
        ("color", args.color, ImageEnhance.Color),
        ("sharpness", args.sharpness, ImageEnhance.Sharpness),
    ):
        if abs(factor - 1.0) < 1e-6:
            continue
        report(f"  {label} x{factor}")
        result = enhancer(result).enhance(factor)
    return result


def enhance_gfpgan(source: Image.Image, args, device: str) -> Image.Image:
    """
    GFPGAN face restoration.

    Alpha is set aside and put back afterwards - the model works on BGR only,
    and losing a cut-out's transparency here would undo remove_bg.
    """
    import numpy as np
    from gfpgan import GFPGANer

    from utils import PIPELINE_ROOT

    model_dir = PIPELINE_ROOT / "models" / "gfpgan"
    model_dir.mkdir(parents=True, exist_ok=True)
    weights = model_dir / "GFPGANv1.4.pth"

    if not weights.exists():
        report(f"Downloading GFPGAN weights to {weights}")
        import urllib.request

        urllib.request.urlretrieve(
            "https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.4.pth",
            weights,
        )

    alpha = source.getchannel("A") if source.mode == "RGBA" else None
    rgb = np.array(source.convert("RGB"))[:, :, ::-1]  # PIL RGB to the BGR the model expects

    # GFPGAN 1.3 resolves its detector/parser cache below a relative
    # gfpgan/weights path. Anchor that legacy path in the shared model root so
    # deployments never download support weights into a release or cwd.
    with chdir(PIPELINE_ROOT / "models"):
        restorer = GFPGANer(
            model_path=str(weights),
            upscale=1,
            arch="clean",
            channel_multiplier=2,
            device=device,
        )
    report(f"GFPGAN on {device}")
    _, _, restored = restorer.enhance(rgb, has_aligned=False, paste_back=True, weight=args.fidelity)

    if restored is None:
        report("  No face found - leaving the image alone.")
        return source

    result = Image.fromarray(restored[:, :, ::-1])
    if alpha is not None:
        result.putalpha(alpha)
    return result


def main() -> None:
    parser = base_parser("Enhance a photograph.")
    parser.add_argument("--engine", default="auto", choices=ENGINES)
    parser.add_argument(
        "--fidelity",
        type=float,
        default=0.7,
        help="GFPGAN: 0 rebuilds aggressively, 1 stays close to the original.",
    )
    parser.add_argument("--brightness", type=float, default=1.0)
    parser.add_argument("--contrast", type=float, default=1.0)
    parser.add_argument("--sharpness", type=float, default=1.0)
    parser.add_argument("--color", type=float, default=1.0)
    args = parser.parse_args()

    if not args.input.exists():
        fail(f"No such file: {args.input}")

    with Image.open(args.input) as opened:
        source = opened.convert("RGBA" if opened.mode in ("RGBA", "LA", "P") else "RGB")
        report(f"Input: {source.width}x{source.height} {source.mode}")

        engine = args.engine
        device = torch_device()

        if engine == "auto":
            engine = "gfpgan" if device == "cuda" else "pillow"
            report(f"Engine auto-selected: {engine}" + (f" ({device})" if device else " (no torch)"))
        elif engine == "gfpgan" and not device:
            report("torch is not installed here - falling back to pillow.")
            engine = "pillow"

        if engine == "gfpgan":
            try:
                result = enhance_gfpgan(source, args, device)
            except Exception as error:  # noqa: BLE001 - any failure should still produce an image
                report(f"GFPGAN failed ({error}) - falling back to pillow.")
                result = enhance_pillow(source, args)
        else:
            result = enhance_pillow(source, args)

        prepare_output(args.output)
        result.save(args.output, format="PNG", optimize=True)
        report(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
