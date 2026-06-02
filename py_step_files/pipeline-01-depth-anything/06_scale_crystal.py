# =============================================================
# 06_scale_crystal.py — Scale mesh to physical crystal dimensions
# =============================================================
# PURPOSE:
#   Optional final step after 05_export.py. Takes the validated
#   full-size mesh and scales it to exact physical millimeter
#   dimensions matching a chosen K9 crystal blank.
#
#   Run this AFTER you are satisfied with the full-size export.
#   The full-size export stays untouched — this produces a second
#   copy in exports/crystal_size/{run}/ so you can compare both.
#
# CRYSTAL PRESETS (W x H x D in mm — all popular K9 blank sizes):
#
#   Key            W    H    D    Notes
#   ------------- ---- ---- ---- ----------------------------------------
#   xs_cube        40   40   30  Keychain / pendant
#   s_cube         60   60   40  Small desk, most common starter size
#   m_cube         80   80   50  Medium desk — most popular overall
#   l_cube        100  100   60  Large desk — high detail portraits
#   xl_cube       120  120   80  Extra large, high-end gift
#   s_rect         80   60   40  Small landscape rectangle
#   m_rect        100   60   40  Medium landscape rectangle — MOST POPULAR (default)
#   l_rect        120   80   60  Large landscape rectangle
#   s_heart        80   80   40  Heart shape (XY is outer bounding box)
#   tower          60   60  100  Tall pillar / standing portrait
#
# SCALING LOGIC:
#   Mesh is uniformly scaled so its longest proportional axis fits
#   exactly within the crystal blank dimensions. The margin is NOT
#   subtracted — the mesh is never stretched or forced into a shape.
#   It is scaled down proportionally by calculation.
#
#   Example: 800x800x800 mesh → 200x200x200 mm crystal scales to
#   200x200x200 mm (scale = 0.25 on all axes).
#   Example: 2000x1000x500 mesh → 100x60x40 mm crystal:
#     scale per axis = 0.05 / 0.06 / 0.08 → min = 0.05 → 100x50x25 mm
#
#   After scaling, a warning is printed if any axis is within
#   CRYSTAL_MARGIN_MM of the crystal edge — to alert you to rerun
#   with a smaller crystal or trim the mesh. The margin never
#   changes the scale factor.
#
# INPUTS:
#   - Full-size OBJ from output/exports/full_size/{run}/
#     (or any OBJ produced earlier in the pipeline)
#
# OUTPUTS:
#   - output/exports/crystal_size/{run}/{stem}_crystal_{preset}.obj
#   - output/exports/crystal_size/{run}/{stem}_crystal_{preset}.stl  (etc.)
#   - output/exports/crystal_size/{run}/{stem}_crystal_{preset}_report.txt
#   - output/exports/crystal_size/{run}/{stem}_crystal_{preset}_preview.png
#
# USAGE:
#   python 06_scale_crystal.py
#   python 06_scale_crystal.py --crystal m_cube
#   python 06_scale_crystal.py --crystal-size 100 80 50
#   python 06_scale_crystal.py --crystal l_rect --no-center
#   python 06_scale_crystal.py --list-crystals
#
# PowerShell one-liners:
#   .\.venv\Scripts\python.exe .\06_scale_crystal.py --list-crystals
#   .\.venv\Scripts\python.exe .\06_scale_crystal.py
#   .\.venv\Scripts\python.exe .\06_scale_crystal.py --crystal m_cube
#   .\.venv\Scripts\python.exe .\06_scale_crystal.py --crystal-size 100 80 50
#   .\.venv\Scripts\python.exe .\06_scale_crystal.py --crystal xl_cube --export-format obj
#   .\.venv\Scripts\python.exe .\06_scale_crystal.py --from-run export_01 --crystal s_cube
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
    tqdm = lambda it, **kw: it  # type: ignore[assignment]

