# =============================================================
# 01_prepare.py — Background removal + aspect-ratio-safe resize
# =============================================================
# PURPOSE:
#   First step. Takes a raw source photo from input/, removes the
#   background, then resizes the result to the target working
#   resolution. Output is an RGBA PNG ready for depth estimation.
#
# ORDER OF OPERATIONS:
#   1. Remove background (rembg) at native resolution
#      Doing this before resize gives the model the most pixels to
#      find subject edges accurately, especially on hair/fur.
#   2. Resize the clean RGBA to the target size
#      The target is defined by --target-long-edge (default 1800px).
#      The short side is always calculated from the true input ratio
#      so proportions are mathematically identical to the original.
#
# ASPECT RATIO RULE:
#   compute_target_size() is the single function that decides both
#   dimensions. Never compute target sizes inline. The pipeline
#   always preserves the exact image ratio — no cropping, no padding,
#   no squashing.
#
# REMBG MODEL SELECTION:
#   isnet-general-use   — best detail on hair/soft edges (default)
#   u2net               — fast general-purpose baseline
#   u2netp              — lightest, lowest quality
#   isnet-anime         — for illustrated/anime subjects
#   sam                 — Segment Anything (most precise, CUDA)
#
# OUTPUTS:
#   output/prepared/{run}/{stem}_prepared.png       — RGBA subject
#   output/prepared/{run}/{stem}_prepared_mask.png  — grayscale mask
#
# USAGE:
#   python 01_prepare.py                                # all images in input/
#   python 01_prepare.py --file portrait.jpg            # single file
#   python 01_prepare.py --target-long-edge 2000        # larger working size
#   python 01_prepare.py --model u2net                  # override rembg model
#   python 01_prepare.py --run one_person_v1            # explicit run name
#
# DEPENDENCIES: rembg, Pillow, numpy, python-dotenv, tqdm
# =============================================================

from pathlib import Path
import argparse
import io
import sys
import time
import os

from dotenv import load_dotenv

PIPELINE_DIR = Path(__file__).resolve().parent
load_dotenv(PIPELINE_DIR / ".env")


# =============================================================
# DEPENDENCY CHECKS
# =============================================================

try:
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None  # rembg on native-res images can exceed Pillow's default limit
except ImportError:
    print("ERROR: Pillow is not installed. Run: pip install Pillow")
    sys.exit(1)

try:
    from rembg import new_session, remove as rembg_remove
except ImportError:
    print("ERROR: rembg is not installed. Run: pip install 'rembg[gpu]'")
    sys.exit(1)

try:
    from tqdm import tqdm
except ImportError:
    print("ERROR: tqdm is not installed. Run: pip install tqdm")
    sys.exit(1)

from utils.file_utils import (
    build_output_path,
    get_input_dir,
    list_input_images,
    resolve_run_name,
)
from utils.image_utils import (
    compute_target_size,
    extract_alpha_mask,
    get_image_info,
    resize_image,
)


# =============================================================
# REMBG MODEL REGISTRY
# =============================================================

MODEL_INFO: dict[str, str] = {
    "isnet-general-use": "Best quality on hair and soft edges — recommended for portraits",
    "u2net":             "Fast general-purpose model — good default for non-portrait subjects",
    "u2netp":            "Lightweight u2net variant — fastest but lowest edge quality",
    "isnet-anime":       "Optimized for illustrations and anime-style artwork",
    "sam":               "Segment Anything — highest precision, requires CUDA",
}

DEFAULT_MODEL = os.getenv("REMBG_MODEL", "isnet-general-use")

# Default long-edge target for the prepared output.
# 1800px on the long side is enough for ZoeDepth and mesh generation —
# larger values give no depth quality benefit but increase memory and time.
DEFAULT_LONG_EDGE = int(os.getenv("PREPARE_LONG_EDGE", "1800"))


# =============================================================
# CORE PROCESSING
# =============================================================

