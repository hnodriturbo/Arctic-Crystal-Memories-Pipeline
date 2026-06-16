# =============================================================
# 02_depth_estimate.py — Depth map generation
# =============================================================
# PURPOSE:
#   Second step. Generates a grayscale depth map from the
#   prepared (background-removed, resized) image. The depth map encodes how far
#   each pixel is from the camera — white = closest (nose tip),
#   black = furthest (back of head / edges). This depth map
#   is the foundation of the entire 3D mesh.
#
# WHY DEPTH QUALITY IS EVERYTHING:
#   Every problem in the final crystal engraving traces back
#   to depth map quality. A flat nose, a collapsed forehead,
#   or ear-level depth all come from a bad depth map. This step
#   deserves the most testing, manual correction, and iteration.
#
# MODELS AVAILABLE (configured via DEPTH_MODEL in .env):
#
#   depth_anything_v2 (default, recommended for portraits)
#     - Best general purpose depth model as of 2024-2025
#     - Three sizes: Small / Base / Large (DEPTH_ANYTHING_MODEL_SIZE)
#     - Large = best quality, ~4GB VRAM, ~30s/image
#     - HuggingFace: depth-anything/Depth-Anything-V2-{Size}-hf
#
#   midas (reliable fallback)
#     - Well-established, good for portraits
#     - DPT_Large variant used
#     - HuggingFace: Intel/dpt-large
#
#   zoedepth (metric depth)
#     - Produces depth in real-world scale (meters)
#     - Better for objects with known size
#     - Use when relative depth is not enough
#
# INPUTS:
#   - Prepared PNGs from output/prepared/{run}/  (RGBA, already resized)
#   - DEPTH_MODEL and DEPTH_ANYTHING_MODEL_SIZE from .env
#
# OUTPUTS:
#   - 16-bit grayscale PNG: output/depth_maps/{run}/{stem}_depth.png
#     (16-bit preserves full precision — critical for mesh quality)
#   - 8-bit preview PNG: output/depth_maps/{run}/{stem}_depth_preview.png
#     (human-readable version for visual inspection with colormap)
#
# USAGE:
#   python 02_depth_estimate.py
#   python 02_depth_estimate.py --file photo_prepared.png
#   python 02_depth_estimate.py --model midas
#   python 02_depth_estimate.py --model depth_anything_v2 --size Large
#   python 02_depth_estimate.py --from-run try_01 --run try_01
#   python 02_depth_estimate.py --profile soft_edges_feathered
#
# PROFILES (edge masking behaviour — see DEPTH_DECISIONS.md):
#   standard              Binary hard cut at alpha > 0 (original behaviour)
#   soft_edges_v1         Alpha value used as linear weight — gradual fade
#   soft_edges_feathered  Alpha weight + Gaussian blur on mask — smoothest edges
#
# DEPENDENCIES: torch, torchvision, transformers, timm, einops,
#               Pillow, numpy, python-dotenv, tqdm
#
# NOTES:
#   - Models download automatically on first run (~1–4GB each).
#   - 16-bit output is essential — do not convert to 8-bit here.
#   - The depth map should always be inspected before step 04.
#   - Manual corrections: open _depth.png in Photoshop, paint
#     corrections with white (closer) or black (further) brush,
#     save back as 16-bit PNG. Normal and expected workflow.
#   - Alpha mask from bg_removed step is applied after inference —
#     background pixels (alpha=0) are zeroed out in the depth map.
# =============================================================

from pathlib import Path
import argparse
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
    import numpy as np
except ImportError:
    print("ERROR: numpy is not installed. Run: pip install numpy")
    sys.exit(1)

try:
    import torch
except ImportError:
    print("ERROR: torch is not installed.")
    print("       Run: pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124")
    sys.exit(1)

try:
    from PIL import Image
except ImportError:
    print("ERROR: Pillow is not installed. Run: pip install Pillow")
    sys.exit(1)

try:
    from transformers import AutoImageProcessor, AutoModelForDepthEstimation
except ImportError:
    print("ERROR: transformers is not installed. Run: pip install transformers")
    sys.exit(1)

try:
    from tqdm import tqdm
except ImportError:
    print("ERROR: tqdm is not installed. Run: pip install tqdm")
    sys.exit(1)

