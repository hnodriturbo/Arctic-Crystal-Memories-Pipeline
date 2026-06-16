# =============================================================
# 02_remove_bg.py — Background removal using REMBG
# =============================================================
# PURPOSE:
#   Second step in the pipeline. Takes the upscaled image from
#   step 01 and cleanly separates the subject (person, object)
#   from the background. The result is a PNG with full transparency
#   where the background was.
#
# WHY THIS MATTERS FOR SSLE (Crystal Engraving):
#   Background elements have their own depth. If the background
#   is not removed, the depth model in step 03 will estimate depth
#   for walls, floors, furniture — everything in the scene. That
#   bleeds into the subject's mesh, creating noise and artifacts
#   around edges. In a 3D crystal this looks like a muddy, blurry
#   outline or ghost shapes behind the subject.
#
#   Clean background removal = clean depth map = clean crystal.
#
# STRATEGY — REMBG MODEL SELECTION:
#   REMBG is a Python wrapper around neural matting/segmentation
#   models. Different models make different quality/speed tradeoffs:
#
#   u2net               — fast, general, good baseline
#   u2netp              — lighter version of u2net, lower quality
#   isnet-general-use   — best detail on hair and fine edges (default)
#   isnet-anime         — for illustrated/anime subjects
#   sam                 — Segment Anything (most precise, requires CUDA)
#
#   For portrait photos (our main use case), isnet-general-use wins
#   on hair and soft edges. It is slower than u2net but the quality
#   difference at the hair boundary is visible in the final crystal.
#
#   Models are downloaded automatically on first use and cached to:
#   ~/.u2net/  (managed by rembg — not a pipeline/ folder)
#
# ALPHA MASK:
#   The output PNG has 4 channels (RGBA). The alpha channel is the
#   segmentation mask: 255 = subject kept, 0 = background removed.
#   An additional grayscale mask PNG is saved alongside each result
#   so it can be inspected or refined in Photoshop before step 03.
#
# INPUTS:
#   - Upscaled PNG(s) from output/upscaled/
#   - REMBG_MODEL from .env (default: isnet-general-use)
#
# OUTPUTS:
#   - output/bg_removed/{stem}_nobg.png   — RGBA subject (4-channel)
#   - output/bg_removed/{stem}_mask.png   — grayscale alpha mask
#
# USAGE:
#   python 02_remove_bg.py                           # all upscaled images
#   python 02_remove_bg.py --file photo_upscaled.png # single file
#   python 02_remove_bg.py --model u2net             # override model
#   python 02_remove_bg.py --no-mask                 # skip mask export
#
# DEPENDENCIES: rembg, Pillow, numpy, python-dotenv, tqdm
#
# NOTES:
#   - Always visually inspect output before running step 03.
#     A missed background permanently degrades the depth map.
#   - CUDA speeds up the sam model significantly. Other models
#     run fine on CPU in ~5–20 seconds per image.
#   - If hair edges look rough, switch to isnet-general-use.
#   - The --no-mask flag exists for batch runs where disk space
#     matters more than having masks for manual review.
# =============================================================

from pathlib import Path
import argparse
import sys
import time
import os

# Load .env before anything else so REMBG_MODEL and OUTPUT_DIR are visible
# to the utility imports below. This mirrors the same pattern used in 01_upscale.py.
from dotenv import load_dotenv

PIPELINE_DIR = Path(__file__).resolve().parent
load_dotenv(PIPELINE_DIR / ".env")


# =============================================================
# DEPENDENCY CHECKS
# =============================================================
# Guard against missing packages with a clear message and install hint
# rather than letting Python show a raw ImportError traceback.

try:
    from PIL import Image
except ImportError:
    print("ERROR: Pillow is not installed.")
    print("       Run: pip install Pillow")
    sys.exit(1)

try:
    from rembg import new_session, remove as rembg_remove
except ImportError:
    print("ERROR: rembg is not installed.")
    print("       Run: pip install rembg")
    sys.exit(1)

try:
    from tqdm import tqdm
except ImportError:
    print("ERROR: tqdm is not installed. Run: pip install tqdm")
    sys.exit(1)

# Pipeline utilities — safe to import after load_dotenv() above
from utils.file_utils import (
    build_output_path,
    get_output_dir,
    latest_run_name,
    resolve_run_name,
)
from utils.image_utils import get_image_info


