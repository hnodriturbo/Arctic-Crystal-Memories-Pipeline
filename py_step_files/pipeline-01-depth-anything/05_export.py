# =============================================================
# 05_export.py — Mesh validation and full-size export
# =============================================================
# PURPOSE:
#   Fifth step. Validates the mesh from Stage 04, runs a cleanup
#   pass, and exports a production-ready full-size mesh.
#   "Full size" means model-space units (-1..+1 XY, 0..z_scale Z)
#   as produced by Stage 04. No physical millimeter scaling is
#   applied here — that is handled by 06_scale_crystal.py.
#
#   Keep the mesh large at this stage so you can inspect it in
#   Blender or Meshmixer before committing to a crystal preset.
#
# KEY OPERATIONS:
#   1. Validate mesh (watertight, orientable, self-intersections)
#   2. Light cleanup (degenerate/duplicate removal, normal recompute)
#   3. Export final mesh in format(s) from MESH_EXPORT_FORMAT in .env
#      (obj / stl / ply / all)
#   4. Write human-readable validation report (.txt)
#   5. Generate top-down preview PNG via Open3D offscreen renderer
#
# INPUTS:
#   - OBJ mesh from output/meshes/{run}/
#
# OUTPUTS:
#   - output/exports/full_size/{run}/{stem}_export.{ext}   (per format)
#   - output/exports/full_size/{run}/{stem}_report.txt
#   - output/exports/full_size/{run}/{stem}_preview.png
#
# USAGE:
#   python 05_export.py
#   python 05_export.py --file image_01_mesh.obj
#   python 05_export.py --from-run try_03 --run export_01
#   python 05_export.py --smooth 4
#   python 05_export.py --export-format obj
#
# PowerShell one-liners:
#   .\.venv\Scripts\python.exe .\05_export.py
#   .\.venv\Scripts\python.exe .\05_export.py --file image_01_upscaled_nobg_depth_anything_v2_depth_mesh.obj
#   .\.venv\Scripts\python.exe .\05_export.py --from-run try_03 --smooth 0
#   .\.venv\Scripts\python.exe .\05_export.py --export-format obj
#
# DEPENDENCIES: open3d, numpy, Pillow, python-dotenv, tqdm
# =============================================================

import argparse
import os
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image
from dotenv import load_dotenv

PIPELINE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PIPELINE_DIR))
load_dotenv(PIPELINE_DIR / ".env")

from utils.file_utils import get_output_dir, latest_run_name, resolve_run_name

try:
    import open3d as o3d
except ImportError:
    print("ERROR: open3d not installed. Run: pip install open3d")
    sys.exit(1)

try:
    from tqdm import tqdm
except ImportError:
    tqdm = lambda it, **__: it  # type: ignore[assignment]

DEFAULT_SMOOTH_ITERS = int(os.getenv("EXPORT_SMOOTH_ITERS", "2"))
DEFAULT_EXPORT_FMT   = os.getenv("MESH_EXPORT_FORMAT", "all").lower()

# Maps short format name to file extension
FORMAT_EXT: dict[str, str] = {
    "obj": ".obj",
    "stl": ".stl",
    "ply": ".ply",
}


def _resolve_formats(fmt_str: str) -> list[tuple[str, str]]:
    """Return list of (name, ext) pairs from a format string like 'all', 'obj', 'obj,stl'."""
    if fmt_str == "all":
        return list(FORMAT_EXT.items())
    formats = []
    for f in [x.strip() for x in fmt_str.split(",")]:
        if f in FORMAT_EXT:
            formats.append((f, FORMAT_EXT[f]))
        else:
            print(f"  Warning: unknown format '{f}' — skipped")
    return formats


# ----------------------------------------------------------------
# VALIDATION
# ----------------------------------------------------------------

def validate_mesh(mesh: "o3d.geometry.TriangleMesh") -> dict:
    """Run structural checks and collect stats. Returns a report dict."""
    verts = np.asarray(mesh.vertices)
    tris  = np.asarray(mesh.triangles)
    bb    = mesh.get_axis_aligned_bounding_box()
    ext   = bb.get_extent()

    report = {
        "vertex_count":      len(verts),
        "triangle_count":    len(tris),
        "bbox_x":            round(float(ext[0]), 4),
        "bbox_y":            round(float(ext[1]), 4),
        "bbox_z":            round(float(ext[2]), 4),
        "is_watertight":     bool(mesh.is_watertight()),
        "is_orientable":     bool(mesh.is_orientable()),
        "self_intersecting": bool(mesh.is_self_intersecting()),
        "pass":              False,
    }
    report["pass"] = (
        report["is_watertight"]
        and report["is_orientable"]
        and not report["self_intersecting"]
    )
    return report


