# =============================================================
# 02_depth_estimate.py — Depth map generation
# =============================================================
# PURPOSE:
#   Second step. Generates a 16-bit grayscale depth map from the
#   prepared (background-removed, resized) image. The depth map
#   encodes per-pixel distance from the camera — white = closest
#   (nose tip), black = furthest. This is the foundation of the
#   entire 3D mesh.
#
# DEPTH MODEL:
#   Default: Depth Anything V2 Large (depth-anything/Depth-Anything-V2-Large-hf)
#   No ZoeDepth in this pipeline — Depth Anything V2 gives better
#   portrait quality and does not require timm version pins.
#
# PROFILES (edge masking):
#   standard              Binary hard cut at alpha=0
#   soft_edges_v1         Alpha value used as linear weight
#   soft_edges_feathered  Alpha weight + Gaussian blur — smoothest edges
#
# INPUTS:  output/prepared/{run}/*_prepared.png (RGBA)
# OUTPUTS: output/depth_maps/{run}/{stem}_{model}_{profile}_depth.png (16-bit)
#          output/depth_maps/{run}/{stem}_{model}_{profile}_preview.png (8-bit inferno)
#
# USAGE:
#   python 02_depth_estimate.py
#   python 02_depth_estimate.py --model midas
#   python 02_depth_estimate.py --model depth_anything_v2 --size Large
#   python 02_depth_estimate.py --profile soft_edges_feathered
#   python 02_depth_estimate.py --from-run try_01 --run try_01
#
# DEPENDENCIES: torch, transformers, timm, einops, Pillow, numpy, scipy, tqdm
# =============================================================

from pathlib import Path
import argparse
import sys
import time
import os

from dotenv import load_dotenv

PIPELINE_DIR = Path(__file__).resolve().parent
load_dotenv(PIPELINE_DIR / ".env")

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
from utils.image_utils import get_image_info, save_depth_map, save_preview_depth


# =============================================================
# MODEL REGISTRY
# =============================================================

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
    "depth_pro": {
        "type": "transformers",
        "repo": "apple/DepthPro",
        "description": "Apple Depth Pro — sharp boundaries, metric depth (registry stub)",
    },
    "marigold": {
        "type": "diffusers",
        "repo": "prs-eth/marigold-lcm-v1-0",
        "description": "Diffusion-based depth — highest surface detail, slower (registry stub)",
    },
}

DEFAULT_MODEL = os.getenv("DEPTH_MODEL", "depth_anything_v2")
DEFAULT_SIZE  = os.getenv("DEPTH_ANYTHING_MODEL_SIZE", "Large")


# =============================================================
# DEPTH PROCESSING PROFILES
# =============================================================

DEPTH_PROFILES: dict[str, dict] = {
    "standard": {
        "mask_mode": "binary",
        "feather_sigma": 0.0,
        "description": "Binary hard cut — pixels with alpha=0 set to 0 depth.",
        "status": "stable",
    },
    "soft_edges_v1": {
        "mask_mode": "alpha_weight",
        "feather_sigma": 0.0,
        "description": "Alpha value used as linear weight (0.0-1.0).",
        "status": "experimental",
    },
    "soft_edges_feathered": {
        "mask_mode": "alpha_weight",
        "feather_sigma": 10.0,
        "description": "Alpha weight with Gaussian blur (sigma=10px). Smoothest edges.",
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
    Load the requested depth estimation model.

    Returns (model, processor). ZoeDepth is NOT supported in this pipeline —
    use pipeline-02-zoedepth for ZoeDepth testing.
    """
    if model_name not in MODEL_REGISTRY:
        available = ", ".join(MODEL_REGISTRY.keys())
        raise ValueError(f"Unknown model '{model_name}'. Available: {available}")

    config = MODEL_REGISTRY[model_name]
    print(f"  Model:   {model_name}  —  {config['description']}")

    if model_name == "depth_anything_v2":
        if size not in config["sizes"]:
            raise ValueError(f"Invalid size '{size}'. Use: {config['sizes']}")
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

    if model_name in ("depth_pro", "marigold"):
        raise NotImplementedError(
            f"Model '{model_name}' is registered but not yet implemented. "
            "Use depth_anything_v2 or midas."
        )

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
    Run depth estimation on one image and return a float32 array.

    Returns float32 (H, W) array where 1.0 = closest, 0.0 = furthest.
    Alpha masking is applied according to the selected profile.
    """
    rgba = Image.open(image_path).convert("RGBA")
    rgb  = rgba.convert("RGB")

    alpha_arr = np.array(rgba)[:, :, 3]
    orig_w, orig_h = rgb.size

    inputs = processor(images=rgb, return_tensors="pt")
    inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.no_grad():
        outputs = model(**inputs)
        predicted_depth = outputs.predicted_depth

    depth_tensor = torch.nn.functional.interpolate(
        predicted_depth.unsqueeze(1),
        size=(orig_h, orig_w),
        mode="bilinear",
        align_corners=False,
    ).squeeze()

    depth_np = depth_tensor.cpu().numpy().astype(np.float32)

    # Normalize: transformer models output disparity (larger = closer)
    d_min = depth_np.min()
    d_max = depth_np.max()

    if d_max > d_min:
        depth_norm = (depth_np - d_min) / (d_max - d_min)
    else:
        depth_norm = np.zeros_like(depth_np, dtype=np.float32)

    # Apply alpha masking
    prof = DEPTH_PROFILES[profile]
    mask_mode = prof["mask_mode"]
    feather_sigma = feather_override if feather_override is not None else float(prof["feather_sigma"])

    if mask_mode == "binary":
        depth_norm[alpha_arr == 0] = 0.0

    elif mask_mode == "alpha_weight":
        from scipy.ndimage import gaussian_filter
        alpha_weight = alpha_arr.astype(np.float32) / 255.0
        if feather_sigma > 0.0:
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
    profile_tag: str,
) -> tuple[Path, Path]:
    """Save 16-bit depth PNG and 8-bit inferno colormap preview."""
    stem = Path(source_filename).stem
    tagged_stem = f"{stem}_{model_name}_{profile_tag}"

    depth_path = build_output_path(f"{tagged_stem}.png", "depth", "png", run=run)
    save_depth_map(depth, depth_path)
    tqdm.write(f"  16-bit:  {depth_path.name}")

    preview_path = depth_path.parent / f"{tagged_stem}_preview.png"
    save_preview_depth(depth, preview_path)
    tqdm.write(f"  Preview: {preview_path.name}")

    return depth_path, preview_path


# =============================================================
# INPUT SCANNER
# =============================================================

def list_prepared_images(run: str) -> list[Path]:
    """Return all _prepared.png files from output/prepared/{run}/ sorted alphabetically."""
    prepared_dir = get_output_dir("prepared", run)

    images = sorted(
        [p for p in prepared_dir.iterdir() if p.is_file() and p.name.endswith("_prepared.png")],
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
        description="Step 02 — Generate depth map with Depth Anything V2 or MiDaS.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python 02_depth_estimate.py\n"
            "  python 02_depth_estimate.py --model midas\n"
            "  python 02_depth_estimate.py --model depth_anything_v2 --size Large\n"
            "  python 02_depth_estimate.py --profile soft_edges_feathered\n"
            "  python 02_depth_estimate.py --from-run try_01 --run try_01\n"
        ),
    )
    parser.add_argument("--file", type=str, default=None, metavar="FILENAME",
                        help="Process a single file from the prepared run folder.")
    parser.add_argument("--model", type=str, default=env_model,
                        choices=list(MODEL_REGISTRY.keys()),
                        help=f"Depth model to use (default: {env_model}).")
    parser.add_argument("--size", type=str, default=env_size,
                        choices=["Small", "Base", "Large"],
                        help=f"Model size for depth_anything_v2 (default: {env_size}).")
    parser.add_argument("--device", type=str, default=None, choices=["cuda", "cpu"],
                        help=f"Computation device (default from .env: {env_device}).")
    parser.add_argument("--from-run", type=str, default=None, metavar="NAME",
                        help="Which prepared run to read from. Defaults to latest.")
    parser.add_argument("--run", type=str, default=None, metavar="NAME",
                        help="Output run subfolder name. Auto-increments if omitted.")
    parser.add_argument("--profile", type=str, default=env_profile,
                        choices=list(DEPTH_PROFILES.keys()),
                        help=f"Edge masking profile (default: {env_profile}).")
    parser.add_argument("--feather", type=float, default=None, metavar="SIGMA",
                        help="Override feather_sigma for the selected profile.")
    return parser.parse_args()