def prepare_image(
    image_path: Path,
    session,
    target_long_edge: int,
    run: str,
    fg_threshold: int = 240,
    bg_threshold: int = 10,
    erode_size: int = 10,
) -> tuple[Path, Path]:
    """
    Remove background then resize one image to the target working resolution.

    Both steps run at this function's scope so intermediate (native-res RGBA)
    data is freed from memory as soon as the resize is complete.

    Args:
        image_path:       Path to the source image in input/
        session:          Active rembg session
        target_long_edge: Pixel length of the longer dimension after resize
        run:              Output run subfolder name

    Returns:
        Tuple of (prepared_rgba_path, mask_path)
    """
    info = get_image_info(image_path)
    orig_w, orig_h = info["width"], info["height"]
    new_w, new_h = compute_target_size(orig_w, orig_h, target_long_edge)

    tqdm.write(
        f"  Input:   {image_path.name}  {orig_w} x {orig_h} px  |  "
        f"{info['file_size_mb']} MB  |  {info['mode']}"
    )
    tqdm.write(
        f"  Target:  {new_w} x {new_h} px  "
        f"(long edge {target_long_edge}px, ratio {orig_w/orig_h:.4f} → {new_w/new_h:.4f})"
    )

    t_start = time.perf_counter()

    # Step 1: remove background at native resolution for best edge quality
    image_bytes = image_path.read_bytes()
    output_bytes = rembg_remove(
        image_bytes,
        session=session,
        alpha_matting=True,
        alpha_matting_foreground_threshold=fg_threshold,
        alpha_matting_background_threshold=bg_threshold,
        alpha_matting_erode_size=erode_size,
    )

    if isinstance(output_bytes, Image.Image):
        rgba_native = output_bytes.convert("RGBA")
    else:
        rgba_native = Image.open(io.BytesIO(bytes(output_bytes))).convert("RGBA")

    bg_elapsed = time.perf_counter() - t_start
    tqdm.write(f"  BG done: {rgba_native.width} x {rgba_native.height} px  |  {bg_elapsed:.1f}s")

    # Step 2: resize to target — aspect ratio guaranteed by compute_target_size()
    rgba_resized = resize_image(rgba_native, new_w, new_h)
    del rgba_native  # free native-res RGBA before saving

    resize_elapsed = time.perf_counter() - t_start - bg_elapsed
    tqdm.write(
        f"  Resized: {rgba_resized.width} x {rgba_resized.height} px  |  {resize_elapsed:.2f}s"
    )

    # Save RGBA
    prepared_path = build_output_path(image_path.name, "prepared", "png", run=run)
    rgba_resized.save(str(prepared_path), format="PNG", compress_level=1)
    tqdm.write(f"  Saved:   {prepared_path.name}")

    # Save grayscale mask from the resized RGBA
    mask = extract_alpha_mask(rgba_resized)
    mask_stem = prepared_path.stem.replace("_prepared", "_prepared_mask")
    mask_path = prepared_path.parent / f"{mask_stem}.png"
    mask.save(str(mask_path), format="PNG")
    tqdm.write(f"  Mask:    {mask_path.name}")

    total_elapsed = time.perf_counter() - t_start
    tqdm.write(f"  Total:   {total_elapsed:.1f}s")

    return prepared_path, mask_path


