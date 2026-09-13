"""
File: code/research/run_hrn_head_modelscope.py
Purpose:
 - Run the official ModelScope HRN Head reconstruction without ACM geometry tools.
 - Export the native OBJ, texture, and a reproducibility manifest for each input.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import platform
import sys
import time
import traceback
from pathlib import Path

import cv2
import numpy as np
import torch
from modelscope.models.cv.face_reconstruction.utils import write_obj
from modelscope.outputs import OutputKeys
from modelscope.pipelines import pipeline
from modelscope.utils.constant import Tasks


MODEL_STACK = "Official ModelScope HRN Head (BFM+FLAME), hair_tex=true"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run an unmodified HRN Head model and export its native result."
    )
    parser.add_argument(
        "--model-dir",
        type=Path,
        required=True,
        help="Local damo/cv_HRN_head-reconstruction model directory.",
    )
    parser.add_argument(
        "--input",
        dest="inputs",
        type=Path,
        action="append",
        required=True,
        help="Input image. Repeat this option to process multiple images.",
    )
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument(
        "--device",
        default="gpu",
        choices=("gpu", "cpu"),
        help="ModelScope device selector.",
    )
    parser.add_argument(
        "--no-hair-texture",
        action="store_true",
        help="Disable HRN's native hair-texture post-processing.",
    )
    parser.add_argument(
        "--nvdiffrast-plugin",
        type=Path,
        help=(
            "Optional previously compiled nvdiffrast_plugin.so. This keeps the "
            "frozen CUDA 11.8 HRN runtime usable when the host GCC is newer than 11."
        ),
    )
    return parser.parse_args()


def preload_nvdiffrast_plugin(plugin_path: Path) -> None:
    """Load a verified local CUDA extension without asking PyTorch to rebuild it."""

    plugin_path = plugin_path.resolve()
    if not plugin_path.is_file():
        raise FileNotFoundError(f"nvdiffrast plugin not found: {plugin_path}")
    specification = importlib.util.spec_from_file_location(
        "nvdiffrast_plugin", plugin_path
    )
    if specification is None or specification.loader is None:
        raise RuntimeError(f"Could not load nvdiffrast plugin spec: {plugin_path}")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    sys.modules["nvdiffrast_plugin"] = module

    import nvdiffrast.torch.ops as nvdiffrast_ops

    nvdiffrast_ops._cached_plugin[False] = module
    print(f"Loaded precompiled nvdiffrast plugin: {plugin_path}", flush=True)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def image_metadata(path: Path) -> dict[str, object]:
    image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if image is None:
        raise ValueError(f"Could not read image: {path}")
    return {
        "path": str(path.resolve()),
        "sha256": sha256_file(path),
        "width": int(image.shape[1]),
        "height": int(image.shape[0]),
        "channels": 1 if image.ndim == 2 else int(image.shape[2]),
    }


def mesh_metadata(mesh: dict[str, np.ndarray]) -> dict[str, object]:
    vertices = np.asarray(mesh["vertices"])
    faces = np.asarray(mesh["faces"])
    return {
        "vertices": int(vertices.shape[0]),
        "faces": int(faces.shape[0]),
        "bounds_min": vertices.min(axis=0).astype(float).tolist(),
        "bounds_max": vertices.max(axis=0).astype(float).tolist(),
    }


def main() -> int:
    args = parse_args()
    model_dir = args.model_dir.resolve()
    output_root = args.output_root.resolve()
    hair_texture = not args.no_hair_texture

    if not model_dir.is_dir():
        raise FileNotFoundError(f"HRN model directory not found: {model_dir}")

    if args.nvdiffrast_plugin is not None:
        preload_nvdiffrast_plugin(args.nvdiffrast_plugin)

    output_root.mkdir(parents=True, exist_ok=True)

    print(f"Loading {MODEL_STACK}", flush=True)
    reconstruction = pipeline(
        Tasks.head_reconstruction,
        model=str(model_dir),
        device=args.device,
        hair_tex=hair_texture,
    )

    for input_path in args.inputs:
        input_path = input_path.resolve()
        sample_dir = output_root / input_path.stem
        sample_dir.mkdir(parents=True, exist_ok=True)

        started_at = time.time()
        print(f"Processing {input_path}", flush=True)
        try:
            result = reconstruction(str(input_path))
        except Exception as error:
            failure = {
                "status": "model-error",
                "model_stack": MODEL_STACK,
                "input": image_metadata(input_path),
                "error_type": type(error).__name__,
                "error": str(error),
                "traceback": traceback.format_exc(),
            }
            (sample_dir / "run-manifest.json").write_text(
                json.dumps(failure, indent=2), encoding="utf-8"
            )
            print(
                f"HRN failed for {input_path}: {type(error).__name__}: {error}",
                flush=True,
            )
            continue
        if not result or result.get(OutputKeys.OUTPUT) is None:
            failure = {
                "status": "no-face-or-no-output",
                "model_stack": MODEL_STACK,
                "input": image_metadata(input_path),
            }
            (sample_dir / "run-manifest.json").write_text(
                json.dumps(failure, indent=2), encoding="utf-8"
            )
            print(f"No HRN output for {input_path}", flush=True)
            continue

        mesh = result[OutputKeys.OUTPUT]["mesh"]
        texture_map = result[OutputKeys.OUTPUT_IMG]
        mesh["texture_map"] = texture_map

        obj_path = sample_dir / "hrn-head.obj"
        write_obj(str(obj_path), mesh)
        cv2.imwrite(str(sample_dir / "hrn-texture.png"), texture_map)

        manifest = {
            "status": "completed",
            "model_stack": MODEL_STACK,
            "model": {
                "name": "damo/cv_HRN_head-reconstruction",
                "revision": "v0.1 / local ModelScope asset revision 89587fd",
                "model_dir": str(model_dir),
                "hair_texture": hair_texture,
                "acm_geometry_or_refinement_used": False,
            },
            "input": image_metadata(input_path),
            "output": {
                "obj": str(obj_path),
                "texture": str(sample_dir / "hrn-texture.png"),
                "native_mask_exported": False,
                **mesh_metadata(mesh),
            },
            "runtime": {
                "seconds": round(time.time() - started_at, 3),
                "python": platform.python_version(),
                "torch": torch.__version__,
                "cuda_available": torch.cuda.is_available(),
                "cuda_device": (
                    torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
                ),
            },
        }
        (sample_dir / "run-manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )
        print(f"Wrote {obj_path}", flush=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
