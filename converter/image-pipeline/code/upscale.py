"""
upscale.py — enlarge a photograph without softening it.
Path: converter/image-pipeline/code/upscale.py

Aspect ratio and alpha are always preserved, and an image already at or above
the target is copied through untouched rather than being re-encoded.

Engines:
  auto        Real-ESRGAN when torch is installed, Lanczos otherwise.
  realesrgan  AI upscale. Needs torch; slow but usable on CPU, seconds on CUDA.
  lanczos     Classic resample. Instant, invents nothing, never fails.

The VPS has no torch, so `auto` quietly resolves to lanczos there. That is the
honest outcome: a real upscale needs a GPU, and pretending otherwise would
just make the job time out.

  python code/upscale.py --input photo.jpg --output big.png --target 2048
"""

from __future__ import annotations

import shutil

from PIL import Image

from utils import base_parser, fail, prepare_output, report, torch_device

ENGINES = ["auto", "realesrgan", "lanczos"]
REALESRGAN_URL = (
    "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth"
)


def upscale_lanczos(source: Image.Image, target_long_edge: int) -> Image.Image:
    """Plain resample. The floor every machine can reach."""
    scale = target_long_edge / float(max(source.width, source.height))
    size = (max(1, round(source.width * scale)), max(1, round(source.height * scale)))
    report(f"Lanczos to {size[0]}x{size[1]}")
    return source.resize(size, Image.LANCZOS)


def upscale_realesrgan(source: Image.Image, target_long_edge: int, device: str) -> Image.Image:
    """
    Real-ESRGAN x4, then resampled down to the requested long edge.

    Alpha is carried around the model rather than through it: the network has
    three input channels, and a cut-out's transparency is the whole point of
    having run remove_bg first.
    """
    import numpy as np
    from basicsr.archs.rrdbnet_arch import RRDBNet
    from realesrgan import RealESRGANer

    from utils import PIPELINE_ROOT

    model_dir = PIPELINE_ROOT / "models" / "realesrgan"
    model_dir.mkdir(parents=True, exist_ok=True)
    weights = model_dir / "RealESRGAN_x4plus.pth"

    if not weights.exists():
        report(f"Downloading Real-ESRGAN weights to {weights}")
        import urllib.request

        urllib.request.urlretrieve(REALESRGAN_URL, weights)

    architecture = RRDBNet(
        num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=4
    )
    upsampler = RealESRGANer(
        scale=4,
        model_path=str(weights),
        model=architecture,
        half=(device == "cuda"),
        device=device,
    )

    alpha = source.getchannel("A") if source.mode == "RGBA" else None
    rgb = np.array(source.convert("RGB"))

    report(f"Real-ESRGAN x4 on {device}")
    enlarged, _ = upsampler.enhance(rgb, outscale=4)
    result = Image.fromarray(enlarged)

    if alpha is not None:
        result.putalpha(alpha.resize(result.size, Image.LANCZOS))

    if max(result.width, result.height) != target_long_edge:
        result = upscale_lanczos(result, target_long_edge)
    return result


def main() -> None:
    parser = base_parser("Upscale a photograph.")
    parser.add_argument("--engine", default="auto", choices=ENGINES)
    parser.add_argument("--target", type=int, default=2048, help="Target long edge in pixels.")
    args = parser.parse_args()

    if not args.input.exists():
        fail(f"No such file: {args.input}")

    with Image.open(args.input) as opened:
        source = opened.convert("RGBA" if opened.mode in ("RGBA", "LA", "P") else "RGB")
        long_edge = max(source.width, source.height)
        report(f"Input: {source.width}x{source.height} {source.mode}")

        if long_edge >= args.target:
            report(f"Already {long_edge}px on the long edge - copying through untouched.")
            prepare_output(args.output)
            if args.input.suffix.lower() == args.output.suffix.lower():
                shutil.copyfile(args.input, args.output)
            else:
                source.save(args.output)
            report(f"Wrote {args.output}")
            return

        engine = args.engine
        device = torch_device()

        if engine == "auto":
            engine = "realesrgan" if device else "lanczos"
            report(f"Engine auto-selected: {engine}" + (f" ({device})" if device else " (no torch)"))
        elif engine == "realesrgan" and not device:
            report("torch is not installed here - falling back to lanczos.")
            engine = "lanczos"

        if engine == "realesrgan":
            try:
                result = upscale_realesrgan(source, args.target, device)
            except Exception as error:  # noqa: BLE001 - any failure should still produce an image
                report(f"Real-ESRGAN failed ({error}) - falling back to lanczos.")
                result = upscale_lanczos(source, args.target)
        else:
            result = upscale_lanczos(source, args.target)

        prepare_output(args.output)
        result.save(args.output, format="PNG", optimize=True)
        report(f"Wrote {args.output} at {result.width}x{result.height}")


if __name__ == "__main__":
    main()
