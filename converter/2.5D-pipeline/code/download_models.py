"""
File: converter/2.5D-pipeline/code/download_models.py
Purpose:
 - Materialise model weights under Models/ before a real 2.5D job starts.
 - Keep Hugging Face assets in named folders that adapters can load directly.
 - Record source revisions, licences, sizes and SHA-256 checksums locally.

Models/ is git-ignored. Tracked provenance lives in utils.py; each
local model also receives an ignored source.json beside its weights.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from depth_map import DEPTH_ANYTHING_MODELS, MARIGOLD_MODEL  # noqa: E402
from utils import (  # noqa: E402
    MODEL_ASSETS,
    MODELS_DIR,
    RECOMMENDED_BASELINE,
    report,
    use_local_model_cache,
)


def sha256_file(path: Path) -> str:
    """Hash a multi-gigabyte weight without loading it into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as input_file:
        for chunk in iter(lambda: input_file.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_source_record(asset_name: str, target_dir: Path, files: list[Path]) -> None:
    """Write ignored local proof of exactly what was materialised."""
    asset = MODEL_ASSETS[asset_name]
    record = {
        "asset": asset_name,
        "source": {key: value for key, value in asset.items() if key != "required_files"},
        "files": [
            {
                "path": str(path.relative_to(target_dir)).replace("\\", "/"),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for path in files
        ],
    }
    (target_dir / "source.json").write_text(
        json.dumps(record, indent=2, sort_keys=True), encoding="utf-8"
    )


def fetch_huggingface_asset(asset_name: str) -> None:
    """Download a pinned Hub snapshot into a stable direct-load directory."""
    from huggingface_hub import snapshot_download

    asset = MODEL_ASSETS[asset_name]
    target_dir = MODELS_DIR / asset["directory"]
    target_dir.mkdir(parents=True, exist_ok=True)
    report(f"[models] {asset['repo_id']} @ {asset['revision']}")
    snapshot_download(
        repo_id=asset["repo_id"],
        revision=asset["revision"],
        local_dir=target_dir,
        cache_dir=MODELS_DIR / ".hf-cache",
    )
    required = [target_dir / name for name in asset["required_files"]]
    missing = [path.name for path in required if not path.is_file()]
    if missing:
        raise RuntimeError(f"{asset_name} is incomplete; missing: {', '.join(missing)}")
    write_source_record(asset_name, target_dir, required)


def download_with_resume(url: str, target: Path, expected_bytes: int | None) -> None:
    """Stream a direct checkpoint with a resumable .partial file."""
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(target.suffix + ".partial")
    existing = partial.stat().st_size if partial.exists() else 0
    headers = {"User-Agent": "ACM-2.5D-pipeline/1"}
    if existing:
        headers["Range"] = f"bytes={existing}-"

    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request) as response:  # noqa: S310 - pinned HTTPS source
        resumable = existing > 0 and getattr(response, "status", None) == 206
        if existing and not resumable:
            report("[models] server did not resume; restarting the partial download")
            existing = 0
        mode = "ab" if resumable else "wb"
        downloaded = existing
        report_step = 256 * 1024 * 1024
        next_report = ((downloaded // report_step) + 1) * report_step
        with partial.open(mode) as output_file:
            while True:
                chunk = response.read(8 * 1024 * 1024)
                if not chunk:
                    break
                output_file.write(chunk)
                downloaded += len(chunk)
                if downloaded >= next_report:
                    report(f"[models] downloaded {downloaded / 1_073_741_824:.2f} GiB")
                    next_report += report_step

    if expected_bytes is not None and partial.stat().st_size != expected_bytes:
        raise RuntimeError(
            f"Download size mismatch for {target.name}: "
            f"{partial.stat().st_size} != {expected_bytes} bytes"
        )
    partial.replace(target)


def fetch_direct_asset(asset_name: str) -> None:
    """Download a non-Hub checkpoint such as Apple's official Depth Pro weight."""
    asset = MODEL_ASSETS[asset_name]
    target_dir = MODELS_DIR / asset["directory"]
    target = target_dir / asset["filename"]
    if target.is_file() and target.stat().st_size == asset.get("expected_bytes"):
        report(f"[models] {asset_name} already present")
    else:
        report(f"[models] {asset_name} from {asset['url']}")
        download_with_resume(asset["url"], target, asset.get("expected_bytes"))
    write_source_record(asset_name, target_dir, [target])


def fetch_asset(asset_name: str) -> None:
    """Dispatch one registry entry to its source-specific downloader."""
    if MODEL_ASSETS[asset_name]["kind"] == "huggingface":
        fetch_huggingface_asset(asset_name)
    else:
        fetch_direct_asset(asset_name)


def fetch_depth_anything(size: str) -> None:
    """Materialise one legacy Depth Anything checkpoint in the local HF cache."""
    from transformers import AutoImageProcessor, AutoModelForDepthEstimation

    model_id = DEPTH_ANYTHING_MODELS[size]
    report(f"[models] {model_id}")
    AutoImageProcessor.from_pretrained(model_id)
    AutoModelForDepthEstimation.from_pretrained(model_id)


def fetch_marigold() -> None:
    """Materialise the existing Marigold depth pipeline when requested."""
    try:
        from diffusers import MarigoldDepthPipeline
    except ImportError:
        report("[models] diffusers is not installed - skipping Marigold.")
        return

    report(f"[models] {MARIGOLD_MODEL}")
    MarigoldDepthPipeline.from_pretrained(MARIGOLD_MODEL)


def main() -> int:
    parser = argparse.ArgumentParser(description="Download 2.5D models into Models/.")
    parser.add_argument(
        "--model",
        action="append",
        choices=[*sorted(DEPTH_ANYTHING_MODELS), "all"],
        help="Legacy Depth Anything sizes. Repeatable; defaults to large if no other option is used.",
    )
    parser.add_argument("--marigold", action="store_true", help="Fetch the existing Marigold depth model.")
    parser.add_argument(
        "--asset",
        action="append",
        choices=sorted(MODEL_ASSETS),
        help="Pinned direct-load model asset. Repeatable.",
    )
    parser.add_argument(
        "--baseline",
        action="store_true",
        help="Fetch MoGe-2 vitb-normal, MoGe-2 vitl-normal and Apple Depth Pro.",
    )
    args = parser.parse_args()

    use_local_model_cache()
    report(f"[models] root {MODELS_DIR}")

    requested_assets = list(args.asset or [])
    if args.baseline:
        requested_assets.extend(RECOMMENDED_BASELINE)
    for asset_name in dict.fromkeys(requested_assets):
        fetch_asset(asset_name)

    wanted = list(args.model or [])
    if not requested_assets and not args.marigold and not wanted:
        wanted = ["large"]
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
