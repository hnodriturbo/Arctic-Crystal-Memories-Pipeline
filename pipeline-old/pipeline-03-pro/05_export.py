# =============================================================
# 05_export.py — Mesh validation, cleanup, and export
# =============================================================
# PURPOSE:
#   Fifth step (Phase 5 — Artist Stage). Validates the geometry
#   and/or textured mesh from step 03/04b, applies light cleanup,
#   generates a quality report, and exports in production formats.
#
# INPUTS:
#   - output/meshes/{run}/geometry/  (vertex-colored mesh — Path A)
#   - output/meshes/{run}/textured/  (textured mesh — Path B, if exists)
#
# OUTPUTS:
#   - output/exports/{run}/full_size/{stem}_export.obj (.stl, .ply)
#   - output/exports/{run}/full_size/{stem}_report.txt
#
# SMOOTHING:
#   Default 0 passes. Smoothing is destructive — only apply when
#   explicitly requested with --smooth N. Smoothing loses facial
#   detail that cannot be recovered.
#
# DECIMATION:
#   Use --decimate N to reduce face count to N faces.
#   Default: no decimation (full resolution for Cockpit3D).
#
# USAGE:
#   python 05_export.py
#   python 05_export.py --smooth 2
#   python 05_export.py --decimate 1000000
#   python 05_export.py --export-format obj,stl
#   python 05_export.py --from-run try_01 --run export_01
#
# DEPENDENCIES: open3d, numpy, Pillow, python-dotenv, tqdm
# =============================================================

import argparse
import os
import sys
import time
from pathlib import Path

import numpy as np
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
    print("ERROR: tqdm not installed. Run: pip install tqdm")
    sys.exit(1)


DEFAULT_EXPORT_FMT    = os.getenv("MESH_EXPORT_FORMAT", "all").lower()
DEFAULT_SMOOTH_PASSES = int(os.getenv("MESH_SMOOTH_PASSES", "0"))


# ----------------------------------------------------------------
# VALIDATION
# ----------------------------------------------------------------

def validate_mesh(mesh: o3d.geometry.TriangleMesh) -> dict:
    """
    Run mesh quality checks and return a report dict.

    Checks: watertight, orientable, vertex/triangle counts, bounding box.
    """
    vertices  = np.asarray(mesh.vertices)
    triangles = np.asarray(mesh.triangles)
    bbox      = mesh.get_axis_aligned_bounding_box()
    extent    = np.asarray(bbox.get_extent())

    is_watertight   = mesh.is_watertight()
    is_orientable   = mesh.is_orientable()
    vertex_count    = len(vertices)
    triangle_count  = len(triangles)

    return {
        "vertex_count":    vertex_count,
        "triangle_count":  triangle_count,
        "is_watertight":   is_watertight,
        "is_orientable":   is_orientable,
        "bbox_x":          float(extent[0]),
        "bbox_y":          float(extent[1]),
        "bbox_z":          float(extent[2]),
    }


def write_report(report: dict, stem: str, out_dir: Path) -> Path:
    """Write a human-readable validation report to a text file."""
    report_path = out_dir / f"{stem}_report.txt"
    lines = [
        f"Mesh Validation Report — {stem}",
        "=" * 50,
        f"Vertex count:    {report['vertex_count']:,}",
        f"Triangle count:  {report['triangle_count']:,}",
        f"Watertight:      {'YES' if report['is_watertight'] else 'NO — has open edges'}",
        f"Orientable:      {'YES' if report['is_orientable'] else 'NO — mixed normals'}",
        f"Bounding box:    {report['bbox_x']:.4f} x {report['bbox_y']:.4f} x {report['bbox_z']:.4f}  (unit scale)",
        "",
        "Next step: python 06_scale_crystal.py --crystal m_cube",
    ]
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


# ----------------------------------------------------------------
# CLEANUP
# ----------------------------------------------------------------

