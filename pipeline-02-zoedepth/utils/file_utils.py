# =============================================================
# file_utils.py — File and path management helpers
# =============================================================
# PURPOSE:
#   Centralizes all file I/O operations for the pipeline.
#   Every pipeline step uses these helpers instead of writing
#   its own path logic, keeping filenames consistent and
#   output folders automatically created.
#
# RESPONSIBILITIES:
#   - Build consistent output file paths per pipeline stage
#   - Ensure output directories exist before writing
#   - Resolve INPUT_DIR and OUTPUT_DIR from .env
#   - List available images in the input folder
#
# INPUTS:  Source filename (stem), stage name, file extension
# OUTPUTS: Resolved absolute Path objects ready for use
#
# DEPENDENCIES: pathlib, python-dotenv, os
# =============================================================

from pathlib import Path
from dotenv import load_dotenv
import os

# This file lives at pipeline/utils/file_utils.py.
# Going two levels up (.parent.parent) gives us the pipeline/ directory,
# which is where .env lives and where all relative paths in .env are anchored.
PIPELINE_DIR = Path(__file__).resolve().parent.parent

# Load .env at import time so os.getenv calls in functions below always work.
# load_dotenv is idempotent — calling it multiple times (once here, once in
# the calling script) is safe and does not override variables already set.
load_dotenv(PIPELINE_DIR / ".env")

# File extensions that count as processable images throughout the pipeline.
# TIFF and BMP are included because customers occasionally supply scanned photos.
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tiff", ".bmp"}

# Maps the short stage identifier used in filenames to the actual output subfolder name.
# Keeping these separate lets the folder names stay readable in the filesystem
# while the code uses concise single-word identifiers.
# Example: stage "nobg" → folder "bg_removed" → file "photo_nobg.png"
STAGE_OUTPUT_DIRS: dict[str, str] = {
    "prepared":   "prepared",
    "depth":      "depth_maps",
    "pointcloud": "point_clouds",
    "mesh":       "meshes",
    "export":     "exports",
}


# -------------------------------------------------------------
# DIRECTORY HELPERS
# -------------------------------------------------------------

def get_input_dir() -> Path:
    """
    Return the pipeline input directory, creating it if it doesn't exist.

    Reads INPUT_DIR from .env, resolved relative to pipeline/.
    Falls back to pipeline/input/ when the variable is not set.

    Returns:
        Resolved absolute Path to the input directory
    """
    raw = os.getenv("INPUT_DIR", "./input")

    # Always resolve relative to pipeline/ regardless of the working directory
    # the user ran the script from. This keeps behaviour consistent.
    path = (PIPELINE_DIR / raw).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def _scan_run_nums(stage: str, non_empty_only: bool = False) -> list[int]:
    """Return sorted list of try_NN integers found in the stage output folder.

    Args:
        non_empty_only: When True, skip folders that contain no files.
    """
    base_raw = os.getenv("OUTPUT_DIR", "./output")
    base = (PIPELINE_DIR / base_raw).resolve()
    subfolder = STAGE_OUTPUT_DIRS.get(stage, stage)
    stage_dir = base / subfolder

    if not stage_dir.exists():
        return []

    nums = []
    for d in stage_dir.iterdir():
        if d.is_dir() and d.name.startswith("try_"):
            if non_empty_only and not any(d.iterdir()):
                continue
            try:
                nums.append(int(d.name.split("_")[1]))
            except (IndexError, ValueError):
                pass
    return sorted(nums)


def resolve_run_name(stage: str, run: str | None, tag: str | None = None) -> str:
    """
    Resolve the run subfolder name for writing output (Stage 01 / new-run use).

    Creates the *next* available try_XX folder. Use this when starting a new
    processing run so output never overwrites a previous attempt.

    Args:
        stage: Stage identifier, e.g. 'upscaled'.
        run:   Explicit name to use, or None to auto-increment.
        tag:   Optional image name appended to the auto-generated name,
               e.g. 'image_02' → 'try_03_image_02'. Ignored when run is explicit.

    Returns:
        Run name string, e.g. 'try_01', 'try_03_image_02'.
    """
    if run is not None:
        return run

    nums = _scan_run_nums(stage)
    base = f"try_{max(nums) + 1:02d}" if nums else "try_01"
    return f"{base}_{tag}" if tag else base