# =============================================================
# MODEL REGISTRY
# =============================================================
# Describes the available REMBG models and their best use cases.
# This registry drives both CLI tab-completion (choices=) and the
# informational print at startup so the operator knows what is running.

MODEL_INFO: dict[str, str] = {
    "isnet-general-use": (
        "Best quality on hair and soft edges — recommended for portraits"
    ),
    "u2net": (
        "Fast general-purpose model — good default for non-portrait subjects"
    ),
    "u2netp":  (
        "Lightweight u2net variant — fastest but lowest edge quality"
    ),
    "isnet-anime": (
        "Optimized for illustrations and anime-style artwork"
    ),
    "sam": (
        "Segment Anything — highest precision, requires CUDA, very slow on CPU"
    ),
}

# Default model chosen for portrait photos — isnet handles hair better than u2net.
# This is what matters most for the Crystal Clear Memories use case.
DEFAULT_MODEL = os.getenv("REMBG_MODEL", "isnet-general-use")


# =============================================================
# SESSION MANAGEMENT
# =============================================================

def load_rembg_session(model_name: str):
    """
    Create and return a REMBG inference session for the given model.

    REMBG downloads the model weights on first use (to ~/.u2net/) and
    caches them locally. Subsequent runs find the cached weights and
    start immediately. The session object is created once and reused
    for every image to avoid reloading weights between images.

    Args:
        model_name: Key from MODEL_INFO, e.g. 'isnet-general-use'

    Returns:
        REMBG session object ready to pass to rembg_remove()
    """
    if model_name not in MODEL_INFO:
        available = ", ".join(MODEL_INFO.keys())
        raise ValueError(
            f"Unknown model '{model_name}'. Available models: {available}"
        )

    print(f"  Model:   {model_name}")
    print(f"           {MODEL_INFO[model_name]}")
    print("  Loading session... (weights download on first use)")

    session = new_session(model_name)
    return session


# =============================================================
# BACKGROUND REMOVAL
# =============================================================

def remove_background(
    image_path: Path,
    session,
    run: str,
    fg_threshold: int = 240,
    bg_threshold: int = 10,
    erode_size: int = 10,
) -> Path:
    """
    Remove the background from one image and save the RGBA result.

    REMBG expects raw bytes from the image file and returns a PNG as bytes.
    The output is a 4-channel RGBA image where the alpha channel encodes
    the segmentation mask (255 = keep, 0 = removed).

    Args:
        image_path: Path to the upscaled source PNG
        session:    Active REMBG session (call load_rembg_session() first)

    Returns:
        Path to the saved RGBA PNG in output/bg_removed/
    """
    info = get_image_info(image_path)
    tqdm.write(
        f"  Input:   {image_path.name}  "
        f"{info['width']} x {info['height']} px  |  "
        f"{info['file_size_mb']} MB"
    )

    t_start = time.perf_counter()

    # Read the image as raw bytes — REMBG handles format detection internally.
    # Using bytes avoids an unnecessary decode/encode round-trip.
    image_bytes = image_path.read_bytes()

    # rembg_remove() runs the neural model and returns PNG bytes with alpha.
    # alpha_matting=True enables soft edge blending for hair/fur, at the cost
    # of slightly longer processing time. It only applies to the final edge pixels.
    output_bytes = rembg_remove(
        image_bytes,
        session=session,
        alpha_matting=True,
        alpha_matting_foreground_threshold=fg_threshold,
        alpha_matting_background_threshold=bg_threshold,
        alpha_matting_erode_size=erode_size,
    )

    elapsed = time.perf_counter() - t_start

    # rembg_remove() can return bytes, a PIL Image, or a numpy array depending on
    # what was passed in. We always pass bytes so the return is bytes, but the
    # type stub is a union — cast explicitly to satisfy the type checker and
    # avoid any ambiguity at runtime.
    import io
    if isinstance(output_bytes, Image.Image):
        result_img = output_bytes.convert("RGBA")
    else:
        result_img = Image.open(io.BytesIO(bytes(output_bytes))).convert("RGBA")

    tqdm.write(
        f"  Output:  {result_img.width} x {result_img.height} px  |  "
        f"RGBA  |  {elapsed:.1f}s"
    )

    # Build output path: photo_upscaled.png → bg_removed/photo_upscaled_nobg.png
    # Note: we use the full upscaled filename stem (including _upscaled) so the
    # output folder clearly shows which upscaled version this was made from.
    nobg_path = build_output_path(image_path.name, "nobg", "png", run=run)
    result_img.save(nobg_path, format="PNG")
    tqdm.write(f"  Saved:   {nobg_path.name}")

    return nobg_path