DEFAULT_EXPORT_FMT = os.getenv("MESH_EXPORT_FORMAT", "all").lower()
DEFAULT_CRYSTAL    = os.getenv("CRYSTAL_PRESET", "m_cube")
DEFAULT_MARGIN     = float(os.getenv("CRYSTAL_MARGIN_MM", "5.0"))

FORMAT_EXT: dict[str, str] = {
    "obj": ".obj",
    "stl": ".stl",
    "ply": ".ply",
}

# ----------------------------------------------------------------
# CRYSTAL PRESETS — (W_mm, H_mm, D_mm)
# W = left-right, H = top-bottom, D = front-back (laser depth axis)
# All values are outer blank dimensions for common K9 stock sizes.
# ----------------------------------------------------------------
CRYSTAL_PRESETS: dict[str, tuple[float, float, float]] = {
    "xs_cube":  ( 40,  40,  30),   # keychain / pendant
    "s_cube":   ( 60,  60,  40),   # small desk — common starter
    "m_cube":   ( 80,  80,  50),   # medium desk — most popular
    "l_cube":   (100, 100,  60),   # large desk — portrait quality
    "xl_cube":  (120, 120,  80),   # extra large, premium gift
    "s_rect":   ( 80,  60,  40),   # small landscape rectangle
    "m_rect":   (100,  60,  40),   # medium landscape rectangle — most popular (default)
    "l_rect":   (120,  80,  60),   # large landscape rectangle
    "s_heart":  ( 80,  80,  40),   # heart (bounding box)
    "tower":    ( 60,  60, 100),   # tall pillar / standing portrait
}


def _resolve_formats(fmt_str: str) -> list[tuple[str, str]]:
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
# SCALE TO CRYSTAL
# ----------------------------------------------------------------

def scale_to_crystal(
    mesh: "o3d.geometry.TriangleMesh",
    crystal_dims: tuple[float, float, float],
    center_xy: bool,
) -> tuple["o3d.geometry.TriangleMesh", float]:
    """
    Uniformly scale mesh so it fits exactly within crystal_dims, then
    center in XY and place base at Z=0.

    Scaling is purely proportional — crystal_dims are the target container.
    The margin is never applied here; call check_margin_fit() separately to
    warn the user if the result is too close to the crystal edge.

    Returns (scaled_mesh, scale_factor).
    """
    bb  = mesh.get_axis_aligned_bounding_box()
    ext = bb.get_extent()

    # Uniform scale: each axis maps to its crystal dimension; take the min
    # so the mesh fits on all axes without exceeding the blank on any side.
    scale = min(crystal_dims[i] / float(ext[i]) for i in range(3) if float(ext[i]) > 0)

    mesh.scale(scale, center=mesh.get_center())

    bb2     = mesh.get_axis_aligned_bounding_box()
    min_pt  = bb2.get_min_bound()
    max_pt  = bb2.get_max_bound()
    center2 = (min_pt + max_pt) / 2.0

    if center_xy:
        tx = (crystal_dims[0] / 2.0) - center2[0]
        ty = (crystal_dims[1] / 2.0) - center2[1]
    else:
        tx = ty = 0.0

    # Place front face of mesh at Z = 0
    tz = -float(min_pt[2])

    mesh.translate([tx, ty, tz])
    mesh.compute_vertex_normals()
    return mesh, scale


def check_margin_fit(
    mesh: "o3d.geometry.TriangleMesh",
    crystal_dims: tuple[float, float, float],
    margin_mm: float,
) -> list[str]:
    """
    Return a list of warning strings if the scaled mesh is within margin_mm
    of any crystal edge. Empty list means the mesh fits comfortably.

    This is purely informational — it never changes the mesh.
    """
    bb  = mesh.get_axis_aligned_bounding_box()
    ext = bb.get_extent()
    warnings = []
    axis_names = ("W (left-right)", "H (top-bottom)", "D (front-back)")
    for i, name in enumerate(axis_names):
        gap = (crystal_dims[i] - float(ext[i])) / 2.0
        if gap < margin_mm:
            warnings.append(
                f"  WARNING: {name} axis — only {gap:.1f} mm clearance "
                f"(margin threshold: {margin_mm:.1f} mm). "
                f"Consider rerunning with a larger crystal or trimming the mesh."
            )
    return warnings