def clean_mesh(
    mesh: o3d.geometry.TriangleMesh,
    smooth_passes: int = 0,
    decimate_target: int | None = None,
) -> o3d.geometry.TriangleMesh:
    """
    Apply light mesh cleanup: remove isolated components, optional smooth and decimate.

    Smoothing is disabled by default (smooth_passes=0). Only enable when the user
    explicitly requests it — smoothing is destructive and loses facial detail.
    """
    # Remove small isolated floating components
    triangle_clusters, cluster_n_triangles, _ = mesh.cluster_connected_triangles()
    triangle_clusters = np.asarray(triangle_clusters)
    cluster_n_triangles = np.asarray(cluster_n_triangles)

    if len(cluster_n_triangles) > 1:
        largest_cluster = cluster_n_triangles.argmax()
        triangles_to_remove = triangle_clusters != largest_cluster
        mesh.remove_triangles_by_mask(triangles_to_remove)
        mesh.remove_unreferenced_vertices()
        removed = int(triangles_to_remove.sum())
        if removed > 0:
            print(f"  Cleanup:  removed {removed:,} isolated triangles")

    mesh.remove_degenerate_triangles()
    mesh.remove_duplicated_triangles()
    mesh.remove_duplicated_vertices()
    mesh.remove_non_manifold_edges()

    if smooth_passes > 0:
        print(f"  Smooth:   {smooth_passes} Laplacian pass(es)  [WARNING: destructive — loses facial detail]")
        mesh = mesh.filter_smooth_laplacian(number_of_iterations=smooth_passes)

    if decimate_target is not None:
        current = len(np.asarray(mesh.triangles))
        if current > decimate_target:
            ratio = decimate_target / current
            print(f"  Decimate: {current:,} -> ~{decimate_target:,} triangles  (ratio={ratio:.3f})")
            try:
                mesh = mesh.simplify_quadric_decimation(decimate_target)
            except Exception as e:
                print(f"  Decimate ERROR: {e} — skipping decimation")

    mesh.compute_vertex_normals()
    return mesh


# ----------------------------------------------------------------
# SAVE EXPORTS
# ----------------------------------------------------------------

def save_exports(
    mesh: o3d.geometry.TriangleMesh,
    stem: str,
    out_dir: Path,
    export_fmt: str,
) -> None:
    """Save mesh in all requested formats to the export directory."""
    formats: list[tuple[str, str]] = []
    if export_fmt == "all":
        formats = [("obj", ".obj"), ("stl", ".stl"), ("ply", ".ply")]
    else:
        for fmt in [f.strip() for f in export_fmt.split(",")]:
            if fmt in ("obj", "stl", "ply"):
                formats.append((fmt, f".{fmt}"))

    tri_count = len(np.asarray(mesh.triangles))
    for fmt_name, ext in formats:
        out_path = out_dir / f"{stem}_export{ext}"
        try:
            o3d.io.write_triangle_mesh(str(out_path), mesh)
            print(f"  Export ({fmt_name.upper()}): {out_path.name}  ({tri_count:,} triangles)")
        except Exception as e:
            print(f"  ERROR saving {fmt_name}: {e}")


# ----------------------------------------------------------------
# MESH SCANNER
# ----------------------------------------------------------------

def list_geometry_meshes(run: str) -> list[Path]:
    """Find mesh files in output/meshes/{run}/geometry/."""
    mesh_base = get_output_dir("mesh", run)
    geo_dir = mesh_base / "geometry"
    if not geo_dir.exists():
        print(f"  No geometry/ subfolder in {mesh_base} — trying mesh root")
        files = sorted(
            [p for p in mesh_base.iterdir() if p.suffix in (".obj", ".ply") and "_mesh" in p.name],
            key=lambda p: p.name.lower(),
        )
    else:
        files = sorted(
            [p for p in geo_dir.iterdir() if p.suffix in (".obj", ".ply") and "_mesh" in p.name],
            key=lambda p: p.name.lower(),
        )
    print(f"Found {len(files)} geometry mesh(es)")
    return files


