"""
File: converter/2.5D-pipeline/code/download_models.py
Purpose:
 - Pull the depth weights into models/ once, so the first real job is not also
   a 1.3 GB download that looks like a hung run in the web UI.

Same role as image-pipeline/code/download_models.py, and the same reason: a
progress bar inside an SSE stream is nobody's idea of a status report.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from utils import MODELS_DIR, report, use_local_model_cache  # noqa: E402
from depth_map import DEPTH_ANYTHING_MODELS, MARIGOLD_MODEL  # noqa: E402


def fetch_depth_anything(size: str) -> None:
    """Materialise one Depth Anything checkpoint in the local cache."""
    from transformers import AutoImageProcessor, AutoModelForDepthEstimation

    model_id = DEPTH_ANYTHING_MODELS[size]
    report(f"[models] {model_id}")
    AutoImageProcessor.from_pretrained(model_id)
    AutoModelForDepthEstimation.from_pretrained(model_id)


def fetch_marigold() -> None:
    """Materialise the Marigold pipeline, if diffusers is installed at all."""
    try:
        from diffusers import MarigoldDepthPipeline
    except ImportError:
        report("[models] diffusers is not installed - skipping Marigold.")
        return

    report(f"[models] {MARIGOLD_MODEL}")
    MarigoldDepthPipeline.from_pretrained(MARIGOLD_MODEL)


def main() -> int:
    parser = argparse.ArgumentParser(description="Pre-download the depth models into models/.")
    parser.add_argument(
        "--model",
        action="append",
        choices=[*sorted(DEPTH_ANYTHING_MODELS), "all"],
        help="Depth Anything sizes to fetch. Repeatable. Defaults to large.",
    )
    parser.add_argument("--marigold", action="store_true", help="Also fetch the Marigold pipeline.")
    args = parser.parse_args()

    use_local_model_cache()
    report(f"[models] cache {MODELS_DIR}")

    wanted = args.model or ["large"]
    if "all" in wanted:
        wanted = sorted(DEPTH_ANYTHING_MODELS)

    for size in dict.fromkeys(wanted):
        fetch_depth_anything(size)
    if args.marigold:
        fetch_marigold()

    report("[models] done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
