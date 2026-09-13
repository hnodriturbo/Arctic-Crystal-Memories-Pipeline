"""
File: converter/2.5D-pipeline/code/healthcheck.py
Purpose:
 - Report what this environment can actually do, without loading a model or
   writing anything.

Read by the web UI's Environments panel, which is where "why is the 2.5D tab
greyed out" gets answered.
"""

from __future__ import annotations

import importlib.util
import json
import platform
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from utils import MODELS_DIR, use_local_model_cache  # noqa: E402


def version_of(module_name: str) -> str | None:
    """Import a module only if it is genuinely installed, and report its version."""
    if importlib.util.find_spec(module_name) is None:
        return None
    try:
        return getattr(__import__(module_name), "__version__", "unknown")
    except Exception:  # noqa: BLE001 - a broken install is the same as an absent one
        return None


def cached_models() -> list[str]:
    """Checkpoints already on disk, so the UI can warn before a 1.3 GB surprise."""
    hub = MODELS_DIR / "hub"
    if not hub.is_dir():
        return []
    return sorted(entry.name for entry in hub.iterdir() if entry.name.startswith("models--"))


def local_models() -> list[str]:
    """Fully materialised model folders that pipeline code can load directly."""
    if not MODELS_DIR.is_dir():
        return []
    return sorted(
        entry.name
        for entry in MODELS_DIR.iterdir()
        if entry.is_dir() and entry.name not in {"hub", "xet", ".hf-cache"}
    )


def main() -> int:
    use_local_model_cache()
    pipeline_root = Path(__file__).resolve().parents[1]

    torch_version = version_of("torch")
    transformers_version = version_of("transformers")
    diffusers_version = version_of("diffusers")
    cuda = False
    if torch_version:
        import torch

        cuda = torch.cuda.is_available()

    # 3.11, matching the other three pipelines. Not cosmetic: the CPU torch
    # wheels this folder installs are published per minor version, and the VPS
    # provisioning script builds every venv on 3.11.
    correct_python = sys.version_info[:2] == (3, 11)

    directories = {
        name: (pipeline_root / folder).is_dir()
        for name, folder in (("input", "input"), ("output", "output"), ("models", "Models"))
    }
    gnm_files = {
        "source": MODELS_DIR / "research" / "GNM" / "gnm" / "shape" / "gnm_pytorch.py",
        "head_model": (
            MODELS_DIR
            / "research"
            / "GNM"
            / "gnm"
            / "shape"
            / "data"
            / "versions"
            / "v3_0"
            / "gnm_head.npz"
        ),
        "mediapipe_correspondence": (
            MODELS_DIR / "research" / "mediapipe" / "gnm_head_dense_468.txt"
        ),
    }
    gnm_ready = all(path.is_file() for path in gnm_files.values())
    moge_ready = (MODELS_DIR / "moge-2-vitl-normal" / "model.pt").is_file()
    engine_ready = moge_ready or bool(transformers_version) or bool(diffusers_version)
    report = {
        "ok": (
            correct_python
            and bool(torch_version)
            and engine_ready
            and bool(version_of("scipy"))
            and gnm_ready
            and all(directories.values())
        ),
        "python": platform.python_version(),
        "python_ok": correct_python,
        "torch": torch_version,
        "transformers": transformers_version,
        "diffusers": diffusers_version,
        "trimesh": version_of("trimesh"),
        "scipy": version_of("scipy"),
        "pillow": version_of("PIL"),
        "cuda": cuda,
        "device": "cuda" if cuda else "cpu",
        "engines": {
            "moge-2": moge_ready,
            "depth-anything": bool(transformers_version),
            "marigold": bool(diffusers_version),
        },
        "gnm_head": {
            "ready": gnm_ready,
            "files": {name: path.is_file() for name, path in gnm_files.items()},
        },
        "cached_models": cached_models(),
        "local_models": local_models(),
        "directories": directories,
    }
    print(json.dumps(report, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
