# =============================================================
# 01_upscale.py — Image upscaling using Real-ESRGAN
# =============================================================
# PURPOSE:
#   First step in the pipeline. Upscales source photos before
#   any other processing. More pixels = better depth estimation
#   = finer, more detailed engravings. This step is critical
#   for getting good results from low-to-medium resolution photos.
#
# WHY FIRST:
#   Depth estimation models produce better results when given
#   high-resolution input. A 4x upscale of a 2MP photo (1920x1080)
#   produces an 8MP equivalent before the depth model runs.
#   Real-ESRGAN is specifically trained to restore realistic
#   detail, not just scale pixels — it adds plausible texture.
#
# MODEL USED:
#   RealESRGAN_x4plus        — general photo upscaling (portraits, customer photos)
#   RealESRGAN_x2plus        — 2x variant for already high-res input
#   RealESRGAN_x4plus_anime  — illustrated / artwork input (logos, graphics)
#   Models auto-download on first run to: pipeline/models/realesrgan/
#
# INPUTS:
#   - Source image(s) from INPUT_DIR (.jpg, .png, etc.)
#   - UPSCALE_FACTOR from .env (default: 4)
#
# OUTPUTS:
#   - Upscaled PNG saved to: OUTPUT_DIR/upscaled/{stem}_upscaled.png
#   - Always PNG (lossless) — no quality loss before the next step
#
# USAGE:
#   python 01_upscale.py                         # all images in input/
#   python 01_upscale.py --file photo.jpg        # single file
#   python 01_upscale.py --factor 2              # override scale factor
#   python 01_upscale.py --tile 256              # smaller tiles (low VRAM)
#   python 01_upscale.py --model RealESRGAN_x4plus_anime_6B  # artwork
#
# DEPENDENCIES: realesrgan, basicsr, opencv-python, Pillow, torch, python-dotenv
#
# NOTES:
#   - CUDA strongly recommended. CPU mode works but is 5–15 min per image.
#   - Models folder is gitignored — downloaded automatically on first run.
#   - Do not upscale above 4x (diminishing returns, very large intermediate files).
#   - Real-ESRGAN expects BGR input (OpenCV convention). Conversion is handled here.
# =============================================================

from pathlib import Path
import argparse
import sys
import time
import os

# Load .env before anything else so all os.getenv calls find the right values.
# This must happen before the utils imports because file_utils.py also reads env vars.
from dotenv import load_dotenv

# pipeline/ is the parent of this file
PIPELINE_DIR = Path(__file__).resolve().parent
load_dotenv(PIPELINE_DIR / ".env")

# =============================================================
# DEPENDENCY CHECKS
# Guard against missing packages with clear, actionable messages
# rather than cryptic ImportError tracebacks.
# =============================================================

try:
    import torch
except ImportError:
    print("ERROR: torch is not installed.")
    print("       Run: pip install torch torchvision")
    sys.exit(1)

try:
    import cv2
except ImportError:
    print("ERROR: opencv-python is not installed.")
    print("       Run: pip install opencv-python")
    sys.exit(1)

try:
    from basicsr.archs.rrdbnet_arch import RRDBNet
    from basicsr.utils.download_util import load_file_from_url
    from realesrgan import RealESRGANer
except ImportError:
    print("ERROR: Real-ESRGAN or basicsr is not installed.")
    print(
        "       Install with: "
        "pip install git+https://github.com/xinntao/Real-ESRGAN.git"
    )
    sys.exit(1)

try:
    from tqdm import tqdm
except ImportError:
    print("ERROR: tqdm is not installed. Run: pip install tqdm")
    sys.exit(1)

# Pipeline utilities — these are safe to import after load_dotenv() above
from utils.file_utils import (
    build_output_path,
    get_input_dir,
    list_input_images,
    resolve_run_name,
)
from utils.image_utils import get_image_info


# =============================================================
# MODEL REGISTRY
# =============================================================

