"""
File: converter/image-pipeline/code/download_models.py
Purpose:
 - Preload every supported CPU image-model weight into the shared VPS cache.
 - Keep downloads idempotent and atomic so interrupted deployments remain safe.
"""

from __future__ import annotations

import os
import shutil
import tempfile
import urllib.request
from pathlib import Path

from rembg.sessions import sessions_class

from utils import PIPELINE_ROOT

MODEL_ROOT = Path(os.environ.get("U2NET_HOME", PIPELINE_ROOT / "models")).resolve()
REMBG_MODELS = (
    "birefnet-portrait",
    "birefnet-general",
    "isnet-general-use",
    "u2net_human_seg",
    "u2net",
    "u2netp",
)
EXTRA_MODELS = (
    (
        "gfpgan/GFPGANv1.4.pth",
        "https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.4.pth",
        348_632_874,
    ),
    (
        "gfpgan/weights/detection_Resnet50_Final.pth",
        "https://github.com/xinntao/facexlib/releases/download/v0.1.0/detection_Resnet50_Final.pth",
        109_497_761,
    ),
    (
        "gfpgan/weights/parsing_parsenet.pth",
        "https://github.com/xinntao/facexlib/releases/download/v0.2.2/parsing_parsenet.pth",
        85_331_193,
    ),
    (
        "realesrgan/RealESRGAN_x4plus.pth",
        "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth",
        67_040_989,
    ),
)


def download_file(relative_path: str, url: str, expected_bytes: int) -> Path:
    """Download one official weight to a temporary file, verify size, then rename."""

    destination = MODEL_ROOT / relative_path
    if destination.is_file() and destination.stat().st_size == expected_bytes:
        print(f"ready {relative_path} ({expected_bytes} bytes)", flush=True)
        return destination

    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "ACM-Pipeline/1.0"})
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{destination.name}.", suffix=".part", dir=destination.parent, delete=False
        ) as temporary:
            temporary_path = Path(temporary.name)
            print(f"downloading {relative_path}", flush=True)
            with urllib.request.urlopen(request, timeout=120) as response:
                shutil.copyfileobj(response, temporary, length=1024 * 1024)

        actual_bytes = temporary_path.stat().st_size
        if actual_bytes != expected_bytes:
            raise RuntimeError(
                f"Unexpected size for {relative_path}: {actual_bytes}, expected {expected_bytes}."
            )
        os.replace(temporary_path, destination)
        print(f"ready {relative_path} ({actual_bytes} bytes)", flush=True)
        return destination
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def main() -> None:
    """Ask rembg to cache all ONNX weights, then fetch the two Torch weights."""

    MODEL_ROOT.mkdir(parents=True, exist_ok=True)
    os.environ["U2NET_HOME"] = str(MODEL_ROOT)

    available = {session.name(): session for session in sessions_class}
    for model_name in REMBG_MODELS:
        session = available.get(model_name)
        if session is None:
            raise RuntimeError(f"Installed rembg does not provide {model_name}.")
        model_path = Path(session.download_models())
        print(f"ready {model_path.name} ({model_path.stat().st_size} bytes)", flush=True)

    for relative_path, url, expected_bytes in EXTRA_MODELS:
        download_file(relative_path, url, expected_bytes)

    total_bytes = sum(path.stat().st_size for path in MODEL_ROOT.rglob("*") if path.is_file())
    print(f"MODEL_CACHE_COMPLETE root={MODEL_ROOT} bytes={total_bytes}", flush=True)


if __name__ == "__main__":
    main()