# =============================================================
# CLI ARGUMENT PARSING
# =============================================================

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Step 01 — Remove background and resize to working resolution.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python 01_prepare.py\n"
            "  python 01_prepare.py --file portrait.jpg\n"
            "  python 01_prepare.py --target-long-edge 2000\n"
            "  python 01_prepare.py --model u2net --run test_01\n"
        ),
    )

    parser.add_argument(
        "--file",
        type=str,
        default=None,
        metavar="FILENAME",
        help="Process a single file from input/. Provide just the filename.",
    )
    parser.add_argument(
        "--target-long-edge",
        type=int,
        default=DEFAULT_LONG_EDGE,
        metavar="PX",
        help=(
            f"Pixel length of the longer image dimension after resize (default: {DEFAULT_LONG_EDGE}). "
            "The shorter side is calculated automatically from the true aspect ratio."
        ),
    )
    parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_MODEL,
        choices=list(MODEL_INFO.keys()),
        help=f"rembg model for background removal (default: {DEFAULT_MODEL}).",
    )
    parser.add_argument(
        "--fg-threshold",
        type=int,
        default=240,
        metavar="N",
        help="Alpha matting foreground threshold 0-255 (default: 240).",
    )
    parser.add_argument(
        "--bg-threshold",
        type=int,
        default=10,
        metavar="N",
        help="Alpha matting background threshold 0-255 (default: 10).",
    )
    parser.add_argument(
        "--erode-size",
        type=int,
        default=10,
        metavar="N",
        help="Alpha matting erode size in pixels (default: 10).",
    )
    parser.add_argument(
        "--run",
        type=str,
        default=None,
        metavar="NAME",
        help="Output run subfolder name. Auto-increments to next try_XX if omitted.",
    )

    return parser.parse_args()


# =============================================================
# MAIN ENTRY POINT
# =============================================================

def main() -> None:
    args = parse_args()

    print("=" * 60)
    print("K9 Crystal Pipeline  —  Step 01: Prepare")
    print("=" * 60)
    print(f"  BG model:    {args.model}")
    print(f"               {MODEL_INFO[args.model]}")
    print(f"  Target size: long edge = {args.target_long_edge}px  (short side auto-calculated)")
    print()

    # Collect images
    if args.file:
        single_path = get_input_dir() / args.file
        if not single_path.exists():
            print(f"ERROR: File not found: {single_path}")
            sys.exit(1)
        images_to_process = [single_path]
    else:
        images_to_process = list_input_images()
        if not images_to_process:
            print("No images found in input/. Drop .jpg or .png files there and re-run.")
            sys.exit(0)

    print(f"Processing {len(images_to_process)} image(s).\n")

    # Resolve run name once — all images in this batch share the same folder
    tag = Path(args.file).stem if args.file else None
    run = resolve_run_name("prepared", args.run, tag=tag)
    print(f"Run:     {run}  →  output/prepared/{run}/\n")

    # Load rembg session once — reused for every image
    print("Initializing rembg session...")
    session = new_session(args.model)
    print("Session ready.\n")

    total_start = time.perf_counter()
    success_count = 0
    failed: list[str] = []

    progress_bar = tqdm(
        images_to_process,
        desc="Preparing",
        unit="img",
        leave=True,
        dynamic_ncols=True,
    )

    for image_path in progress_bar:
        progress_bar.set_description(f"Preparing: {image_path.name}")
        try:
            prepare_image(
                image_path,
                session,
                target_long_edge=args.target_long_edge,
                run=run,
                fg_threshold=args.fg_threshold,
                bg_threshold=args.bg_threshold,
                erode_size=args.erode_size,
            )
            success_count += 1
        except Exception as exc:
            tqdm.write(f"\nERROR — '{image_path.name}': {exc}")
            tqdm.write("  Skipping this file and continuing.\n")
            failed.append(image_path.name)

    total_elapsed = time.perf_counter() - total_start

    print()
    print("=" * 60)
    print("Step 01 complete.")
    print(f"  Prepared:   {success_count} image(s)")
    if failed:
        print(f"  Failed:     {len(failed)} image(s)")
        for name in failed:
            print(f"    - {name}")
    print(f"  Total time: {total_elapsed:.1f}s")
    print(f"  Output:     output/prepared/{run}/")
    print()
    print("  IMPORTANT: Inspect the mask PNG before continuing.")
    print("             A missed background degrades the depth map.")
    print()
    print("Next step: python 02_depth_estimate.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
