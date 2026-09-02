"""
File: code/research/integrate_icon_front_bni.py
Purpose:
 - Integrate exported ICON front/back normal tensors with ECON's d-BiNI solver.
 - Preserve only the source-facing front surface for the crystal 2.5D research path.
"""

import argparse
import json
from pathlib import Path

import numpy as np
import torch
from PIL import Image

from lib.common.BNI import BNI
from lib.common.render import query_color


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--raw-dir", required=True, type=Path)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--k", type=float, default=4.0)
    parser.add_argument("--lambda1", type=float, default=1e-4)
    parser.add_argument("--boundary-consist", type=float, default=1e-6)
    parser.add_argument("--keep-intersections", action="store_true")
    parser.add_argument("--keep-stretched-faces", action="store_true")
    parser.add_argument("--fillet-radius-fraction", type=float, default=0.0)
    parser.add_argument("--fillet-gradient-quantile", type=float, default=98.5)
    return parser.parse_args()


def write_depth_preview(depth, output_path):
    valid = np.isfinite(depth)
    preview = np.zeros(depth.shape, dtype=np.uint8)
    if valid.any():
        low, high = np.percentile(depth[valid], [1.0, 99.0])
        if high > low:
            normalized = np.clip((depth - low) / (high - low), 0.0, 1.0)
            preview[valid] = np.round((1.0 - normalized[valid]) * 255.0).astype(np.uint8)
    Image.fromarray(preview, mode="L").save(output_path)


def main():
    args = parse_arguments()
    input_dir = args.input_dir.resolve()
    raw_dir = args.raw_dir.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    payload_paths = sorted(input_dir.glob("*_icon_BNI.npy"))
    if not payload_paths:
        raise FileNotFoundError(f"No *_icon_BNI.npy payloads found in {input_dir}")

    device = torch.device(args.device)
    first_payload = np.load(payload_paths[0], allow_pickle=True).item()
    image_size = max(first_payload["mask"].shape)
    fillet_radius = max(1, round(image_size * args.fillet_radius_fraction)) if args.fillet_radius_fraction > 0 else 0
    config = {
        "k": args.k,
        "lambda1": args.lambda1,
        "boundary_consist": args.boundary_consist,
        "cut_intersection": not args.keep_intersections,
        "remove_stretched": not args.keep_stretched_faces,
        "fillet_radius": fillet_radius,
        "fillet_gradient_quantile": args.fillet_gradient_quantile,
    }
    all_stats = {}

    for payload_path in payload_paths:
        suffix = "_icon_BNI.npy"
        subject = payload_path.name[: -len(suffix)]
        raw_path = raw_dir / f"{subject}_icon_front_raw.npz"
        if not raw_path.exists():
            raise FileNotFoundError(f"Missing raw ICON tensor payload: {raw_path}")

        bni_payload = np.load(payload_path, allow_pickle=True).item()
        raw_payload = np.load(raw_path)
        integrator = BNI(
            dir_path=str(output_dir),
            name=subject,
            BNI_dict=bni_payload,
            cfg=config,
            device=device,
        )
        integrator.extract_surface(False)

        front_mesh = integrator.F_trimesh.copy()
        image_tensor = torch.from_numpy(raw_payload["image"]).unsqueeze(0).float().to(device)
        colors = query_color(
            torch.from_numpy(front_mesh.vertices).float(),
            torch.from_numpy(front_mesh.faces).long(),
            image_tensor,
            device=device,
            paint_normal=False,
        )
        front_mesh.visual.vertex_colors = colors.numpy().astype(np.uint8)

        obj_path = output_dir / f"{subject}_icon_front_bni.obj"
        glb_path = output_dir / f"{subject}_icon_front_bni.glb"
        depth_path = output_dir / f"{subject}_icon_front_depth.npy"
        preview_path = output_dir / f"{subject}_icon_front_depth.png"
        front_mesh.export(obj_path)
        front_mesh.export(glb_path)
        np.save(depth_path, integrator.F_depth.cpu().numpy())
        write_depth_preview(integrator.F_depth.cpu().numpy(), preview_path)

        all_stats[subject] = {
            "vertices": int(len(front_mesh.vertices)),
            "triangles": int(len(front_mesh.faces)),
            "components": int(len(front_mesh.split(only_watertight=False))),
            "bounds": front_mesh.bounds.tolist(),
            "extents": front_mesh.extents.tolist(),
            "watertight": bool(front_mesh.is_watertight),
            "source_payload": str(payload_path),
            "raw_tensor_payload": str(raw_path),
        }
        print(
            f"[ICON front d-BiNI] {subject}: "
            f"{len(front_mesh.vertices):,} vertices / {len(front_mesh.faces):,} triangles"
        )

    with (output_dir / "icon_front_bni_stats.json").open("w", encoding="utf-8") as handle:
        json.dump({"config": config, "subjects": all_stats}, handle, indent=2)


if __name__ == "__main__":
    main()