# =============================================================
# MAIN ENTRY POINT
# =============================================================

def main() -> None:
    args = parse_args()

    device_setting = args.device if args.device is not None else os.getenv("DEVICE", "cuda")

    print("=" * 60)
    print("K9 Crystal Pipeline 03 Pro  —  Step 02: Depth Estimation")
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

    input_run  = latest_run_name("prepared", args.from_run)
    tag = Path(args.file).stem if args.file else None
    output_run = resolve_run_name("depth", args.run, tag=tag)
    print(f"  Input:   output/prepared/{input_run}/")
    print(f"  Output:  output/depth_maps/{output_run}/\n")

    if args.file:
        single_path = get_output_dir("prepared", input_run) / args.file
        if not single_path.exists():
            print(f"ERROR: File not found: {single_path}")
            sys.exit(1)
        images_to_process = [single_path]
    else:
        images_to_process = list_prepared_images(input_run)
        if not images_to_process:
            print("ERROR: No _prepared.png files found. Run step 01 first: python 01_prepare.py")
            sys.exit(1)

    print(f"Processing {len(images_to_process)} image(s).\n")

    print("Loading depth model...")
    t_load = time.perf_counter()
    model, processor = load_depth_model(args.model, args.size, device)
    print(f"Model ready. ({time.perf_counter() - t_load:.1f}s)\n")

    total_start = time.perf_counter()
    success_count = 0
    failed: list[str] = []

    progress_bar = tqdm(images_to_process, desc="Depth estimation", unit="img", leave=True, dynamic_ncols=True)

    for image_path in progress_bar:
        progress_bar.set_description(f"Processing: {image_path.name}")
        try:
            info = get_image_info(image_path)
            tqdm.write(f"  Input:   {image_path.name}  {info['width']} x {info['height']} px")

            t_start = time.perf_counter()
            depth = estimate_depth(image_path, model, processor, args.model, device, args.profile, args.feather)
            elapsed = time.perf_counter() - t_start

            tqdm.write(
                f"  Depth:   min={depth.min():.3f}  max={depth.max():.3f}  "
                f"mean={depth.mean():.3f}  |  {elapsed:.1f}s"
            )

            feather_tag = f"_f{int(args.feather)}" if args.feather is not None else ""
            profile_tag = f"{args.profile}{feather_tag}"
            save_depth_outputs(depth, image_path.name, args.model, output_run, profile_tag)
            success_count += 1

        except Exception as exc:
            tqdm.write(f"\nERROR — '{image_path.name}': {exc}")
            tqdm.write("  Skipping this file and continuing.\n")
            failed.append(image_path.name)

    total_elapsed = time.perf_counter() - total_start

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
    print("  IMPORTANT: Inspect the _preview.png before continuing.")
    print("             Warm colors = close, cool/dark = far.")
    print("             Nose tip should be the brightest point on a portrait.")
    print()
    print("Next step: python 03_mesh_generate.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