from utils.file_utils import (
    build_output_path,
    get_output_dir,
    latest_run_name,
    resolve_run_name,
)
from utils.image_utils import get_image_info, save_depth_map


# =============================================================
# MODEL REGISTRY
# =============================================================

# Maps model name → HuggingFace repo pattern or torch.hub identifier.
# size_map is used only for depth_anything_v2 where the repo name encodes size.
MODEL_REGISTRY: dict[str, dict] = {
    "depth_anything_v2": {
        "type": "transformers",
        "repo_pattern": "depth-anything/Depth-Anything-V2-{size}-hf",
        "sizes": ["Small", "Base", "Large"],
        "description": "Best general-purpose depth model for portraits (2024-2025)",
    },
    "midas": {
        "type": "transformers",
        "repo": "Intel/dpt-large",
        "description": "Reliable DPT-Large model, good portrait fallback",
    },
    "zoedepth": {
        "type": "torchhub",
        "repo": "isl-org/ZoeDepth",
        "variant": "ZoeD_NK",
        "description": "Metric depth in real-world scale (meters)",
    },
    "depth_pro": {
        "type": "transformers",
        "repo": "apple/DepthPro",
        "description": "Apple Depth Pro — sharp boundaries, metric depth, zero-shot",
    },
    "marigold": {
        "type": "diffusers",
        "repo": "prs-eth/marigold-lcm-v1-0",
        "description": "Diffusion-based depth — highest surface detail, slower than transformer models",
    },
    "patchfusion": {
        "type": "custom",
        "repo": "zhyever/PatchFusion",
        "description": "High-resolution tile-based depth fusion — requires custom loader setup",
    },
}

DEFAULT_MODEL = os.getenv("DEPTH_MODEL", "depth_anything_v2")
DEFAULT_SIZE  = os.getenv("DEPTH_ANYTHING_MODEL_SIZE", "Large")


# =============================================================
# DEPTH PROCESSING PROFILES
# =============================================================
# Each profile controls how the alpha mask from step 02 is applied
# to the raw depth output. Profiles are additive — old ones are never
# removed. Select via --profile CLI arg or DEPTH_PROFILE in .env.
#
# See DEPTH_DECISIONS.md for the reasoning behind each profile.

DEPTH_PROFILES: dict[str, dict] = {
    "standard": {
        "mask_mode": "binary",
        "feather_sigma": 0.0,
        "description": "Binary hard cut — pixels with alpha=0 set to 0 depth. Original behaviour.",
        "added": "2026-05-28",
        "status": "stable",
    },
    "soft_edges_v1": {
        "mask_mode": "alpha_weight",
        "feather_sigma": 0.0,
        "description": "Alpha value used as linear weight (0.0–1.0). Semi-transparent edge pixels get proportionally less depth.",
        "added": "2026-05-29",
        "status": "experimental",
    },
    "soft_edges_feathered": {
        "mask_mode": "alpha_weight",
        "feather_sigma": 10.0,
        "description": "Alpha weight with Gaussian blur (sigma=10px). Smooths the transition zone even on binary masks.",
        "added": "2026-05-29",
        "status": "experimental",
    },
}

DEFAULT_PROFILE = os.getenv("DEPTH_PROFILE", "standard")


# =============================================================
# DEVICE RESOLUTION
# =============================================================

def resolve_device(requested: str) -> str:
    if requested.lower() == "cuda":
        if torch.cuda.is_available():
            print(f"  Device:  cuda  ({torch.cuda.get_device_name(0)})")
            return "cuda"
        print("  Device:  cpu  (CUDA requested but not available — falling back)")
        print("           Depth estimation on CPU is very slow.")
        return "cpu"
    print("  Device:  cpu")
    return "cpu"


# =============================================================
# MODEL LOADING
# =============================================================

