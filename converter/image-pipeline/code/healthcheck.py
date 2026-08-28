"""
File: converter/image-pipeline/code/healthcheck.py
Purpose:
 - Verify the isolated image environment, CPU-only ONNX provider and model cache.
 - Optionally run a tiny in-memory background-removal inference for deployment QA.
"""

from __future__ import annotations

import argparse
import json
import platform


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
    from PIL import Image, ImageDraw

    report = {
        "cpu_only": onnxruntime.get_device() == "CPU",
        "inference": None,
        "numpy": numpy.__version__,
        "onnxruntime": onnxruntime.__version__,
        "python": platform.python_version(),
        "scipy": scipy.__version__,
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
        raise SystemExit("Image environment is not using the CPU ONNX runtime.")

    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