# ----------------------------------------------------------------
# CLI
# ----------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Step 05 — Validate, clean, and export mesh"
    )
    parser.add_argument("--file", type=str, default=None,
                        help="Process a single mesh file (name only, inside geometry/)")
    parser.add_argument("--export-format", type=str, default=DEFAULT_EXPORT_FMT,
                        help=f"Comma-separated formats: obj,stl,ply or 'all' (default: {DEFAULT_EXPORT_FMT})")
    parser.add_argument("--smooth", type=int, default=DEFAULT_SMOOTH_PASSES, metavar="N",
                        help=f"Laplacian smooth passes (default: {DEFAULT_SMOOTH_PASSES} — disabled). "
                             "Destructive — loses facial detail.")
    parser.add_argument("--decimate", type=int, default=None, metavar="N",
                        help="Reduce mesh to N triangles (default: none — full resolution)")
    parser.add_argument("--from-run", type=str, default=None,
                        help="Read meshes from this mesh run (default: latest)")
    parser.add_argument("--run", type=str, default=None,
                        help="Write exports to this export run (default: auto-increment)")
    return parser.parse_args()


# ----------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------

def main() -> None:
    args = parse_args()

    mesh_run   = latest_run_name("mesh", args.from_run)
    tag = None
    if args.file:
        tag = Path(args.file).stem
    export_run = resolve_run_name("export", args.run, tag=tag)

    print("=" * 60)
    print("K9 Crystal Pipeline 03 Pro  —  Step 05: Export")
    print(f"  Mesh run:     {mesh_run}")
    print(f"  Export run:   {export_run}")
    print(f"  Format:       {args.export_format}")
    print(f"  Smooth:       {args.smooth} pass(es)")
    print(f"  Decimate:     {args.decimate if args.decimate else 'disabled'}")
    print("=" * 60)

    mesh_files = list_geometry_meshes(mesh_run)
    if not mesh_files:
        print("ERROR: No geometry meshes found. Run step 03 first: python 03_mesh_generate.py")
        sys.exit(1)

    if args.file:
        mesh_base = get_output_dir("mesh", mesh_run)
        geo_dir = mesh_base / "geometry"
        candidate = geo_dir / args.file if geo_dir.exists() else mesh_base / args.file
        targets = [candidate]
        if not candidate.exists():
            print(f"ERROR: {args.file} not found")
            sys.exit(1)
    else:
        targets = mesh_files

    export_dir = get_output_dir("export", export_run)
    full_size_dir = export_dir / "full_size"
    full_size_dir.mkdir(parents=True, exist_ok=True)

    total_start = time.time()
    success_count = 0

    for mesh_path in tqdm(targets, desc="Exporting", unit="mesh"):
        print(f"\nProcessing: {mesh_path.name}")
        t0 = time.time()

        try:
            mesh = o3d.io.read_triangle_mesh(str(mesh_path))
            if not mesh.has_vertices():
                print(f"  ERROR: could not read mesh — skipping")
                continue

            print(f"  Loaded: {len(np.asarray(mesh.vertices)):,} verts  {len(np.asarray(mesh.triangles)):,} tris")

            # Validate before cleanup
            report = validate_mesh(mesh)
            print(f"  Watertight: {report['is_watertight']}  |  Orientable: {report['is_orientable']}")

            # Cleanup
            mesh = clean_mesh(mesh, smooth_passes=args.smooth, decimate_target=args.decimate)

            # Validate after cleanup
            report = validate_mesh(mesh)

            # Write report
            stem = mesh_path.stem.replace("_mesh", "")
            report_path = write_report(report, stem, full_size_dir)
            print(f"  Report: {report_path.name}")

            # Export
            save_exports(mesh, stem, full_size_dir, args.export_format)

            success_count += 1
            print(f"  Done in {time.time() - t0:.1f}s")

        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()

    total_elapsed = time.time() - total_start

    print()
    print("=" * 60)
    print("Step 05 complete.")
    print(f"  Exported:   {success_count} mesh(es)")
    print(f"  Total time: {total_elapsed:.1f}s")
    print(f"  Output:     output/exports/{export_run}/full_size/")
    print()
    print("  Read the _report.txt file — check face count and watertight status.")
    print("  Only proceed to step 06 if the mesh passes visual inspection.")
    print()
    print("Next step: python 06_scale_crystal.py --crystal m_cube")
    print("=" * 60)


if __name__ == "__main__":
    main()
