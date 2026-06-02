# =============================================================
# 06_scale_crystal.py — Scale mesh to crystal blank dimensions
# =============================================================
# PURPOSE:
#   Sixth and final step (Phase 6 — Crystal Scaling). Scales the
#   exported mesh to fit inside a chosen K9 crystal blank, applies
#   a clearance margin on all sides, centers the mesh, and exports
#   the crystal-ready file.
#
#   Full SSLE optimization (point density, laser preview) is handled
#   inside Cockpit3D. This step only scales and positions the mesh.
#
# CRYSTAL PRESETS (W x H x D in mm):
#   xs_cube   : 40 x 40 x 30   — Keychain / pendant
#   s_cube    : 60 x 60 x 40   — Small desk
#   m_cube    : 80 x 80 x 50   — Medium desk (most popular)
#   l_cube    : 100 x 100 x 60 — Large desk
#   xl_cube   : 120 x 120 x 80 — Extra large premium
#   s_rect    : 80 x 60 x 40   — Small landscape rectangle
#   m_rect    : 100 x 80 x 50  — Medium landscape rectangle
#   l_rect    : 120 x 80 x 60  — Large landscape rectangle
#   s_heart   : 80 x 80 x 40   — Heart shape (bounding box)
#   tower     : 60 x 60 x 100  — Tall pillar / standing portrait
#
# USAGE:
#   python 06_scale_crystal.py --crystal m_cube
#   python 06_scale_crystal.py --crystal-size 100 80 50
#   python 06_scale_crystal.py --list-crystals
#   python 06_scale_crystal.py --crystal l_cube --from-run export_01
#
# DEPENDENCIES: open3d, numpy, python-dotenv
# =============================================================

import argparse
import os
import sys
from pathlib import Path

import numpy as np
from dotenv import load_dotenv

PIPELINE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PIPELINE_DIR))
load_dotenv(PIPELINE_DIR / ".env")

from utils.file_utils import get_output_dir, latest_run_name

try:
    import open3d as o3d
except ImportError:
    print("ERROR: open3d not installed. Run: pip install open3d")
    sys.exit(1)


# ----------------------------------------------------------------
# CRYSTAL PRESETS
# ----------------------------------------------------------------
# All dimensions in millimeters: (W, H, D)
CRYSTAL_PRESETS: dict[str, tuple[float, float, float]] = {
    "xs_cube":  (40,  40,  30),
    "s_cube":   (60,  60,  40),
    "m_cube":   (80,  80,  50),
    "l_cube":   (100, 100, 60),
    "xl_cube":  (120, 120, 80),
    "s_rect":   (80,  60,  40),
    "m_rect":   (100, 80,  50),
    "l_rect":   (120, 80,  60),
    "s_heart":  (80,  80,  40),
    "tower":    (60,  60,  100),
}

DEFAULT_CRYSTAL = os.getenv("CRYSTAL_PRESET", "m_cube")
DEFAULT_MARGIN  = float(os.getenv("CRYSTAL_MARGIN_MM", "5.0"))


# ----------------------------------------------------------------
# SCALING LOGIC
# ----------------------------------------------------------------

def scale_to_crystal(
    mesh: o3d.geometry.TriangleMesh,
    crystal_w: float,
    crystal_h: float,
    crystal_d: float,
    margin_mm: float,
) -> o3d.geometry.TriangleMesh:
    """
    Scale and center the mesh to fit inside the crystal blank with margin.

    The longest mesh dimension is scaled to fit the smallest crystal dimension
    minus margin. Center is placed at origin, then lifted so Z=0 is the bottom.

    Args:
        mesh:       Input mesh (any scale)
        crystal_w:  Crystal width in mm
        crystal_h:  Crystal height in mm
        crystal_d:  Crystal depth in mm
        margin_mm:  Clearance on all sides in mm

    Returns:
        Scaled and positioned mesh in mm coordinates
    """
    bbox   = mesh.get_axis_aligned_bounding_box()
    extent = np.asarray(bbox.get_extent())

    # Available interior space after margin
    avail_w = crystal_w - 2 * margin_mm
    avail_h = crystal_h - 2 * margin_mm
    avail_d = crystal_d - 2 * margin_mm

    if any(v <= 0 for v in [avail_w, avail_h, avail_d]):
        raise ValueError(
            f"Margin {margin_mm}mm is too large for crystal {crystal_w}x{crystal_h}x{crystal_d}mm."
        )

    # Scale factor: smallest ratio (fit the most constrained dimension)
    scale_x = avail_w / extent[0] if extent[0] > 0 else 1.0
    scale_y = avail_h / extent[1] if extent[1] > 0 else 1.0
    scale_z = avail_d / extent[2] if extent[2] > 0 else 1.0
    scale   = min(scale_x, scale_y, scale_z)

    print(f"  Scale:   {scale:.4f}  (axis scales: x={scale_x:.3f} y={scale_y:.3f} z={scale_z:.3f})")

    mesh.scale(scale, center=bbox.get_center())

    # Center at origin
    bbox2 = mesh.get_axis_aligned_bounding_box()
    center = np.asarray(bbox2.get_center())
    mesh.translate(-center)

    # Lift so bottom of mesh sits at Z=0 (crystal base)
    bbox3 = mesh.get_axis_aligned_bounding_box()
    min_z = bbox3.get_min_bound()[2]
    mesh.translate([0, 0, -min_z])

    bbox4  = mesh.get_axis_aligned_bounding_box()
    extent4 = np.asarray(bbox4.get_extent())
    print(f"  Result:  {extent4[0]:.1f}mm x {extent4[1]:.1f}mm x {extent4[2]:.1f}mm")
    print(f"  Fits in: {crystal_w}mm x {crystal_h}mm x {crystal_d}mm  (margin={margin_mm}mm)")

    # Validate fit
    for i, (dim, avail, label) in enumerate(
        [(extent4[0], avail_w, "W"), (extent4[1], avail_h, "H"), (extent4[2], avail_d, "D")]
    ):
        if dim > avail + 0.01:
            print(f"  WARNING: mesh {label}={dim:.1f}mm exceeds available {avail:.1f}mm — check margin")

    return mesh