# Each entry defines everything needed to download and instantiate a model variant.
# num_block must match the weight file — mixing them causes silent garbage output.
# scale is the native output multiplier; outscale in enhance() can override it.
MODEL_CONFIGS: dict[str, dict] = {
    "RealESRGAN_x4plus": {
        "url": (
            "https://github.com/xinntao/Real-ESRGAN/releases/download"
            "/v0.1.0/RealESRGAN_x4plus.pth"
        ),
        "scale": 4,
        "num_block": 23,
        "description": "General photo upscaling — recommended for portraits",
    },
    "RealESRGAN_x2plus": {
        "url": (
            "https://github.com/xinntao/Real-ESRGAN/releases/download"
            "/v0.2.1/RealESRGAN_x2plus.pth"
        ),
        "scale": 2,
        "num_block": 23,
        "description": "2x upscaling for already high-resolution input",
    },
    "RealESRGAN_x4plus_anime_6B": {
        "url": (
            "https://github.com/xinntao/Real-ESRGAN/releases/download"
            "/v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth"
        ),
        "scale": 4,
        "num_block": 6,
        "description": "4x upscaling for illustrations, logos, and artwork",
    },
}

# Default model for portrait photos (as recommended in INSTRUCTIONS.md section 24)
DEFAULT_MODEL = "RealESRGAN_x4plus"

# Where model weight files are cached locally after first download
MODELS_DIR = PIPELINE_DIR / "models" / "realesrgan"


# =============================================================
# DEVICE RESOLUTION
# =============================================================

def resolve_device(requested: str) -> str:
    """
    Confirm the computation device is actually available.

    If CUDA is requested but not available, falls back to CPU and
    prints a clear warning so the operator knows upscaling will be slow.

    Args:
        requested: 'cuda' or 'cpu' from DEVICE in .env or --device CLI arg

    Returns:
        'cuda' if CUDA is available and was requested, otherwise 'cpu'
    """
    if requested.lower() == "cuda":
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            print(f"  Device:  cuda  ({gpu_name})")
            return "cuda"
        print("  Device:  cpu  (CUDA requested but not available — falling back)")
        print("           Upscaling on CPU is very slow: expect 5–15 min per image.")
        return "cpu"

    print("  Device:  cpu")
    return "cpu"


# =============================================================
# MODEL LOADING
# =============================================================

def load_model(model_name: str, device: str, tile: int) -> RealESRGANer:
    """
    Download (if needed) and instantiate a RealESRGANer model.

    Weight files are saved to MODELS_DIR and reused on subsequent runs.
    The tile parameter controls whether large images are split into patches
    to avoid GPU out-of-memory errors — set tile=0 only for small images.

    Args:
        model_name: Key in MODEL_CONFIGS, e.g. 'RealESRGAN_x4plus'
        device:     'cuda' or 'cpu'
        tile:       Tile size in pixels (0 = process whole image at once)

    Returns:
        Configured RealESRGANer ready for inference
    """
    if model_name not in MODEL_CONFIGS:
        raise ValueError(
            f"Unknown model '{model_name}'. "
            f"Available models: {list(MODEL_CONFIGS.keys())}"
        )

    config = MODEL_CONFIGS[model_name]
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    local_model_path = MODELS_DIR / f"{model_name}.pth"

    if not local_model_path.exists():
        # First run — download from GitHub Releases.
        # load_file_from_url from basicsr handles resumable download and progress bar.
        print(f"  Downloading model '{model_name}'...")
        print(f"  Saving to: {local_model_path}")
        load_file_from_url(
            url=config["url"],
            model_dir=str(MODELS_DIR),
            progress=True,
            file_name=f"{model_name}.pth",
        )
    else:
        print(f"  Model cached: {local_model_path.name}")

    # RRDBNet is the backbone architecture shared by all Real-ESRGAN variants.
    # num_block and scale must match the downloaded weights exactly.
    model_arch = RRDBNet(
        num_in_ch=3,
        num_out_ch=3,
        num_feat=64,
        num_block=config["num_block"],
        num_grow_ch=32,
        scale=config["scale"],
    )

    # fp16 (half precision) cuts VRAM usage roughly in half on GPU with negligible
    # quality difference. CPU does not support fp16 — must stay on fp32.
    use_half_precision = device == "cuda"

    upsampler = RealESRGANer(
        scale=config["scale"],
        model_path=str(local_model_path),
        model=model_arch,
        tile=tile,
        tile_pad=10,      # overlap between tiles prevents visible seam lines at tile edges
        pre_pad=0,
        half=use_half_precision,
    )

    return upsampler