# ----------------------------------------------------------------
# PREVIEW
# ----------------------------------------------------------------

def save_preview(mesh: "o3d.geometry.TriangleMesh", out_path: Path) -> None:
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
        vis.scene.set_background([0.1, 0.1, 0.15, 1.0])

        img_pil = Image.fromarray(np.asarray(vis.render_to_image()))
        img_pil.save(str(out_path))
        print(f"  Preview → {out_path.name}")
    except Exception as e:
        print(f"  Preview skipped (headless renderer unavailable: {e})")
        Image.new("RGB", (800, 800), color=(25, 25, 40)).save(str(out_path))


# ----------------------------------------------------------------
# SAVE OUTPUTS
# ----------------------------------------------------------------

def save_crystal_export(
    mesh: "o3d.geometry.TriangleMesh",
    stem: str,
    preset_name: str,
    crystal_dims: tuple[float, float, float],
    export_dir: Path,
    formats: list[tuple[str, str]],
    scale_used: float,
) -> None:
    tris = len(np.asarray(mesh.triangles))
    bb   = mesh.get_axis_aligned_bounding_box()
    ext  = bb.get_extent()

    for fmt_name, ext_str in formats:
        out_path = export_dir / f"{stem}_crystal_{preset_name}{ext_str}"
        try:
            o3d.io.write_triangle_mesh(str(out_path), mesh)
            print(f"  {fmt_name.upper()} → {out_path.name}  ({tris:,} triangles)")
        except Exception as e:
            print(f"  ERROR saving {fmt_name}: {e}")

    report_path = export_dir / f"{stem}_crystal_{preset_name}_report.txt"
    lines = [
        f"Crystal scale report — {stem}",
        "=" * 50,
        f"Crystal preset:  {preset_name}",
        f"Crystal size:    {crystal_dims[0]:.0f} x {crystal_dims[1]:.0f} x {crystal_dims[2]:.0f} mm (W x H x D)",
        f"Scale factor:    {scale_used:.6f}",
        f"Final extents:   {float(ext[0]):.2f} x {float(ext[1]):.2f} x {float(ext[2]):.2f} mm",
        f"Triangles:       {tris:,}",
        "",
        "Ready to import into Cockpit3D.",
    ]
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  Report → {report_path.name}")

    save_preview(mesh, export_dir / f"{stem}_crystal_{preset_name}_preview.png")


# ----------------------------------------------------------------
# INPUT FILE DISCOVERY
# ----------------------------------------------------------------

def list_full_size_exports(run: str) -> list[Path]:
    """Find full-size OBJ exports written by 05_export.py."""
    base = get_output_dir("export", run) / "full_size"
    if not base.exists():
        return []
    files = sorted(
        [p for p in base.iterdir() if p.suffix.lower() == ".obj"],
        key=lambda p: p.name.lower(),
    )
    print(f"Found {len(files)} full-size OBJ file(s) in: {base}")
    return files


