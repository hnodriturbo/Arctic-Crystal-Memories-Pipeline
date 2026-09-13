"""
File: code/research/install_econ_model_assets.py
Purpose:
 - Extract verified ECON model archives into separate local staging directories.
 - Build ECON/data with hard links matching the official fetch_data.sh layout.
"""

from __future__ import annotations

import argparse
import json
import os
import zipfile
from datetime import datetime, timezone
from pathlib import Path


ARCHIVES = {
    "smpl": "SMPL_python_v.1.0.0.zip",
    "smplify": "mpips_smplify_public_v2.zip",
    "smplx": "models_smplx_v1_1.zip",
    "econ": "econ_data.zip",
    "pixie": "pixie_data.zip",
    "pymafx": "pymafx_data.zip",
}


def parse_args() -> argparse.Namespace:
    """Parse model archive, staging, and canonical data directories."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--downloads", type=Path, required=True)
    parser.add_argument("--staging", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    return parser.parse_args()


def extract_archive(archive_path: Path, destination: Path) -> None:
    """Extract one ZIP after validating every member against path traversal."""

    if destination.is_dir() and any(destination.iterdir()):
        print(f"[existing staging] {destination.name}")
        return

    destination.mkdir(parents=True, exist_ok=True)
    destination_root = destination.resolve()
    with zipfile.ZipFile(archive_path) as archive:
        bad_member = archive.testzip()
        if bad_member is not None:
            raise RuntimeError(f"CRC failure in {archive_path.name}: {bad_member}")

        for member in archive.infolist():
            member_path = (destination / member.filename).resolve()
            if destination_root not in member_path.parents and member_path != destination_root:
                raise RuntimeError(f"Unsafe ZIP member in {archive_path.name}: {member.filename}")
        archive.extractall(destination)
    print(f"[extracted] {archive_path.name} -> {destination}")


def hardlink_file(source: Path, destination: Path) -> None:
    """Create a canonical hard link without overwriting an existing different file."""

    if not source.is_file():
        raise FileNotFoundError(source)
    destination.parent.mkdir(parents=True, exist_ok=True)

    if destination.exists():
        if not destination.is_file() or destination.stat().st_size != source.stat().st_size:
            raise RuntimeError(f"Canonical destination differs: {destination}")
        return

    os.link(source, destination)


def hardlink_tree(source: Path, destination: Path) -> int:
    """Hard-link every regular source file while preserving its relative path."""

    count = 0
    for source_file in source.rglob("*"):
        if not source_file.is_file() or source_file.name == ".DS_Store":
            continue
        hardlink_file(source_file, destination / source_file.relative_to(source))
        count += 1
    return count


def main() -> int:
    """Install all ECON inference assets and validate the resulting core layout."""

    args = parse_args()
    downloads = args.downloads.resolve()
    staging = args.staging.resolve()
    data_dir = args.data_dir.resolve()

    staging_dirs: dict[str, Path] = {}
    for package_name, filename in ARCHIVES.items():
        archive_path = downloads / filename
        if not archive_path.is_file() or not zipfile.is_zipfile(archive_path):
            raise RuntimeError(f"Missing or invalid archive: {archive_path}")
        package_staging = staging / archive_path.stem
        extract_archive(archive_path, package_staging)
        staging_dirs[package_name] = package_staging

    linked = 0
    linked += hardlink_tree(staging_dirs["econ"] / "ckpt", data_dir / "ckpt")
    linked += hardlink_tree(
        staging_dirs["econ"] / "smpl_data",
        data_dir / "smpl_related" / "smpl_data",
    )
    linked += hardlink_tree(
        staging_dirs["smplx"] / "models",
        data_dir / "smpl_related" / "models",
    )
    linked += hardlink_tree(
        staging_dirs["pixie"] / "pixie_data",
        data_dir / "HPS" / "pixie_data",
    )
    linked += hardlink_tree(
        staging_dirs["pymafx"] / "pymafx_data",
        data_dir / "HPS" / "pymafx_data",
    )

    smpl_model_dir = data_dir / "smpl_related" / "models" / "smpl"
    hardlink_file(
        staging_dirs["smpl"] / "smpl" / "models" / "basicModel_f_lbs_10_207_0_v1.0.0.pkl",
        smpl_model_dir / "SMPL_FEMALE.pkl",
    )
    hardlink_file(
        staging_dirs["smpl"] / "smpl" / "models" / "basicmodel_m_lbs_10_207_0_v1.0.0.pkl",
        smpl_model_dir / "SMPL_MALE.pkl",
    )
    hardlink_file(
        staging_dirs["smplify"]
        / "smplify_public"
        / "code"
        / "models"
        / "basicModel_neutral_lbs_10_207_0_v1.0.0.pkl",
        smpl_model_dir / "SMPL_NEUTRAL.pkl",
    )
    linked += 3

    required_paths = (
        "ckpt/normal.ckpt",
        "smpl_related/models/smpl/SMPL_FEMALE.pkl",
        "smpl_related/models/smpl/SMPL_MALE.pkl",
        "smpl_related/models/smpl/SMPL_NEUTRAL.pkl",
        "smpl_related/models/smplx/SMPLX_FEMALE.npz",
        "smpl_related/models/smplx/SMPLX_MALE.npz",
        "smpl_related/models/smplx/SMPLX_NEUTRAL.npz",
        "HPS/pixie_data/pixie_model.tar",
        "HPS/pixie_data/SMPLX_NEUTRAL_2020.npz",
        "HPS/pymafx_data/PyMAF-X_model_checkpoint.pt",
    )
    missing = [relative for relative in required_paths if not (data_dir / relative).is_file()]
    if missing:
        raise RuntimeError("Canonical ECON data is incomplete:\n- " + "\n- ".join(missing))

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data_dir": str(data_dir),
        "hardlinked_files_processed": linked,
        "required_paths": list(required_paths),
        "status": "ready",
    }
    manifest_path = staging.parent / "install-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"[ready] canonical ECON data: {data_dir}")
    print(f"[manifest] {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