# =============================================================
# ALPHA MASK EXPORT
# =============================================================

def save_alpha_mask(nobg_path: Path) -> Path:
    """
    Extract the alpha channel from the RGBA result and save it as a
    standalone grayscale PNG.

    The mask PNG is a visual map of what was kept (white) vs. removed (black).
    It is useful for:
      - Quickly checking whether the model correctly found the subject
      - Manual retouching in Photoshop/GIMP to fix missed areas
      - Passing to step 03 as an explicit foreground hint (future feature)

    The mask file lives in the same bg_removed/ folder as the RGBA result
    with a _mask suffix so it is easy to find alongside its source.

    Args:
        nobg_path: Path to the RGBA PNG saved by remove_background()

    Returns:
        Path to the saved grayscale mask PNG
    """
    rgba_img = Image.open(nobg_path).convert("RGBA")

    # Split returns (R, G, B, A) — we only need the last channel.
    _, _, _, alpha = rgba_img.split()

    # Build the mask path from the nobg path — e.g.
    # bg_removed/photo_upscaled_nobg.png → bg_removed/photo_upscaled_mask.png
    mask_stem = nobg_path.stem.replace("_nobg", "_mask")
    mask_path = nobg_path.parent / f"{mask_stem}.png"

    alpha.save(mask_path, format="PNG")
    tqdm.write(f"  Mask:    {mask_path.name}")

    return mask_path


# =============================================================
# INPUT SCANNER — upscaled folder
# =============================================================

def list_upscaled_images(run: str) -> list[Path]:
    """
    Return all PNG files in output/upscaled/{run}/ sorted alphabetically.

    Args:
        run: Run subfolder name, e.g. 'try_01'

    Returns:
        Sorted list of Path objects for all .png files in the run folder
    """
    upscaled_dir = get_output_dir("upscaled", run)

    images = sorted(
        [p for p in upscaled_dir.iterdir() if p.is_file() and p.suffix.lower() == ".png"],
        key=lambda p: p.name.lower(),
    )

    print(f"Found {len(images)} upscaled image(s) in: {upscaled_dir}")
    return images


# =============================================================
# CLI ARGUMENT PARSING
# =============================================================