# =============================================================
# SINGLE-IMAGE UPSCALING
# =============================================================

def upscale_image(
    image_path: Path,
    upsampler: RealESRGANer,
    outscale: int,
    run: str,
) -> Path:
    """
    Upscale one image and save the result as a lossless PNG.

    Real-ESRGAN works in OpenCV BGR format internally. This function handles
    the conversion from whatever format is on disk → BGR for the model →
    BGR written directly to PNG via cv2.imwrite. No RGB round-trip is needed
    when saving with OpenCV.

    The 'outscale' parameter can differ from the model's native scale.
    For example, a 4x model with outscale=2 upscales internally to 4x and
    then downsamples to 2x — this produces higher quality than a native 2x
    model because more detail is extracted before downsampling.

    Args:
        image_path: Path to the source image file
        upsampler:  Loaded RealESRGANer instance
        outscale:   Final output scale factor (1–4 recommended)

    Returns:
        Path to the saved upscaled PNG file
    """
    # Print input info so the operator can confirm resolution before waiting
    info = get_image_info(image_path)
    tqdm.write(
        f"  Input:   {image_path.name}  "
        f"{info['width']} x {info['height']} px  |  "
        f"{info['file_size_mb']} MB  |  {info['mode']}"
    )

    t_start = time.perf_counter()

    try:
        # IMREAD_UNCHANGED preserves alpha channel if present (e.g. PNG with transparency).
        # Real-ESRGAN handles RGBA internally — it upscales alpha separately.
        img_bgr = cv2.imread(str(image_path), cv2.IMREAD_UNCHANGED)

        if img_bgr is None:
            raise RuntimeError(
                "cv2.imread returned None — the file may be corrupt, "
                "empty, or an unsupported format."
            )

        # enhance() runs the model and returns a BGR uint8 array.
        # outscale controls the final output resolution; the model always
        # runs at its native scale then resizes to match outscale.
        output_bgr, _ = upsampler.enhance(img_bgr, outscale=outscale)

    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(
            f"Real-ESRGAN inference failed on '{image_path.name}': {exc}"
        ) from exc

    elapsed = time.perf_counter() - t_start
    output_h, output_w = output_bgr.shape[:2]
    tqdm.write(
        f"  Output:  {output_w} x {output_h} px  |  "
        f"{outscale}x scale  |  {elapsed:.1f}s"
    )

    output_path = build_output_path(image_path.name, "upscaled", "png", run=run)

    # cv2.imwrite writes BGR arrays natively — no channel swap needed before saving
    success = cv2.imwrite(str(output_path), output_bgr)
    if not success:
        raise RuntimeError(
            f"cv2.imwrite failed to write to '{output_path}'. "
            "Check that the output directory exists and is writable."
        )

    tqdm.write(f"  Saved:   {output_path.name}")
    return output_path


# =============================================================
# CLI ARGUMENT PARSING
# =============================================================

