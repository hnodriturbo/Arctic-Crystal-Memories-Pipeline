"""
File: converter/image-pipeline/code/healthcheck.py
Purpose:
 - Verify the isolated image environment, CPU-only ONNX provider and model cache.
 - Optionally run a tiny in-memory background-removal inference for deployment QA.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import platform
from pathlib import Path

from utils import PIPELINE_ROOT

EXPECTED_MODELS = (
    "birefnet-portrait.onnx",
    "birefnet-general.onnx",
    "isnet-general-use.onnx",
    "u2net_human_seg.onnx",
    "u2net.onnx",
    "u2netp.onnx",
    "gfpgan/GFPGANv1.4.pth",
    "gfpgan/weights/detection_Resnet50_Final.pth",
    "gfpgan/weights/parsing_parsenet.pth",
    "realesrgan/RealESRGAN_x4plus.pth",
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify the CPU image-pipeline environment.")
    parser.add_argument(
        "--inference",
        action="store_true",
        help="Run a small u2netp inference in memory after checking imports.",
    )
    args = parser.parse_args()

    import numpy
    import onnxruntime
    import scipy
    import torch
    import torchvision
    import cv2
    import gfpgan  # noqa: F401 - import proves the BasicSR stack is compatible
    import realesrgan  # noqa: F401 - import proves the BasicSR stack is compatible
    from PIL import Image, ImageDraw

    model_root = Path(os.environ.get("U2NET_HOME", PIPELINE_ROOT / "models")).resolve()
    missing_models = [name for name in EXPECTED_MODELS if not (model_root / name).is_file()]
    torch_cpu_only = not torch.cuda.is_available() and torch.version.cuda is None

    report = {
        "cpu_only": onnxruntime.get_device() == "CPU" and torch_cpu_only,
        "inference": None,
        "models": {
            "count": len(EXPECTED_MODELS) - len(missing_models),
            "expected": len(EXPECTED_MODELS),
            "missing": missing_models,
            "root": str(model_root),
        },
        "numpy": numpy.__version__,
        "onnxruntime": onnxruntime.__version__,
        "opencv": cv2.__version__,
        "python": platform.python_version(),
        "realesrgan": importlib.metadata.version("realesrgan"),
        "scipy": scipy.__version__,
        "torch": torch.__version__,
        "torchvision": torchvision.__version__,
        "gfpgan": importlib.metadata.version("gfpgan"),
    }

    if args.inference:
        from rembg import new_session, remove

        source = Image.new("RGB", (128, 128), "white")
        ImageDraw.Draw(source).ellipse((24, 12, 104, 116), fill="black")
        result = remove(source, session=new_session("u2netp")).convert("RGBA")
        report["inference"] = {
            "alpha_extrema": result.getchannel("A").getextrema(),
            "model": "u2netp",
            "size": result.size,
        }

    if not report["cpu_only"]:
        raise SystemExit("Image environment contains a CUDA runtime; production must remain CPU-only.")
    if missing_models:
        raise SystemExit(f"Image model cache is incomplete: {', '.join(missing_models)}")

    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
