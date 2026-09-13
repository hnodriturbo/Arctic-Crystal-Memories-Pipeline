"""
File: code/research/audit_icon_data.py
Purpose:
 - Validate the canonical ICON data layout before ICON or ECON inference.
 - Separate core checkpoints, body models, and alternative HPS dependencies.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AssetGroup:
    """Describe one independently installable group of model assets."""

    name: str
    purpose: str
    paths: tuple[str, ...]


ASSET_GROUPS = (
    AssetGroup(
        "ICON core checkpoints",
        "Normal prediction and ICON/benchmark reconstruction checkpoints.",
        (
            "ckpt/icon-filter.ckpt",
            "ckpt/icon-nofilter.ckpt",
            "ckpt/normal.ckpt",
            "ckpt/pamir.ckpt",
            "ckpt/pifu.ckpt",
        ),
    ),
    AssetGroup(
        "ICON SMPL support data",
        "Topology and conversion data unpacked from icon_data.zip.",
        (
            "smpl_related/smpl_data/smpl_verts.npy",
            "smpl_related/smpl_data/smplx_cmap.npy",
            "smpl_related/smpl_data/smplx_faces.npy",
            "smpl_related/smpl_data/smplx_verts.npy",
        ),
    ),
    AssetGroup(
        "SMPL body models",
        "Licensed male, female, and neutral SMPL body priors.",
        (
            "smpl_related/models/smpl/SMPL_FEMALE.pkl",
            "smpl_related/models/smpl/SMPL_MALE.pkl",
            "smpl_related/models/smpl/SMPL_NEUTRAL.pkl",
        ),
    ),
    AssetGroup(
        "SMPL-X body models",
        "Expressive body, hands, jaw, and face prior used by PIXIE and ECON.",
        (
            "smpl_related/models/smplx/SMPLX_FEMALE.npz",
            "smpl_related/models/smplx/SMPLX_MALE.npz",
            "smpl_related/models/smplx/SMPLX_NEUTRAL.npz",
            "smpl_related/models/smplx/version.txt",
        ),
    ),
    AssetGroup(
        "PIXIE HPS",
        "Preferred ECON human-pose-and-shape estimator for face and hands.",
        (
            "pixie_data/flame2smplx_tex_1024.npy",
            "pixie_data/MANO_SMPLX_vertex_ids.pkl",
            "pixie_data/pixie_model.tar",
            "pixie_data/SMPL-X__FLAME_vertex_ids.npy",
            "pixie_data/SMPL_X_template_FLAME_uv.obj",
            "pixie_data/smplx_extra_joints.yaml",
            "pixie_data/smplx_hand.obj",
            "pixie_data/SMPLX_NEUTRAL_2020.npz",
            "pixie_data/smplx_tex.obj",
            "pixie_data/smplx_tex.png",
            "pixie_data/SMPLX_to_J14.pkl",
            "pixie_data/uv_face_eye_mask.png",
            "pixie_data/uv_face_mask.png",
        ),
    ),
    AssetGroup(
        "PARE HPS alternative",
        "Optional SMPL pose-and-shape estimator.",
        (
            "pare_data/J_regressor_extra.npy",
            "pare_data/J_regressor_h36m.npy",
            "pare_data/pare/checkpoints/pare_checkpoint.ckpt",
            "pare_data/pare/checkpoints/pare_config.yaml",
            "pare_data/pare/checkpoints/pare_w_3dpw_checkpoint.ckpt",
            "pare_data/pare/checkpoints/pare_w_3dpw_config.yaml",
            "pare_data/smpl_mean_params.npz",
            "pare_data/smpl_partSegmentation_mapping.pkl",
        ),
    ),
    AssetGroup(
        "PyMAF HPS alternative",
        "Optional SMPL pose-and-shape estimator.",
        (
            "pymaf_data/cube_parts.npy",
            "pymaf_data/gmm_08.pkl",
            "pymaf_data/J_regressor_extra.npy",
            "pymaf_data/J_regressor_h36m.npy",
            "pymaf_data/mesh_downsampling.npz",
            "pymaf_data/pretrained_model/PyMAF_model_checkpoint.pt",
            "pymaf_data/smpl_mean_params.npz",
            "pymaf_data/UV_data/UV_Processed.mat",
            "pymaf_data/UV_data/UV_symmetry_transforms.mat",
            "pymaf_data/vertex_texture.npy",
        ),
    ),
)


def parse_args() -> argparse.Namespace:
    """Parse the canonical ICON data directory to inspect."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("data_dir", type=Path, help="Path to ICON/data")
    return parser.parse_args()


def main() -> int:
    """Print a deterministic readiness report and return nonzero if PIXIE inference is incomplete."""

    data_dir = parse_args().data_dir.resolve()
    print(f"ICON data root: {data_dir}")

    group_status: dict[str, bool] = {}
    for group in ASSET_GROUPS:
        missing = [relative for relative in group.paths if not (data_dir / relative).is_file()]
        ready = not missing
        group_status[group.name] = ready
        print(f"\n[{'READY' if ready else 'MISSING'}] {group.name}")
        print(f"  Purpose: {group.purpose}")
        for relative in missing:
            print(f"  - {relative}")

    required_for_pixie = (
        "ICON core checkpoints",
        "ICON SMPL support data",
        "SMPL body models",
        "SMPL-X body models",
        "PIXIE HPS",
    )
    ready_for_pixie = all(group_status[name] for name in required_for_pixie)
    print(f"\nPIXIE inference readiness: {'READY' if ready_for_pixie else 'INCOMPLETE'}")
    return 0 if ready_for_pixie else 2


if __name__ == "__main__":
    raise SystemExit(main())
