# =============================================================
# file_utils.py — File and path management helpers
# =============================================================
# Centralizes all file I/O for pipeline-03-pro. Every step uses
# these helpers for consistent paths and auto-created directories.
#
# STAGE_OUTPUT_DIRS maps short stage keys to output subfolder names.
# The geometry/ and textured/ subfolders inside meshes/ are handled
# by the individual scripts, not here.
# =============================================================

from pathlib import Path
from dotenv import load_dotenv
import os

PIPELINE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(PIPELINE_DIR / ".env")

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tiff", ".bmp"}

STAGE_OUTPUT_DIRS: dict[str, str] = {
    "prepared":   "prepared",
    "depth":      "depth_maps",
    "pointcloud": "point_clouds",
    "mesh":       "meshes",
    "export":     "exports",
}


def get_input_dir() -> Path:
    """Return the pipeline input directory, creating it if needed."""
    raw = os.getenv("INPUT_DIR", "./input")
    path = (PIPELINE_DIR / raw).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def _scan_run_nums(stage: str, non_empty_only: bool = False) -> list[int]:
    """Return sorted list of try_NN integers in the stage output folder."""
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
    Resolve the run subfolder name for writing output.
    Creates the next available try_XX folder if run is None.
    """
    if run is not None:
        return run

    nums = _scan_run_nums(stage)
    base = f"try_{max(nums) + 1:02d}" if nums else "try_01"
    return f"{base}_{tag}" if tag else base


def latest_run_name(stage: str, run: str | None) -> str:
    """
    Resolve the run subfolder for reading existing output.
    Returns the latest non-empty try_XX if run is None.
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
    Return the output subdirectory for a pipeline stage and run.
    Creates the directory if it does not exist.
    """
    base_raw = os.getenv("OUTPUT_DIR", "./output")
    base = (PIPELINE_DIR / base_raw).resolve()

    subfolder = STAGE_OUTPUT_DIRS.get(stage, stage)
    run_name = resolve_run_name(stage, run)
    path = base / subfolder / run_name
    path.mkdir(parents=True, exist_ok=True)
    return path


def build_output_path(source_filename: str, stage: str, ext: str, run: str | None = None) -> Path:
    """
    Build the full output file path for a processed image.
    Pattern: OUTPUT_DIR / stage_folder / run_name / {stem}_{stage}.{ext}
    """
    stem = Path(source_filename).stem
    output_filename = f"{stem}_{stage}.{ext}"
    return get_output_dir(stage, run) / output_filename


def list_input_images() -> list[Path]:
    """Scan INPUT_DIR for supported image files, return sorted list."""
    input_dir = get_input_dir()

    images = [
        p for p in input_dir.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    ]

    images.sort(key=lambda p: p.name.lower())

    print(f"Found {len(images)} image(s) in: {input_dir}")
    return images
