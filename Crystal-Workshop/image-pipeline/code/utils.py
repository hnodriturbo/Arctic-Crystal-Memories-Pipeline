"""
utils.py — shared plumbing for the converter's image pipeline.
Path: converter/image-pipeline/code/utils.py

Every script here takes explicit --input and --output paths rather than
writing into a fixed folder under a guessed name. The Node side then owns the
whole temporary-file lifecycle and never has to reconstruct a filename the
Python happened to choose.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PIPELINE_ROOT = Path(__file__).resolve().parent.parent
INPUT_DIR = PIPELINE_ROOT / "input"
OUTPUT_DIR = PIPELINE_ROOT / "output"


def base_parser(description: str) -> argparse.ArgumentParser:
    """Argument shape every script in this folder shares."""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--input", required=True, type=Path, help="Source image.")
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


def torch_device() -> str | None:
    """
    CUDA when it is really there, CPU when torch is installed without it, None
    when torch is absent entirely.

    The VPS is the CPU case. Explicit AI-engine selections may use CPU Torch,
    while each script keeps a lightweight automatic path for routine jobs.
    """
    try:
        import torch
    except ImportError:
        return None
    return "cuda" if torch.cuda.is_available() else "cpu"