def latest_run_name(stage: str, run: str | None) -> str:
    """
    Resolve the run subfolder name for reading existing output (Stage 02+ use).

    Returns the *latest existing* try_XX folder so downstream stages
    automatically pick up what the previous stage produced.

    Args:
        stage: Stage identifier to scan, e.g. 'upscaled'.
        run:   Explicit name to use, or None to find the latest.

    Returns:
        Run name string of the latest existing run, e.g. 'try_02'.

    Raises:
        FileNotFoundError: If no try_XX folders exist and no explicit run given.
    """
    if run is not None:
        return run

    nums = _scan_run_nums(stage, non_empty_only=True)
    if not nums:
        raise FileNotFoundError(
            f"No try_XX run folders found in output/{STAGE_OUTPUT_DIRS.get(stage, stage)}/. "
            f"Run the previous stage first."
        )
    return f"try_{max(nums):02d}"


def get_output_dir(stage: str, run: str | None = None) -> Path:
    """
    Return the output subdirectory for a pipeline stage and run, creating it if needed.

    Path structure: OUTPUT_DIR / stage_folder / run_name /
    Example: output/upscaled/try_01/

    Args:
        stage: Short stage identifier, e.g. 'upscaled', 'nobg'.
               Looked up in STAGE_OUTPUT_DIRS; falls back to the raw string.
        run:   Run subfolder name, e.g. 'try_01'. Auto-increments if None.

    Returns:
        Resolved absolute Path to the run directory inside the stage folder
    """
    base_raw = os.getenv("OUTPUT_DIR", "./output")
    base = (PIPELINE_DIR / base_raw).resolve()

    subfolder = STAGE_OUTPUT_DIRS.get(stage, stage)
    run_name = resolve_run_name(stage, run)
    path = base / subfolder / run_name
    path.mkdir(parents=True, exist_ok=True)
    return path


# -------------------------------------------------------------
# PATH BUILDER
# -------------------------------------------------------------

def build_output_path(source_filename: str, stage: str, ext: str, run: str | None = None) -> Path:
    """
    Build the full output file path for a processed image.

    Path structure: OUTPUT_DIR / stage_folder / run_name / {stem}_{stage}.{ext}
    Examples:
        "photo.jpg" + "upscaled" + "png" + "try_01" → output/upscaled/try_01/photo_upscaled.png
        "photo.jpg" + "nobg"     + "png" + "try_02" → output/bg_removed/try_02/photo_nobg.png

    Args:
        source_filename: Original filename, e.g. "photo.jpg"
        stage:           Stage identifier — becomes both subfolder key and filename suffix
        ext:             Output extension without dot, e.g. "png"
        run:             Run subfolder name. Auto-increments if None.

    Returns:
        Full output Path — parent directory is guaranteed to exist
    """
    stem = Path(source_filename).stem
    output_filename = f"{stem}_{stage}.{ext}"
    return get_output_dir(stage, run) / output_filename


# -------------------------------------------------------------
# INPUT SCANNER
# -------------------------------------------------------------

def list_input_images() -> list[Path]:
    """
    Scan INPUT_DIR for all supported image files and return them sorted by name.

    Only files whose suffix (lowercased) appears in IMAGE_EXTENSIONS are included.
    Subdirectories and non-image files are silently ignored.

    Returns:
        Alphabetically sorted list of Path objects for all found images
    """
    input_dir = get_input_dir()

    images = [
        p for p in input_dir.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    ]

    # Sort alphabetically so processing order is predictable and reproducible
    images.sort(key=lambda p: p.name.lower())

    print(f"Found {len(images)} image(s) in: {input_dir}")
    return images