# ----------------------------------------------------------------
# SCANNER
# ----------------------------------------------------------------

def list_full_size_meshes(run: str) -> list[Path]:
    """Find mesh files in output/exports/{run}/full_size/."""
    export_base = get_output_dir("export", run)
    full_size_dir = export_base / "full_size"
    if not full_size_dir.exists():
        return []
    files = sorted(
        [p for p in full_size_dir.iterdir()
         if p.suffix in (".obj", ".ply", ".stl") and "_export" in p.name],
        key=lambda p: p.name.lower(),
    )
    print(f"Found {len(files)} export mesh(es) in: {full_size_dir}")
    return files


# ----------------------------------------------------------------
# CLI
# ----------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Step 06 — Scale mesh to K9 crystal blank dimensions"
    )
    parser.add_argument("--crystal", type=str, default=DEFAULT_CRYSTAL,
                        choices=list(CRYSTAL_PRESETS.keys()),
                        help=f"Crystal blank preset (default: {DEFAULT_CRYSTAL})")
    parser.add_argument("--crystal-size", type=float, nargs=3, metavar=("W", "H", "D"),
                        help="Custom crystal dimensions in mm. Overrides --crystal.")
    parser.add_argument("--margin", type=float, default=DEFAULT_MARGIN,
                        help=f"Clearance margin on all sides in mm (default: {DEFAULT_MARGIN})")
    parser.add_argument("--list-crystals", action="store_true",
                        help="Print all available crystal presets and exit")
    parser.add_argument("--file", type=str, default=None,
                        help="Process a single export mesh (name only)")
    parser.add_argument("--from-run", type=str, default=None,
                        help="Read exports from this export run (default: latest)")
    return parser.parse_args()


# ----------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------

def main() -> None:
    args = parse_args()

    if args.list_crystals:
        print("\nAvailable crystal presets (W x H x D in mm):\n")
        for name, (w, h, d) in CRYSTAL_PRESETS.items():
            print(f"  {name:<12}  {w:>3}mm x {h:>3}mm x {d:>3}mm")
        print()
        return

    if args.crystal_size:
        crystal_dims = tuple(args.crystal_size)
        preset_name = f"custom_{int(crystal_dims[0])}x{int(crystal_dims[1])}x{int(crystal_dims[2])}"
    else:
        crystal_dims = CRYSTAL_PRESETS[args.crystal]
        preset_name  = args.crystal

    crystal_w, crystal_h, crystal_d = crystal_dims

    export_run = latest_run_name("export", args.from_run)

    print("=" * 60)
    print("K9 Crystal Pipeline 03 Pro  —  Step 06: Crystal Scale")
    print(f"  Export run:  {export_run}")
    print(f"  Crystal:     {preset_name}  —  {crystal_w}mm x {crystal_h}mm x {crystal_d}mm")
    print(f"  Margin:      {args.margin}mm")
    print("=" * 60)

    mesh_files = list_full_size_meshes(export_run)
    if not mesh_files:
        print("ERROR: No export meshes found. Run step 05 first: python 05_export.py")
        sys.exit(1)

    if args.file:
        export_base = get_output_dir("export", export_run)
        targets = [export_base / "full_size" / args.file]
        if not targets[0].exists():
            print(f"ERROR: {args.file} not found")
            sys.exit(1)
    else:
        targets = mesh_files

    export_base = get_output_dir("export", export_run)
    crystal_dir = export_base / "crystal_size"
    crystal_dir.mkdir(parents=True, exist_ok=True)

    success_count = 0

    for mesh_path in targets:
        print(f"\nProcessing: {mesh_path.name}")

        try:
            mesh = o3d.io.read_triangle_mesh(str(mesh_path))
            if not mesh.has_vertices():
                print("  ERROR: could not read mesh — skipping")
                continue

            print(f"  Loaded: {len(np.asarray(mesh.vertices)):,} verts  {len(np.asarray(mesh.triangles)):,} tris")

            mesh = scale_to_crystal(mesh, crystal_w, crystal_h, crystal_d, args.margin)
            mesh.compute_vertex_normals()

            stem = mesh_path.stem.replace("_export", "")
            out_name = f"{stem}_{preset_name}{mesh_path.suffix}"
            out_path = crystal_dir / out_name

            o3d.io.write_triangle_mesh(str(out_path), mesh)
            print(f"  Saved:  {out_path.name}  ({out_path.stat().st_size / 1024:.0f} KB)")
            success_count += 1

        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()

    print()
    print("=" * 60)
    print("Step 06 complete.")
    print(f"  Scaled:  {success_count} mesh(es)")
    print(f"  Output:  output/exports/{export_run}/crystal_size/")
    print()
    print("  Import the crystal-sized OBJ into Cockpit3D.")
    print("  Cockpit3D will generate the laser point cloud.")
    print("=" * 60)


if __name__ == "__main__":
    main()