def print_report(report: dict, stem: str) -> None:
    status = "PASS" if report["pass"] else "NEEDS REVIEW"
    print(f"\n  Validation [{status}]  {stem}")
    print(f"    Vertices:          {report['vertex_count']:,}")
    print(f"    Triangles:         {report['triangle_count']:,}")
    print(f"    Bounding box (model units): "
          f"{report['bbox_x']:.4f} x {report['bbox_y']:.4f} x {report['bbox_z']:.4f}")
    print(f"    Watertight:        {'OK' if report['is_watertight'] else 'FAIL'}")
    print(f"    Orientable:        {'OK' if report['is_orientable'] else 'FAIL'}")
    print(f"    Self-intersecting: {'WARN' if report['self_intersecting'] else 'OK'}")
    if not report["pass"]:
        print("  => Fix in Blender/Meshmixer before scaling to crystal size.")


def write_report(report: dict, stem: str, out_path: Path) -> None:
    lines = [
        f"Validation report — {stem}",
        "=" * 50,
        f"Vertices:          {report['vertex_count']:,}",
        f"Triangles:         {report['triangle_count']:,}",
        f"Bounding box (model units): "
        f"{report['bbox_x']:.4f} x {report['bbox_y']:.4f} x {report['bbox_z']:.4f}",
        "",
        f"Watertight:        {'PASS' if report['is_watertight'] else 'FAIL'}",
        f"Orientable:        {'PASS' if report['is_orientable'] else 'FAIL'}",
        f"Self-intersecting: {'WARN — fix before crystal import' if report['self_intersecting'] else 'OK'}",
        "",
        f"Overall: {'PASS — ready for 06_scale_crystal.py' if report['pass'] else 'NEEDS REVIEW — fix mesh before scaling'}",
    ]
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  Report → {out_path.name}")


# ----------------------------------------------------------------
# CLEANUP
# ----------------------------------------------------------------

def clean_mesh(mesh: "o3d.geometry.TriangleMesh", smooth_iters: int) -> "o3d.geometry.TriangleMesh":
    """Remove degenerate geometry and optionally smooth."""
    mesh.remove_degenerate_triangles()
    mesh.remove_duplicated_triangles()
    mesh.remove_duplicated_vertices()
    mesh.remove_non_manifold_edges()
    if smooth_iters > 0:
        mesh = mesh.filter_smooth_laplacian(number_of_iterations=smooth_iters)
    mesh.compute_vertex_normals()
    return mesh


# ----------------------------------------------------------------
# PREVIEW
# ----------------------------------------------------------------

def save_preview(mesh: "o3d.geometry.TriangleMesh", out_path: Path) -> None:
    """
    Render a top-down preview PNG using Open3D's offscreen renderer.
    Falls back to a dark placeholder if the headless renderer is unavailable.
    """
    try:
        vis = o3d.visualization.rendering.OffscreenRenderer(800, 800)  # type: ignore[attr-defined]
        mat = o3d.visualization.rendering.MaterialRecord()  # type: ignore[attr-defined]
        mat.shader = "defaultLit"
        vis.scene.add_geometry("mesh", mesh, mat)

        bb     = mesh.get_axis_aligned_bounding_box()
        center = bb.get_center()
        extent = float(max(bb.get_extent()))
        eye    = center + np.array([0.0, 0.0, extent * 2.0])
        vis.scene.camera.look_at(center, eye, np.array([0.0, 1.0, 0.0]))
        vis.scene.set_background([0.15, 0.15, 0.15, 1.0])

        img_pil = Image.fromarray(np.asarray(vis.render_to_image()))
        img_pil.save(str(out_path))
        print(f"  Preview → {out_path.name}")
    except Exception as e:
        print(f"  Preview skipped (headless renderer unavailable: {e})")
        Image.new("RGB", (800, 800), color=(30, 30, 30)).save(str(out_path))


# ----------------------------------------------------------------
# SAVE EXPORTS
# ----------------------------------------------------------------