# ----------------------------------------------------------------
# CLI
# ----------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Stage 06 — Scale validated mesh to physical crystal dimensions"
    )
    parser.add_argument(
        "--list-crystals", action="store_true",
        help="Print all available crystal presets and exit"
    )
    parser.add_argument(
        "--file", type=str, default=None,
        help="Process a single OBJ file (name only, not full path)"
    )
    parser.add_argument(
        "--from-run", type=str, default=None,
        help="Read full-size exports from this run subfolder (default: latest)"
    )
    parser.add_argument(
        "--run", type=str, default=None,
        help="Write crystal exports to this run subfolder (default: same as from-run)"
    )
    parser.add_argument(
        "--crystal", type=str, default=DEFAULT_CRYSTAL,
        choices=list(CRYSTAL_PRESETS.keys()),
        metavar="PRESET",
        help=f"Crystal size preset (default: {DEFAULT_CRYSTAL}). Use --list-crystals to see all."
    )
    parser.add_argument(
        "--crystal-size", type=float, nargs=3, metavar=("W", "H", "D"),
        default=None,
        help="Custom crystal dimensions in mm: W H D (overrides --crystal)"
    )
    parser.add_argument(
        "--margin", type=float, default=DEFAULT_MARGIN,
        help=f"Safety margin in mm on all sides (default: {DEFAULT_MARGIN})"
    )
    parser.add_argument(
        "--no-center", action="store_true",
        help="Skip XY centering — leave subject at its original XY position"
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
    args = parse_args()

    if args.list_crystals:
        print("\nAvailable crystal presets (W x H x D in mm):\n")
        for name, (w, h, d) in CRYSTAL_PRESETS.items():
            print(f"  {name:<12}  {w:>4.0f} x {h:>4.0f} x {d:>4.0f} mm")
        print()
        sys.exit(0)

    # Resolve crystal dimensions
    if args.crystal_size:
        crystal_dims: tuple[float, float, float] = tuple(args.crystal_size)  # type: ignore[assignment]
        preset_name = f"custom_{int(args.crystal_size[0])}x{int(args.crystal_size[1])}x{int(args.crystal_size[2])}"
    else:
        crystal_dims = CRYSTAL_PRESETS[args.crystal]
        preset_name  = args.crystal

    formats = _resolve_formats(args.export_format)
    if not formats:
        print("ERROR: no valid export formats specified.")
        sys.exit(1)

    export_run = latest_run_name("export", args.from_run)
    out_run    = resolve_run_name("export", args.run or export_run)

    crystal_dir = get_output_dir("export", out_run) / "crystal_size"
    crystal_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Stage 06 — Crystal Size Scaling")
    print(f"  Source run:    {export_run}")
    print(f"  Output run:    {out_run}")
    print(f"  Crystal:       {preset_name}  "
          f"({crystal_dims[0]:.0f} x {crystal_dims[1]:.0f} x {crystal_dims[2]:.0f} mm)")
    print(f"  Margin:        {args.margin} mm")
    print(f"  Center XY:     {'yes' if not args.no_center else 'no'}")
    print(f"  Formats:       {', '.join(n for n, _ in formats)}")
    print("=" * 60)

    all_files = list_full_size_exports(export_run)
    if not all_files:
        print(f"No full-size OBJ exports found. Run 05_export.py first.")
        sys.exit(1)

    if args.file:
        targets = [p for p in all_files if p.name == args.file]
        if not targets:
            print(f"ERROR: {args.file} not found in run {export_run}")
            sys.exit(1)
    else:
        targets = all_files

    for obj_path in tqdm(targets, desc="Scaling to crystal"):
        t0 = time.time()
        print(f"\nProcessing: {obj_path.name}")
        try:
            mesh = o3d.io.read_triangle_mesh(str(obj_path))
            if len(np.asarray(mesh.vertices)) == 0:
                print("  ERROR: empty mesh — skipping")
                continue

            mesh, scale_used = scale_to_crystal(mesh, crystal_dims, not args.no_center)

            margin_warnings = check_margin_fit(mesh, crystal_dims, args.margin)
            for w in margin_warnings:
                print(w)

            save_crystal_export(mesh, obj_path.stem, preset_name, crystal_dims, crystal_dir, formats, scale_used)
            print(f"  Done in {time.time() - t0:.1f}s")

        except Exception as e:
            print(f"  ERROR processing {obj_path.name}: {e}")
            import traceback
            traceback.print_exc()

    print(f"\nStage 06 complete.")
    print(f"  Import the crystal-sized OBJ/STL from:  {crystal_dir}")
    print("  Then open in Cockpit3D to generate the laser point cloud.")


if __name__ == "__main__":
    main()
