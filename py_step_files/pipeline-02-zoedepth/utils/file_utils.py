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
    raw = os.getenv("INPUT_DIR", "./input")
    path = (PIPELINE_DIR / raw).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def _scan_run_nums(stage: str, non_empty_only: bool = False) -> list[int]:
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
    if run is not None:
        return run

    nums = _scan_run_nums(stage)
    base = f"try_{max(nums) + 1:02d}" if nums else "try_01"
    return f"{base}_{tag}" if tag else base


def latest_run_name(stage: str, run: str | None) -> str:
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
    base_raw = os.getenv("OUTPUT_DIR", "./output")
    base = (PIPELINE_DIR / base_raw).resolve()

    subfolder = STAGE_OUTPUT_DIRS.get(stage, stage)
    run_name = resolve_run_name(stage, run)
    path = base / subfolder / run_name
    path.mkdir(parents=True, exist_ok=True)
    return path


def build_output_path(source_filename: str, stage: str, ext: str, run: str | None = None) -> Path:
    stem = Path(source_filename).stem
    output_filename = f"{stem}_{stage}.{ext}"
    return get_output_dir(stage, run) / output_filename


def list_input_images() -> list[Path]:
    input_dir = get_input_dir()

    images = [
        p for p in input_dir.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    ]

    images.sort(key=lambda p: p.name.lower())

    print(f"Found {len(images)} image(s) in: {input_dir}")
    return images