def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments.

    All arguments are optional — .env values are used as defaults.
    CLI arguments always override .env when both are present.
    """
    parser = argparse.ArgumentParser(
        description="Step 02 — Remove image background with REMBG.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python 02_remove_bg.py\n"
            "  python 02_remove_bg.py --file portrait_upscaled.png\n"
            "  python 02_remove_bg.py --model u2net\n"
            "  python 02_remove_bg.py --no-mask\n"
        ),
    )

    parser.add_argument(
        "--file",
        type=str,
        default=None,
        metavar="FILENAME",
        help=(
            "Process a single file from output/upscaled/ instead of the whole folder. "
            "Provide just the filename, e.g. portrait_upscaled.png"
        ),
    )
    parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_MODEL,
        choices=list(MODEL_INFO.keys()),
        help=(
            f"REMBG model to use (default: {DEFAULT_MODEL}). "
            "isnet-general-use is recommended for portrait photos."
        ),
    )
    parser.add_argument(
        "--no-mask",
        action="store_true",
        default=False,
        help=(
            "Skip saving the separate alpha mask PNG. "
            "Use this in batch runs where the mask is not needed for review."
        ),
    )
    parser.add_argument(
        "--fg-threshold",
        type=int,
        default=240,
        metavar="N",
        help="Alpha matting foreground threshold 0-255 (default: 240). Lower = more pixels treated as foreground.",
    )
    parser.add_argument(
        "--bg-threshold",
        type=int,
        default=10,
        metavar="N",
        help="Alpha matting background threshold 0-255 (default: 10). Higher = more pixels treated as background.",
    )
    parser.add_argument(
        "--erode-size",
        type=int,
        default=10,
        metavar="N",
        help="Alpha matting erode size in pixels (default: 10). Higher = more aggressive background erosion near edges.",
    )
    parser.add_argument(
        "--from-run",
        type=str,
        default=None,
        metavar="NAME",
        help=(
            "Which upscaled run to read from, e.g. try_02. "
            "Defaults to the latest non-empty try_XX in output/upscaled/."
        ),
    )
    parser.add_argument(
        "--run",
        type=str,
        default=None,
        metavar="NAME",
        help=(
            "Output run subfolder name, e.g. try_03. "
            "Auto-increments to next available try_XX in output/bg_removed/ if omitted."
        ),
    )

    return parser.parse_args()


# =============================================================
# MAIN ENTRY POINT
# =============================================================

def main() -> None:
    args = parse_args()

    print("=" * 60)
    print("K9 Crystal Pipeline  —  Step 02: Remove Background")
    print("=" * 60)
    print(f"  Model:   {args.model}")
    print(f"           {MODEL_INFO[args.model]}")
    print(f"  Masks:   {'disabled (--no-mask)' if args.no_mask else 'enabled'}")
    print()

    # Input: read from the latest non-empty upscaled run (or explicit --from-run)
    input_run = latest_run_name("upscaled", args.from_run)
    # Output: write to next available nobg run (or explicit --run)
    tag = Path(args.file).stem if args.file else None
    output_run = resolve_run_name("nobg", args.run, tag=tag)
    print(f"  Input:   output/upscaled/{input_run}/")
    print(f"  Output:  output/bg_removed/{output_run}/\n")

    # -------------------------------------------------------
    # Collect images to process
    # -------------------------------------------------------
    if args.file:
        single_path = get_output_dir("upscaled", input_run) / args.file
        if not single_path.exists():
            print(f"ERROR: File not found: {single_path}")
            print(
                "       Make sure you ran step 01 first and "
                "provide just the filename, not a full path."
            )
            sys.exit(1)
        images_to_process = [single_path]
    else:
        images_to_process = list_upscaled_images(input_run)
        if not images_to_process:
            print()
            print("ERROR: No upscaled images found in output/upscaled/")
            print("       Run step 01 first:  python 01_upscale.py")
            sys.exit(1)

    print(f"Processing {len(images_to_process)} image(s).\n")

    # -------------------------------------------------------
    # Load the REMBG session — once, reused for all images.
    # Session creation triggers a model weight download on first run.
    # -------------------------------------------------------
    print("Initializing REMBG session...")
    session = load_rembg_session(args.model)
    print("Session ready.\n")

    # -------------------------------------------------------
    # Process images
    # -------------------------------------------------------
    total_start = time.perf_counter()
    success_count = 0
    failed: list[str] = []

    progress_bar = tqdm(
        images_to_process,
        desc="Removing background",
        unit="img",
        leave=True,
        dynamic_ncols=True,
    )

    for image_path in progress_bar:
        progress_bar.set_description(f"Processing: {image_path.name}")
        try:
            nobg_path = remove_background(
                image_path,
                session,
                run=output_run,
                fg_threshold=args.fg_threshold,
                bg_threshold=args.bg_threshold,
                erode_size=args.erode_size,
            )

            if not args.no_mask:
                save_alpha_mask(nobg_path)

            success_count += 1

        except Exception as exc:
            tqdm.write(f"\nERROR — '{image_path.name}': {exc}")
            tqdm.write("  Skipping this file and continuing with the rest.\n")
            failed.append(image_path.name)

    total_elapsed = time.perf_counter() - total_start

    # -------------------------------------------------------
    # Summary
    # -------------------------------------------------------
    print()
    print("=" * 60)
    print("Step 02 complete.")
    print(f"  Processed: {success_count} image(s)")
    if failed:
        print(f"  Failed:    {len(failed)} image(s)")
        for name in failed:
            print(f"    - {name}")
    print(f"  Total time: {total_elapsed:.1f}s")
    print(f"  Output:    output/bg_removed/{output_run}/")
    print()
    print(
        "  IMPORTANT: Visually inspect the output before continuing.\n"
        "             A missed background will degrade the depth map in step 03."
    )
    print()
    print("Next step: python 03_depth_estimate.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
