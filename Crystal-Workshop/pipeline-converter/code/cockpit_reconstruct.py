"""
Purpose:
 - Run the Cockpit Reconstruct operator job using existing parsers and mesh writers.
 - Save isolated GLB/STL results and a reproducible report, never modify inputs.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from uuid import uuid4

from utils.parsers import parse_cad_points, parse_dxf_points_fast, dedupe_points, center_points, calculate_bounds
from utils.writers import reconstruct_mesh, write_glb, write_stl
from utils.relief_surface import reconstruct_relief
from prepare_showroom import PRESET, smooth_boundary, unlit_glb
from utils.scene_transform import read_scene_transform
from utils.reconstruction_provenance import build_provenance, embed_provenance
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path)
    parser.add_argument("--inspect-scene", type=Path)
    parser.add_argument("--output-subdir", default='cockpit-reconstruct')
    parser.add_argument("--pose-override", action="store_true")
    for kind in ('rotation', 'position'):
        for axis in 'xyz':
            parser.add_argument(f'--pose-{kind}-{axis}', type=float, default=0)
    parser.add_argument("--sample-rate", type=int, default=1)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--stl-limit", type=int, default=PRESET['maxVertices'])
    parser.add_argument("--stl-method", choices=["smooth", "delaunay", "convex"], default="smooth")
    parser.add_argument("--grid-resolution", type=int, default=PRESET['resolution'])
    parser.add_argument("--smoothing", type=float, default=PRESET['smoothing'])
    parser.add_argument("--gap", type=float, default=PRESET['gap'])
    parser.add_argument("--surface-percentile", type=float, default=85.0)
    parser.add_argument("--front", choices=["positive", "negative"], default="positive")
    parser.add_argument("--color-mode", choices=["texture", "vertex"], default="texture")
    parser.add_argument("--dedupe", action="store_true")
    parser.add_argument("--center", action="store_true")
    parser.add_argument("--texture-from", type=Path)
    parser.add_argument("--texture-plane", choices=["auto", "xy", "xz", "yz"], default="xy")
    parser.add_argument("--flip-u", action="store_true")
    parser.add_argument("--flip-v", action="store_true")
    parser.add_argument("--repair-lower", action="store_true", help="Experimental ridge repair limited to the bottom 42%; upper geometry is unchanged.")
    parser.add_argument("--lower-repair-strength", type=float, default=1.0,
                        help="1–3: suppress progressively wider lower-body ridges.")
    args = parser.parse_args()
    if args.inspect_scene:
        _, _, metadata = read_scene_transform(args.inspect_scene)
        print('ACM_SCENE_POSE=' + json.dumps(metadata), flush=True)
        return
    if not args.file:
        parser.error('--file is required for reconstruction.')
    if Path(args.output_subdir).is_absolute() or '..' in Path(args.output_subdir).parts:
        parser.error('Output subdirectory must remain inside output/.')
    if args.sample_rate < 1 or args.limit < 0 or not 3 <= args.stl_limit <= 500000:
        parser.error("Use sample rate >= 1, limit >= 0 and mesh budget between 3 and 500000.")
    if not (64 <= args.grid_resolution <= 768 and 0 <= args.smoothing <= 5
            and 0 <= args.gap <= 8 and 0 <= args.surface_percentile <= 100
            and 1 <= args.lower_repair_strength <= 3):
        parser.error("Use grid 64–768, smoothing 0–5, gap 0–8 and percentile 0–100.")
    print(f"Reading {args.file.name}; keeping every {args.sample_rate}th point.", flush=True)
    options = dict(limit=args.limit or None, sample_rate=args.sample_rate)
    if args.file.suffix.lower() == ".dxf":
        points = parse_dxf_points_fast(args.file, **options)
    elif args.file.suffix.lower() == ".cad":
        points, _ = parse_cad_points(args.file, **options)
    else:
        parser.error("Select a Cockpit3D POINT DXF or CAD export.")
    sampled_count = len(points)
    if args.dedupe:
        points = dedupe_points(points)
    pose = None
    build_points = None
    if args.stl_method == 'smooth' and args.texture_from and args.color_mode == 'texture' and args.texture_plane == 'xy':
        raw = np.asarray(points, dtype=float)
        rotation, position, pose = read_scene_transform(args.texture_from)
        if args.pose_override:
            from utils.scene_transform import override_scene_transform
            rotation, position, pose = override_scene_transform(pose,
                [getattr(args, f'pose_rotation_{axis}') for axis in 'xyz'],
                [getattr(args, f'pose_position_{axis}') for axis in 'xyz'])
        output_center = (raw.min(axis=0) + raw.max(axis=0)) / 2 if args.center else np.zeros(3)
        build_points = rotation.inv().apply(raw - position)
    if args.center:
        points = center_points(points)
    print(f"Sampled {sampled_count:,}; reconstructing {len(points):,} points.", flush=True)
    if args.stl_method == "smooth":
        mesh = reconstruct_relief(build_points if build_points is not None else points, args.grid_resolution, args.smoothing, args.gap,
                                  args.surface_percentile, args.front, args.stl_limit, args.repair_lower,
                                  args.lower_repair_strength)
    else:
        mesh = reconstruct_mesh(points, args.stl_method, args.stl_limit)
    job_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-") + uuid4().hex[:8]
    directory = ROOT / "output" / args.output_subdir
    glb = directory / f"{job_id}.glb"
    stl = directory / f"{job_id}.stl"
    report_path = directory / f"{job_id}.json"
    # A failed color pass never leaves a finished-looking job behind.
    try:
        if args.stl_method == 'smooth' and args.color_mode == 'texture' and args.texture_from and args.texture_plane == 'xy':
            # Match the approved showroom finish while keeping UV bounds fixed before edge relaxation.
            import trimesh
            from utils.photo_projection import photo_uv
            original, faces = mesh
            vertices = smooth_boundary(original, faces, PRESET['boundaryIterations'], PRESET['boundaryMaximumMm'])
            photo, _ = photo_uv(original, args.texture_from, 'xy')
            uv = (vertices[:, :2] - original[:, :2].min(axis=0)) / np.ptp(original[:, :2], axis=0)
            if args.flip_u:
                uv[:, 0] = 1 - uv[:, 0]
            if args.flip_v:
                uv[:, 1] = 1 - uv[:, 1]
            vertices = rotation.apply(vertices) + position - output_center
            model = trimesh.Trimesh(vertices=vertices * 0.001, faces=faces, process=False)
            model.visual = trimesh.visual.TextureVisuals(uv=uv, material=trimesh.visual.material.PBRMaterial(
                baseColorTexture=photo, metallicFactor=0, roughnessFactor=1, doubleSided=True))
            glb.parent.mkdir(parents=True, exist_ok=True)
            glb.write_bytes(unlit_glb(model))
            mesh = vertices, faces
        else:
            write_glb(mesh, glb, args.texture_from, args.texture_plane, args.flip_u, args.flip_v, args.color_mode)
        write_stl(points, stl, mesh=mesh)
        report = {
            "jobId": job_id, "source": args.file.name, "sampledPoints": sampled_count,
            "vertices": len(mesh[0]), "triangles": len(mesh[1]), "boundsMm": calculate_bounds(points),
            "colored": bool(args.texture_from), "glbBytes": glb.stat().st_size,
            "finishPreset": PRESET['name'] if args.stl_method == 'smooth' and args.color_mode == 'texture' and args.texture_from and args.texture_plane == 'xy' else None,
            "sceneTransform": pose,
            "options": {key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()},
            "files": {"glb": f"{args.output_subdir}/{glb.name}", "stl": f"{args.output_subdir}/{stl.name}", "report": f"{args.output_subdir}/{report_path.name}"},
        }
        report['provenance'] = build_provenance(args.file, args.texture_from, report)
        embed_provenance(glb, report['provenance'])
        report['glbBytes'] = glb.stat().st_size
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    except Exception:
        glb.unlink(missing_ok=True)
        stl.unlink(missing_ok=True)
        raise
    print(f"Surface: {len(mesh[0]):,} vertices / {len(mesh[1]):,} triangles; GLB {glb.stat().st_size:,} bytes.")
    print("ACM_RECONSTRUCT_JOB=" + json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
