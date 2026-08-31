"""
utils.py — shared plumbing for the converter's 2.5D relief pipeline.
Path: converter/2.5D-pipeline/code/utils.py

Same contract as image-pipeline/code/utils.py: every script takes explicit
--input and --output paths and never invents a filename, so the Node runner
owns the whole temporary-file lifecycle.

The one thing this module does that the others do not is point the Hugging
Face cache at Models/ before transformers is imported anywhere. Left alone,
transformers writes ~1.3 GB into %USERPROFILE%\\.cache, which then does not
travel to the VPS and does not show up in this folder's disk usage.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

PIPELINE_ROOT = Path(__file__).resolve().parent.parent
INPUT_DIR = PIPELINE_ROOT / "input"
OUTPUT_DIR = PIPELINE_ROOT / "output"
MODELS_DIR = PIPELINE_ROOT / "Models"

# External research baselines. Hugging Face assets are pinned to exact Hub
# revisions; the Apple checkpoint is pinned to the source repository revision
# and verified by size plus a local SHA-256 record after download.
MODEL_ASSETS = {
    "moge-2-vitb-normal": {
        "kind": "huggingface",
        "repo_id": "Ruicheng/moge-2-vitb-normal",
        "revision": "54ad3a693e61907ea4633d13dec6ee682fa09419",
        "directory": "moge-2-vitb-normal",
        "license": "MIT (Hugging Face model-card tag; retain upstream files)",
        "required_files": ["model.pt"],
    },
    "moge-2-vitl-normal": {
        "kind": "huggingface",
        "repo_id": "Ruicheng/moge-2-vitl-normal",
        "revision": "b135031bae30b5ac2ae141a0e68717795ce38340",
        "directory": "moge-2-vitl-normal",
        "license": "MIT (Hugging Face model-card tag; retain upstream files)",
        "required_files": ["model.pt"],
    },
    "depth-pro": {
        "kind": "url",
        "url": "https://ml-site.cdn-apple.com/models/depth-pro/depth_pro.pt",
        "source_repo": "https://github.com/apple/ml-depth-pro",
        "source_revision": "9efe5c1def37a26c5367a71df664b18e1306c708",
        "directory": "depth-pro/checkpoints",
        "filename": "depth_pro.pt",
        "expected_bytes": 1904446787,
        "license": "Apple ml-depth-pro LICENSE terms",
        "required_files": ["depth_pro.pt"],
    },
    "opencv-face-detector-yunet": {
        "kind": "huggingface",
        "repo_id": "opencv/face_detection_yunet",
        "revision": "3cc26e7f1014a5ee5d74a42acee58bafc9d0a310",
        "directory": "opencv-face-detector-yunet",
        "license": "MIT (upstream LICENSE retained beside the checkpoint)",
        "required_files": ["face_detection_yunet_2023mar.onnx", "LICENSE"],
    },
}

RECOMMENDED_BASELINE = (
    "moge-2-vitb-normal",
    "moge-2-vitl-normal",
    "depth-pro",
    "opencv-face-detector-yunet",
)

# Millimetres, mirroring DEFAULT_CRYSTAL_MARGIN in
# pipeline-converter/code/utils/printer_dxf.py. That module stays authoritative
# for the real fit; this is only the relief's own framing default.
DEFAULT_CRYSTAL_MARGIN = 1.0
MIN_CRYSTAL_MARGIN = 0.1


def use_local_model_cache() -> Path:
    """
    Redirect every Hugging Face download into Models/.

    Must run before `import transformers` anywhere in the process, which is why
    each script calls it at the top of main() rather than at import time - the
    argparse failure path should not create a cache directory.
    """
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    # Keep the global HF token in the user's normal credential directory. Only
    # model/cache payloads belong here; secrets must never enter the project.
    os.environ.setdefault("HUGGINGFACE_HUB_CACHE", str(MODELS_DIR / "hub"))
    os.environ.setdefault("TRANSFORMERS_CACHE", str(MODELS_DIR / "hub"))
    os.environ.setdefault("HF_XET_CACHE", str(MODELS_DIR / "xet"))
    return MODELS_DIR


def base_parser(description: str) -> argparse.ArgumentParser:
    """Argument shape every script in this folder shares."""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--input", required=True, type=Path, help="Source file.")
    parser.add_argument("--output", required=True, type=Path, help="Where to write the result.")
    return parser


def report(message: str) -> None:
    """Unbuffered, because the web UI streams stdout line by line as it arrives."""
    print(message, flush=True)


def fail(message: str) -> None:
    """Non-zero exit with the reason on stderr, which is what the UI shows in red."""
    print(message, file=sys.stderr, flush=True)
    raise SystemExit(1)


def prepare_output(path: Path) -> Path:
    """Make sure the destination folder exists before anything tries to write there."""
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def torch_device(requested: str = "auto") -> str:
    """
    Resolve the device to run on.

    'auto' is CUDA when it is genuinely available and CPU otherwise, which is
    the VPS case. An explicit 'cuda' on a CPU-only box is a hard error rather
    than a silent 40x slowdown - a job that was expected to take 8 seconds and
    quietly takes 5 minutes is worse than one that refuses.
    """
    try:
        import torch
    except ImportError:  # pragma: no cover - environment problem, not logic
        fail("Torch is not installed. Run: pip install -r requirements.txt")

    available = torch.cuda.is_available()
    if requested == "auto":
        return "cuda" if available else "cpu"
    if requested == "cuda" and not available:
        fail("--device cuda was asked for, but torch reports no CUDA device here.")
    return requested


def parse_template(name: str) -> dict[str, float] | None:
    """
    Read a crystal blank's millimetres straight out of its name.

    Every key in CRYSTAL_TEMPLATES (printer_dxf.py) and CRYSTAL_BLANKS
    (crystal-blanks.js) is literally WIDTHxHEIGHTxDEPTH, so the name carries
    its own dimensions and this pipeline needs no fourth copy of that table to
    drift out of sync with the other three.
    """
    parts = str(name or "").lower().split("x")
    if len(parts) != 3:
        return None
    try:
        width, height, depth = (float(part) for part in parts)
    except ValueError:
        return None
    if min(width, height, depth) <= 0:
        return None
    return {"width": width, "height": height, "depth": depth}


def usable_space(template: str, border: float = DEFAULT_CRYSTAL_MARGIN) -> dict[str, float]:
    """Engravable millimetres left inside a blank once the margin is removed."""
    blank = parse_template(template)
    if blank is None:
        fail(f"Unrecognised crystal blank '{template}'. Expected WIDTHxHEIGHTxDEPTH, e.g. 60x80x40.")
    if border < MIN_CRYSTAL_MARGIN:
        fail(f"Crystal margin must be at least {MIN_CRYSTAL_MARGIN:g} mm.")

    inside = {axis: blank[axis] - 2 * border for axis in ("width", "height", "depth")}
    for axis, value in inside.items():
        if value <= 0:
            fail(f"Crystal margin {border:g} mm leaves no usable {axis}.")

    inside["border"] = border
    inside["blank"] = blank
    return inside