def save_export(
    mesh: "o3d.geometry.TriangleMesh",
    report: dict,
    stem: str,
    export_dir: Path,
    formats: list[tuple[str, str]],
) -> None:
    for fmt_name, ext in formats:
        out_path = export_dir / f"{stem}_export{ext}"
        try:
            o3d.io.write_triangle_mesh(str(out_path), mesh)
            print(f"  {fmt_name.upper()} → {out_path.name}  ({report['triangle_count']:,} triangles)")
        except Exception as e:
            print(f"  ERROR saving {fmt_name}: {e}")

    write_report(report, stem, export_dir / f"{stem}_report.txt")
    save_preview(mesh, export_dir / f"{stem}_preview.png")


# ----------------------------------------------------------------
# MESH LOADER
# ----------------------------------------------------------------

def list_meshes(run: str) -> list[Path]:
    mesh_dir = get_output_dir("mesh", run)
    files = sorted(
        [p for p in mesh_dir.iterdir() if p.suffix.lower() == ".obj"],
        key=lambda p: p.name.lower(),
    )
    print(f"Found {len(files)} mesh file(s) in: {mesh_dir}")
    return files


# ----------------------------------------------------------------
# CLI
# ----------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Stage 05 — Validate mesh and export full-size files"
    )
    parser.add_argument(
        "--file", type=str, default=None,
        help="Process a single mesh file (name only, not full path)"
    )
    parser.add_argument(
        "--from-run", type=str, default=None,
        help="Read meshes from this run subfolder (default: latest)"
    )
    parser.add_argument(
        "--run", type=str, default=None,
        help="Write exports to this run subfolder (default: auto-increment)"
    )
    parser.add_argument(
        "--smooth", type=int, default=DEFAULT_SMOOTH_ITERS,
        help=f"Laplacian smooth iterations (0 = off, default: {DEFAULT_SMOOTH_ITERS})"
    )
    parser.add_argument(
        "--export-format", type=str, default=DEFAULT_EXPORT_FMT,
        help=f"Export format: obj, stl, ply, all, or comma-separated (default: {DEFAULT_EXPORT_FMT})"
    )
    return parser.parse_args()


# ----------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------

def main() -> None:
    args    = parse_args()
    formats = _resolve_formats(args.export_format)

    if not formats:
        print("ERROR: no valid export formats specified.")
        sys.exit(1)

    mesh_run   = latest_run_name("mesh",   args.from_run)
    export_run = resolve_run_name("export", args.run)

    # Full-size exports go into a sub-folder so they don't collide with crystal exports
    export_dir = get_output_dir("export", export_run) / "full_size"
    export_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Stage 05 — Mesh Validation & Full-Size Export")
    print(f"  Mesh run:      {mesh_run}")
    print(f"  Export run:    {export_run}")
    print(f"  Export dir:    {export_dir}")
    print(f"  Formats:       {', '.join(n for n, _ in formats)}")
    print(f"  Smooth iters:  {args.smooth}")
    print("=" * 60)

    all_meshes = list_meshes(mesh_run)
    if not all_meshes:
        print("No OBJ mesh files found. Run 04_mesh_generate.py first.")
        sys.exit(1)

    if args.file:
        targets = [p for p in all_meshes if p.name == args.file]
        if not targets:
            print(f"ERROR: {args.file} not found in run {mesh_run}")
            sys.exit(1)
    else:
        targets = all_meshes

    passed = 0
    for mesh_path in tqdm(targets, desc="Exporting"):
        t0 = time.time()
        print(f"\nProcessing: {mesh_path.name}")
        try:
            mesh = o3d.io.read_triangle_mesh(str(mesh_path))
            if len(np.asarray(mesh.vertices)) == 0:
                print("  ERROR: empty mesh — skipping")
                continue

            mesh   = clean_mesh(mesh, args.smooth)
            report = validate_mesh(mesh)
            print_report(report, mesh_path.stem)
            save_export(mesh, report, mesh_path.stem, export_dir, formats)

            if report["pass"]:
                passed += 1

            print(f"  Done in {time.time() - t0:.1f}s")
        except Exception as e:
            print(f"  ERROR processing {mesh_path.name}: {e}")
            import traceback
            traceback.print_exc()

    print(f"\nStage 05 complete — {passed}/{len(targets)} mesh(es) passed validation.")
    if passed < len(targets):
        print("  Fix failing meshes in Blender/Meshmixer, then re-run 05_export.py.")
    else:
        print("  Next: run 06_scale_crystal.py to scale to physical crystal dimensions.")


if __name__ == "__main__":
    main()