def load_depth_model(model_name: str, size: str, device: str):
    """
    Download (if needed) and load the requested depth estimation model.

    Returns a (model, processor) tuple. For ZoeDepth, processor is None
    because it handles its own preprocessing internally.

    Args:
        model_name: Key in MODEL_REGISTRY
        size:       Model size for depth_anything_v2 — 'Small', 'Base', or 'Large'
        device:     'cuda' or 'cpu'

    Returns:
        Tuple of (model, processor) — processor is None for zoedepth
    """
    if model_name not in MODEL_REGISTRY:
        available = ", ".join(MODEL_REGISTRY.keys())
        raise ValueError(f"Unknown model '{model_name}'. Available: {available}")

    config = MODEL_REGISTRY[model_name]
    print(f"  Model:   {model_name}  —  {config['description']}")

    if model_name == "depth_anything_v2":
        if size not in config["sizes"]:
            raise ValueError(
                f"Invalid size '{size}' for depth_anything_v2. "
                f"Use: {config['sizes']}"
            )
        repo = config["repo_pattern"].format(size=size)
        print(f"  Repo:    {repo}")
        print("  Loading processor and model (downloads on first run)...")
        processor = AutoImageProcessor.from_pretrained(repo)
        model = AutoModelForDepthEstimation.from_pretrained(repo)
        model = model.to(device).eval()
        return model, processor

    if model_name == "midas":
        repo = config["repo"]
        print(f"  Repo:    {repo}")
        print("  Loading processor and model (downloads on first run)...")
        processor = AutoImageProcessor.from_pretrained(repo)
        model = AutoModelForDepthEstimation.from_pretrained(repo)
        model = model.to(device).eval()
        return model, processor

    if model_name == "zoedepth":
        print("  Loading ZoeDepth via torch.hub (downloads on first run)...")
        # Patch: timm 0.9.x BeiT Block stores the drop path layer as
        # self.drop_path1, but MiDaS hub code calls self.drop_path(x).
        # Alias drop_path → drop_path1 so both names refer to the same layer.
        try:
            import timm.models.beit as _beit
            _orig_beit_init = _beit.Block.__init__
            def _patched_beit_init(self, *args, **kwargs):
                _orig_beit_init(self, *args, **kwargs)
                if not hasattr(self, "drop_path") and hasattr(self, "drop_path1"):
                    self.drop_path = self.drop_path1
            _beit.Block.__init__ = _patched_beit_init
        except Exception:
            pass  # patch is best-effort

        model: torch.nn.Module = torch.hub.load(  # type: ignore[assignment]
            config["repo"],
            config["variant"],
            pretrained=True,
        )
        model = model.to(device).eval()
        return model, None

    raise ValueError(f"Unhandled model '{model_name}'")


# =============================================================
# DEPTH INFERENCE
# =============================================================

