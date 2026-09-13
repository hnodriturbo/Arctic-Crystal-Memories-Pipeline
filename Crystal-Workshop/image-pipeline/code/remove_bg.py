"""
remove_bg.py — cut the subject out of a photograph.
Path: converter/image-pipeline/code/remove_bg.py

Writes an RGBA PNG with a transparent background, and optionally the alpha
channel on its own as a mask.

Why it matters for Meshy: a cut-out subject gives the generator an unambiguous
silhouette. Left on a busy background it will happily solve the sofa behind
someone's shoulder as part of the bust.

CPU-only by design — rembg[cpu] on onnxruntime. A full-size portrait takes a
few seconds on the VPS, which is why this step is available on both machines
while upscaling and face restoration are not.

  python code/remove_bg.py --input photo.jpg --output cutout.png
  python code/remove_bg.py --input photo.jpg --output cutout.png --model birefnet-portrait
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from utils import base_parser, fail, prepare_output, report

# rembg sub-models, best first for the work this pipeline does.
MODELS = [
    "birefnet-portrait",   # people, and the sharpest hair edges of the set
    "birefnet-general",    # objects, buildings, anything not a person
    "isnet-general-use",   # solid general fallback, smaller download
    "u2net_human_seg",     # people-specific, older and softer
    "u2net",               # original general model
    "u2netp",              # smallest CPU/RAM fallback for constrained servers
]


def main() -> None:
    parser = base_parser("Remove a photograph's background.")
    parser.add_argument("--model", default="birefnet-portrait", choices=MODELS)
    parser.add_argument("--mask", type=Path, help="Optional path for the alpha channel alone.")
    parser.add_argument(
        "--alpha-matting",
        action="store_true",
        help="Slower, but recovers fine hair against a busy background.",
    )
    args = parser.parse_args()

    if not args.input.exists():
        fail(f"No such file: {args.input}")

    # Imported here rather than at module scope so --help works without the
    # 4.5 MB model download having ever happened.
    from rembg import new_session, remove

    report(f"Model: {args.model}")
    session = new_session(args.model)

    with Image.open(args.input) as source:
        report(f"Input: {source.width}x{source.height} {source.mode}")
        cutout = remove(
            source.convert("RGBA"),
            session=session,
            alpha_matting=args.alpha_matting,
        )

        if not isinstance(cutout, Image.Image):
            fail("rembg returned an unexpected output type.")

        cutout = cutout.convert("RGBA")
        prepare_output(args.output)
        cutout.save(args.output, format="PNG", optimize=True)
        report(f"Wrote {args.output}")

        if args.mask:
            prepare_output(args.mask)
            cutout.getchannel("A").save(args.mask, format="PNG", optimize=True)
            report(f"Wrote {args.mask}")

    # A cut-out that keeps almost every pixel usually means the model found no
    # subject at all, which is worth saying out loud before Meshy is paid to
    # solve the whole frame as one lump.
    with Image.open(args.output) as result:
        alpha = result.getchannel("A")
        opaque = sum(count for value, count in enumerate(alpha.histogram()) if value > 16)
        coverage = opaque / float(result.width * result.height)
        report(f"Subject covers {coverage:.0%} of the frame.")
        if coverage > 0.95:
            report("  Warning: almost nothing was removed. Try --model birefnet-general.")


if __name__ == "__main__":
    main()