def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments.

    All arguments are optional — .env values are used as defaults so the
    script works with zero arguments after the environment is configured.
    CLI arguments always override .env values when both are present.
    """
    env_factor = os.getenv("UPSCALE_FACTOR", "4")
    env_device = os.getenv("DEVICE", "cpu")

    parser = argparse.ArgumentParser(
        description="Step 01 — Upscale source images with Real-ESRGAN.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python 01_upscale.py\n"
            "  python 01_upscale.py --file portrait.jpg\n"
            "  python 01_upscale.py --factor 2 --tile 256\n"
            "  python 01_upscale.py --model RealESRGAN_x4plus_anime_6B\n"
        ),
    )

    parser.add_argument(
        "--file",
        type=str,
        default=None,
        metavar="FILENAME",
        help=(
            "Process a single file instead of the whole input/ folder. "
            "Provide just the filename, e.g. portrait.jpg"
        ),
    )
    parser.add_argument(
        "--factor",
        type=int,
        default=None,
        choices=[2, 4],
        metavar="N",
        help=(
            f"Output scale factor: 2 or 4. "
            f"Overrides UPSCALE_FACTOR in .env (currently: {env_factor})."
        ),
    )
    parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_MODEL,
        choices=list(MODEL_CONFIGS.keys()),
        help=f"Model variant to use (default: {DEFAULT_MODEL}).",
    )
    parser.add_argument(
        "--tile",
        type=int,
        default=400,
        metavar="PIXELS",
        help=(
            "Tile size for processing large images (default: 400). "
            "Reduce to 256 or lower if you get out-of-memory errors. "
            "Set to 0 to process the whole image at once (may OOM on large input)."
        ),
    )
    parser.add_argument(
        "--device",
        type=str,
        default=None,
        choices=["cuda", "cpu"],
        help=(
            f"Computation device. "
            f"Overrides DEVICE in .env (currently: {env_device})."
        ),
    )
    parser.add_argument(
        "--run",
        type=str,
        default=None,
        metavar="NAME",
        help=(
            "Run subfolder name, e.g. try_02. "
            "Auto-increments to the next available try_XX if omitted."
        ),
    )

    return parser.parse_args()


# =============================================================
# MAIN ENTRY POINT
# =============================================================

def main() -> None:
    args = parse_args()

    # Resolve final settings — CLI overrides .env, .env overrides hardcoded defaults
    upscale_factor = args.factor if args.factor is not None else int(os.getenv("UPSCALE_FACTOR", "4"))
    device_setting  = args.device  if args.device  is not None else os.getenv("DEVICE", "cpu")
    model_name = args.model

    print("=" * 60)
    print("K9 Crystal Pipeline  —  Step 01: Upscale")
    print("=" * 60)
    print(f"  Model:   {model_name}")
    print(f"           {MODEL_CONFIGS[model_name]['description']}")
    print(f"  Scale:   {upscale_factor}x")
    print(f"  Tile:    {args.tile if args.tile > 0 else 'disabled (full image at once)'}")

    # Verify CUDA availability and print final device choice
    device = resolve_device(device_setting)
    print()

    # -------------------------------------------------------
    # Collect images to process
    # -------------------------------------------------------
    if args.file:
        # Single-file mode: look in INPUT_DIR for the given filename
        single_path = get_input_dir() / args.file
        if not single_path.exists():
            print(f"ERROR: File not found: {single_path}")
            print(f"       Drop the file into the input/ folder and re-run.")
            sys.exit(1)
        images_to_process = [single_path]
    else:
        images_to_process = list_input_images()
        if not images_to_process:
            print("No images found in input/.")
            print("Drop .jpg or .png files there and re-run.")
            sys.exit(0)

    print(f"Processing {len(images_to_process)} image(s).\n")

    # -------------------------------------------------------
    # Load the model — done once, reused for every image
    # Loading is slow (~5–10 s) so it must not happen inside the loop
    # -------------------------------------------------------
    print("Loading model weights...")
    upsampler = load_model(model_name, device, tile=args.tile)
    print("Model ready.\n")

    # -------------------------------------------------------
    # Process images
    # tqdm shows overall progress; per-image details print inside upscale_image()
    # -------------------------------------------------------
    total_start = time.perf_counter()
    success_count = 0
    failed: list[str] = []

    progress_bar = tqdm(
        images_to_process,
        desc="Upscaling",
        unit="img",
        leave=True,
        dynamic_ncols=True,
    )

    # Resolve run name once so every image in this batch lands in the same folder
    tag = Path(args.file).stem if args.file else None
    run = resolve_run_name("upscaled", args.run, tag=tag)
    print(f"Run:     {run}  →  output/upscaled/{run}/\n")

    for image_path in progress_bar:
        progress_bar.set_description(f"Upscaling: {image_path.name}")
        try:
            upscale_image(image_path, upsampler, outscale=upscale_factor, run=run)
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
    print(f"Step 01 complete.")
    print(f"  Upscaled:  {success_count} image(s)")
    if failed:
        print(f"  Failed:    {len(failed)} image(s)")
        for name in failed:
            print(f"    - {name}")
    print(f"  Total time: {total_elapsed:.1f}s")
    print(f"  Output:    output/upscaled/{run}/")
    print()
    print("Next step: python 02_remove_bg.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