def estimate_depth(
    image_path: Path,
    model,
    processor,
    model_name: str,
    device: str,
    profile: str = "standard",
    feather_override: float | None = None,
) -> np.ndarray:
    """
    Run depth estimation on one image and return a float32 depth array.

    Loads the RGBA background-removed image, separates RGB for the model
    and alpha for masking. Runs inference, resizes output back to the
    original image dimensions, then applies the selected profile's masking.

    The returned array is normalized so 1.0 = closest to camera (nose tip)
    and 0.0 = furthest (background / edges). This convention matches the
    16-bit PNG encoding used in save_depth_map(): 65535 = closest.

    Args:
        image_path: Path to the _nobg.png RGBA image from step 02
        model:      Loaded depth model
        processor:  Model processor (None for ZoeDepth)
        model_name: Key in MODEL_REGISTRY — controls preprocessing path
        device:     'cuda' or 'cpu'
        profile:    Key in DEPTH_PROFILES — controls edge masking behaviour

    Returns:
        Float32 numpy array shape (H, W), values 0.0–1.0
    """
    rgba = Image.open(image_path).convert("RGBA")
    rgb  = rgba.convert("RGB")

    alpha_arr = np.array(rgba)[:, :, 3]

    orig_w, orig_h = rgb.size

    if model_name in ("depth_anything_v2", "midas"):
        inputs = processor(images=rgb, return_tensors="pt")
        inputs = {k: v.to(device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = model(**inputs)
            # predicted_depth shape: (1, H_model, W_model)
            predicted_depth = outputs.predicted_depth

        # Bilinear upsample back to original image resolution
        depth_tensor = torch.nn.functional.interpolate(
            predicted_depth.unsqueeze(1),
            size=(orig_h, orig_w),
            mode="bilinear",
            align_corners=False,
        ).squeeze()

        depth_np = depth_tensor.cpu().numpy().astype(np.float32)

    elif model_name == "zoedepth":
        # ZoeDepth expects a PIL RGB image directly
        with torch.no_grad():
            depth_np = model.infer_pil(rgb)

        # infer_pil returns metric depth in meters as float32 H×W array.
        # Resize to original dimensions if the model returned a different size.
        if depth_np.shape != (orig_h, orig_w):
            depth_pil = Image.fromarray(depth_np).resize(
                (orig_w, orig_h), Image.Resampling.BILINEAR
            )
            depth_np = np.array(depth_pil, dtype=np.float32)

    else:
        raise ValueError(f"Unhandled model in inference: {model_name}")

    # Raw model output is disparity (closer = higher value) for transformer models,
    # and metric depth (closer = lower value in meters) for ZoeDepth.
    # Normalize to 0.0–1.0 where 1.0 = closest in both cases.
    d_min = depth_np.min()
    d_max = depth_np.max()

    if d_max > d_min:
        if model_name == "zoedepth":
            # ZoeDepth: smaller value = closer → invert after normalization
            depth_norm = 1.0 - (depth_np - d_min) / (d_max - d_min)
        else:
            # Transformer models: larger disparity = closer → keep as-is
            depth_norm = (depth_np - d_min) / (d_max - d_min)
    else:
        depth_norm = np.zeros_like(depth_np, dtype=np.float32)

    # Apply alpha masking according to the selected profile.
    prof = DEPTH_PROFILES[profile]
    mask_mode = prof["mask_mode"]
    feather_sigma = feather_override if feather_override is not None else float(prof["feather_sigma"])

    if mask_mode == "binary":
        # Original behaviour: hard cut at alpha boundary.
        depth_norm[alpha_arr == 0] = 0.0

    elif mask_mode == "alpha_weight":
        from scipy.ndimage import gaussian_filter
        alpha_weight = alpha_arr.astype(np.float32) / 255.0
        if feather_sigma > 0.0:
            # Gaussian blur widens the fade zone — works even on binary masks.
            alpha_weight = gaussian_filter(alpha_weight, sigma=feather_sigma)
        depth_norm = depth_norm * alpha_weight

    else:
        raise ValueError(f"Unknown mask_mode '{mask_mode}' in profile '{profile}'")

    return depth_norm.astype(np.float32)


# =============================================================
# SAVE OUTPUTS
# =============================================================

def save_depth_outputs(
    depth: np.ndarray,
    source_filename: str,
    model_name: str,
    run: str,
    profile: str = "standard",
) -> tuple[Path, Path]:
    """
    Save the depth array as a 16-bit PNG and an 8-bit colormap preview.

    The 16-bit PNG is the canonical output used by step 04. The preview
    is a false-color visualization for human inspection — warm colors are
    close, cool colors are far. It should not be used as pipeline input.

    Args:
        depth:           Float32 array 0.0–1.0 from estimate_depth()
        source_filename: Original filename, e.g. 'image_01_upscaled_nobg.png'
        model_name:      Used to suffix the filename so different model runs are distinct
        run:             Run subfolder name, e.g. 'try_01'
        profile:         Profile name appended to filename for traceability

    Returns:
        Tuple of (depth_16bit_path, preview_path)
    """
    stem = Path(source_filename).stem
    # Include model + profile in filename so every combination is a distinct file
    tagged_stem = f"{stem}_{model_name}_{profile}"

    depth_path = build_output_path(f"{tagged_stem}.png", "depth", "png", run=run)
    save_depth_map(depth, depth_path)
    tqdm.write(f"  16-bit:  {depth_path.name}")

    # 8-bit preview with matplotlib colormap (no matplotlib dependency — manual colormap)
    depth_uint8 = (depth * 255).clip(0, 255).astype(np.uint8)
    preview_pil = _apply_inferno_colormap(depth_uint8)

    preview_stem = f"{tagged_stem}_preview"
    preview_path = build_output_path(f"{preview_stem}.png", "depth", "png", run=run)
    preview_pil.save(str(preview_path), format="PNG")
    tqdm.write(f"  Preview: {preview_path.name}")

    return depth_path, preview_path


def _apply_inferno_colormap(gray: np.ndarray) -> Image.Image:
    """
    Apply matplotlib's 'inferno' colormap to a uint8 grayscale array.

    Close pixels (high values) appear white/yellow.
    Far pixels (low values) appear dark purple/black.

    Args:
        gray: uint8 H×W array, 0 = far, 255 = close

    Returns:
        RGB PIL Image
    """
    import matplotlib
    colormap = matplotlib.colormaps["inferno"]
    # Normalize to 0.0-1.0, apply colormap (returns RGBA float), convert to uint8 RGB
    rgba = colormap(gray.astype(np.float32) / 255.0)
    rgb = (rgba[:, :, :3] * 255).astype(np.uint8)
    return Image.fromarray(rgb, mode="RGB")


# =============================================================
# INPUT SCANNER — bg_removed folder
# =============================================================

def list_prepared_images(run: str) -> list[Path]:
    """
    Return all _prepared.png files from output/prepared/{run}/ sorted alphabetically.

    Only files ending in _prepared.png are included — mask files are excluded.

    Args:
        run: Run subfolder name, e.g. 'try_01'

    Returns:
        Sorted list of Path objects
    """
    prepared_dir = get_output_dir("prepared", run)

    images = sorted(
        [
            p for p in prepared_dir.iterdir()
            if p.is_file() and p.name.endswith("_prepared.png")
        ],
        key=lambda p: p.name.lower(),
    )

    print(f"Found {len(images)} prepared image(s) in: {prepared_dir}")
    return images


# =============================================================
# CLI ARGUMENT PARSING
# =============================================================

def parse_args() -> argparse.Namespace:
    env_model   = os.getenv("DEPTH_MODEL", "depth_anything_v2")
    env_size    = os.getenv("DEPTH_ANYTHING_MODEL_SIZE", "Large")
    env_device  = os.getenv("DEVICE", "cuda")
    env_profile = os.getenv("DEPTH_PROFILE", "standard")

    parser = argparse.ArgumentParser(
        description="Step 02 — Generate depth map with Depth Anything V2 / MiDaS / ZoeDepth.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python 03_depth_estimate.py\n"
            "  python 03_depth_estimate.py --file image_01_upscaled_nobg.png\n"
            "  python 03_depth_estimate.py --model midas\n"
            "  python 03_depth_estimate.py --model depth_anything_v2 --size Small\n"
            "  python 03_depth_estimate.py --from-run try_03 --run try_01\n"
            "  python 03_depth_estimate.py --profile soft_edges_feathered\n"
        ),
    )

    parser.add_argument(
        "--file",
        type=str,
        default=None,
        metavar="FILENAME",
        help="Process a single file from the bg_removed run folder. Provide just the filename.",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=env_model,
        choices=list(MODEL_REGISTRY.keys()),
        help=f"Depth model to use (default: {env_model}).",
    )
    parser.add_argument(
        "--size",
        type=str,
        default=env_size,
        choices=["Small", "Base", "Large"],
        help=f"Model size for depth_anything_v2 (default: {env_size}). Ignored for other models.",
    )
    parser.add_argument(
        "--device",
        type=str,
        default=None,
        choices=["cuda", "cpu"],
        help=f"Computation device (default: from .env = {env_device}).",
    )
    parser.add_argument(
        "--from-run",
        type=str,
        default=None,
        metavar="NAME",
        help="Which bg_removed run to read from. Defaults to latest non-empty run.",
    )
    parser.add_argument(
        "--run",
        type=str,
        default=None,
        metavar="NAME",
        help="Output run subfolder name. Auto-increments to next available if omitted.",
    )
    parser.add_argument(
        "--profile",
        type=str,
        default=env_profile,
        choices=list(DEPTH_PROFILES.keys()),
        help=(
            f"Edge masking profile (default: {env_profile}). "
            "See DEPTH_DECISIONS.md for details."
        ),
    )
    parser.add_argument(
        "--feather",
        type=float,
        default=None,
        metavar="SIGMA",
        help=(
            "Override feather_sigma for the selected profile. "
            "Only applies when profile uses alpha_weight mask mode. "
            "Higher = wider fade zone (e.g. 10=subtle, 50=medium, 100=aggressive). "
            "Appended to output filename so results are kept separate."
        ),
    )

    return parser.parse_args()


# =============================================================
# MAIN ENTRY POINT
# =============================================================

def main() -> None:
    args = parse_args()

    device_setting = args.device if args.device is not None else os.getenv("DEVICE", "cuda")

    print("=" * 60)
    print("K9 Crystal Pipeline  —  Step 02: Depth Estimation")
    print("=" * 60)
    print(f"  Model:   {args.model}")
    if args.model == "depth_anything_v2":
        print(f"  Size:    {args.size}")
    print(f"  Profile: {args.profile}  —  {DEPTH_PROFILES[args.profile]['description']}")
    effective_sigma = args.feather if args.feather is not None else DEPTH_PROFILES[args.profile]["feather_sigma"]
    if DEPTH_PROFILES[args.profile]["mask_mode"] == "alpha_weight":
        print(f"  Feather: sigma={effective_sigma}px{' (override)' if args.feather is not None else ''}")

    device = resolve_device(device_setting)
    print()

    # Input: latest non-empty prepared run (or explicit --from-run)
    input_run  = latest_run_name("prepared", args.from_run)
    # Output: next available depth_maps run (or explicit --run)
    tag = Path(args.file).stem if args.file else None
    output_run = resolve_run_name("depth", args.run, tag=tag)
    print(f"  Input:   output/prepared/{input_run}/")
    print(f"  Output:  output/depth_maps/{output_run}/\n")

    # -------------------------------------------------------
    # Collect images to process
    # -------------------------------------------------------
    if args.file:
        single_path = get_output_dir("prepared", input_run) / args.file
        if not single_path.exists():
            print(f"ERROR: File not found: {single_path}")
            sys.exit(1)
        images_to_process = [single_path]
    else:
        images_to_process = list_prepared_images(input_run)
        if not images_to_process:
            print("ERROR: No _prepared.png files found in prepared output.")
            print("       Run step 01 first:  python 01_prepare.py")
            sys.exit(1)

    print(f"Processing {len(images_to_process)} image(s).\n")

    # -------------------------------------------------------
    # Load model once — reused for every image in the batch
    # -------------------------------------------------------
    print("Loading depth model...")
    t_load = time.perf_counter()
    model, processor = load_depth_model(args.model, args.size, device)
    print(f"Model ready. ({time.perf_counter() - t_load:.1f}s)\n")

    # -------------------------------------------------------
    # Process images
    # -------------------------------------------------------
    total_start = time.perf_counter()
    success_count = 0
    failed: list[str] = []

    progress_bar = tqdm(
        images_to_process,
        desc="Depth estimation",
        unit="img",
        leave=True,
        dynamic_ncols=True,
    )

    for image_path in progress_bar:
        progress_bar.set_description(f"Processing: {image_path.name}")
        try:
            info = get_image_info(image_path)
            tqdm.write(
                f"  Input:   {image_path.name}  "
                f"{info['width']} x {info['height']} px"
            )

            t_start = time.perf_counter()
            depth = estimate_depth(image_path, model, processor, args.model, device, args.profile, args.feather)
            elapsed = time.perf_counter() - t_start

            tqdm.write(
                f"  Depth:   min={depth.min():.3f}  max={depth.max():.3f}  "
                f"mean={depth.mean():.3f}  |  {elapsed:.1f}s"
            )

            feather_tag = f"_f{int(args.feather)}" if args.feather is not None else ""
            save_depth_outputs(depth, image_path.name, args.model, output_run, f"{args.profile}{feather_tag}")
            success_count += 1

        except Exception as exc:
            tqdm.write(f"\nERROR — '{image_path.name}': {exc}")
            tqdm.write("  Skipping this file and continuing.\n")
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
    print(f"  Output:    output/depth_maps/{output_run}/")
    print()
    print(
        "  IMPORTANT: Inspect the _depth_preview.png before continuing.\n"
        "             Warm colors = close, cool/dark = far.\n"
        "             Nose tip should be the brightest point on a portrait."
    )
    print()
    print("Next step: python 03_mesh_generate.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
