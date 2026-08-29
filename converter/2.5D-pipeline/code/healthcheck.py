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


def main() -> int:
    use_local_model_cache()
    pipeline_root = Path(__file__).resolve().parents[1]

    torch_version = version_of("torch")
    cuda = False
    if torch_version:
        import torch

        cuda = torch.cuda.is_available()

    # 3.11, matching the other three pipelines. Not cosmetic: the CPU torch
    # wheels this folder installs are published per minor version, and the VPS
    # provisioning script builds every venv on 3.11.
    correct_python = sys.version_info[:2] == (3, 11)

    directories = {name: (pipeline_root / name).is_dir() for name in ("input", "output", "models")}
    report = {
        "ok": (
            correct_python
            and bool(torch_version)
            and bool(version_of("transformers"))
            and all(directories.values())
        ),
        "python": platform.python_version(),
        "python_ok": correct_python,
        "torch": torch_version,
        "transformers": version_of("transformers"),
        "diffusers": version_of("diffusers"),
        "trimesh": version_of("trimesh"),
        "pillow": version_of("PIL"),
        "cuda": cuda,
        "device": "cuda" if cuda else "cpu",
        "engines": {
            "depth-anything": bool(version_of("transformers")),
            "marigold": bool(version_of("diffusers")),
        },
        "cached_models": cached_models(),
        "directories": directories,
    }
    print(json.dumps(report, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
