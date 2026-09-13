"""
File: code/rebuild_pointcloud.py
Purpose:
 - Take a POINT-cloud DXF the printer will not accept and re-emit it in the
   exact format it does accept, optionally resized, re-spaced and layered.

This is the repair and re-tune path. Use it when a Cockpit3D export loads
badly, when a job needs a different crystal size, or when dot spacing and
depth layering need changing without going back to the original model.

Honest limit: you cannot invent detail that is not in the source cloud.
Reducing --spacing keeps more of the points that already exist; once the
source's own density runs out, asking for tighter spacing changes nothing.
"""

import argparse
import sys
from pathlib import Path

import numpy as np
from rich.console import Console

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).parent))

from utils.printer_dxf import (  # noqa: E402
    CRYSTAL_TEMPLATES,
    DEFAULT_POINT_DISTANCE,
    apply_depth_layers,
    detect_dxf_kind,
    fit_points_to_template,
    read_point_dxf,
    resolve_template,
    thin_to_grid,
    write_printer_dxf,
)

console = Console()


def estimate_native_spacing(points):
    """Rough dot pitch from bounding volume per point, so we can warn when
    asking for tighter spacing would change nothing."""
    if len(points) < 2:
        return 0.0
    extent = np.maximum(points.max(axis=0) - points.min(axis=0), 1e-9)

    # Engraved clouds are surfaces inside a box, so area per point models the
    # pitch far better than volume per point would.
    surface = 2.0 * (extent[0] * extent[1] + extent[1] * extent[2] + extent[0] * extent[2])
    return float((surface / len(points)) ** 0.5)


def rebuild(source_path, output_dir, args):
    """Read one POINT DXF, apply the requested changes, and write a printer-ready copy."""
    console.print(f"[bold cyan]Source:[/bold cyan] {source_path.name}")

    kind = detect_dxf_kind(source_path)
    if kind == "mesh":
        console.print(
            "[red]This DXF is a triangle mesh, not a point cloud. "
            "Run mesh_to_pointcloud.py on it instead.[/red]"
        )
        return None
    if kind == "unknown":
        console.print("[yellow]No POINT or 3DFACE entities recognised - trying anyway.[/yellow]")

    console.print("  Reading points...")
    points = read_point_dxf(source_path)
    if len(points) == 0:
        console.print("[red]No POINT entities found.[/red]")
        return None

    lower, upper = points.min(axis=0), points.max(axis=0)
    console.print(
        f"  [green]{len(points):,}[/green] points  "
        f"{upper[0] - lower[0]:.1f} x {upper[1] - lower[1]:.1f} x {upper[2] - lower[2]:.1f} mm"
    )
    native = estimate_native_spacing(points)
    console.print(f"  Native dot pitch is roughly {native:.4f} mm")

    # Resizing is opt-in; a pure format repair should not move a single coordinate.
    if args.resize:
        template = resolve_template(
            args.template, args.width, args.height, args.depth, args.border
        )
        points, scale, mapping, binding = fit_points_to_template(
            points, template, args.swap_yz, args.flip,
            args.auto_orient, args.upright, args.depth_axis,
        )
        console.print(
            f"  Refitted to {template['width']:g} x {template['height']:g} x "
            f"{template['depth']:g} mm (border {template['border']:g} mm, "
            f"scale x{scale:.4g}, limited by {binding})"
        )
    elif args.scale and args.scale != 1.0:
        centre = (upper + lower) / 2.0
        points = (points - centre) * args.scale + centre
        console.print(f"  Scaled by x{args.scale:g}")

    if args.spacing:
        before = len(points)
        z_step = args.z_distance if args.z_distance else args.spacing
        points, _ = thin_to_grid(points, args.spacing, z_step)
        console.print(
            f"  Re-spaced at {args.spacing:g} mm (Z {z_step:g} mm): "
            f"{before:,} -> [green]{len(points):,}[/green] points"
        )
        if args.spacing < native * 0.9 and len(points) > before * 0.95:
            console.print(
                "  [yellow]Spacing is finer than the source's own density, so almost "
                "nothing was removed. Re-run from the original mesh for real detail.[/yellow]"
            )

    if args.layers or args.layer_spacing:
        points = apply_depth_layers(
            points, args.layers, args.layer_spacing, args.stagger,
            args.spacing or DEFAULT_POINT_DISTANCE,
        )
        layer_note = (
            f"{args.layer_spacing:g} mm apart" if args.layer_spacing else f"{args.layers} layers"
        )
        console.print(f"  Depth layering: {layer_note}, stagger {args.stagger}")

    if args.limit and len(points) > args.limit:
        step = len(points) / args.limit
        points = points[(np.arange(args.limit) * step).astype(np.int64)]
        console.print(f"  Capped at {len(points):,} points")

    lower, upper = points.min(axis=0), points.max(axis=0)
    console.print(
        f"  X [{lower[0]:.2f}, {upper[0]:.2f}]  "
        f"Y [{lower[1]:.2f}, {upper[1]:.2f}]  "
        f"Z [{lower[2]:.2f}, {upper[2]:.2f}]"
    )

    stem = f"{source_path.stem}-rebuilt-{len(points)}points"
    dxf_path = output_dir / f"{stem}.dxf"
    write_printer_dxf(points, dxf_path)
    console.print(
        f"  [green]Wrote[/green] {dxf_path.name} "
        f"({dxf_path.stat().st_size / 1_048_576:.1f} MB)"
    )

    if args.xyz:
        xyz_path = output_dir / f"{stem}.xyz"
        xyz_path.parent.mkdir(parents=True, exist_ok=True)
        np.savetxt(xyz_path, points, fmt="%.4f", delimiter=" ")
        console.print(f"  [green]Wrote[/green] {xyz_path.name}")

    return dxf_path


def build_parser():
    parser = argparse.ArgumentParser(
        description="Repair, resize and re-space an existing POINT-cloud DXF for the SSLE engraver."
    )
    parser.add_argument("--file", nargs="+", required=True, help="POINT-cloud DXF files.")

    parser.add_argument(
        "--resize", action="store_true",
        help="Refit the cloud into a crystal blank. Without this, coordinates are left alone."
    )
    parser.add_argument("--template", default="60x80x40", choices=sorted(CRYSTAL_TEMPLATES))
    parser.add_argument("--width", type=float, help="Override template width in mm.")
    parser.add_argument("--height", type=float, help="Override template height in mm.")
    parser.add_argument("--depth", type=float, help="Override template depth in mm.")
    parser.add_argument(
        "--border", type=float,
        help="Unengraved margin per side in mm (default 1; minimum 0.1)."
    )
    parser.add_argument(
        "--scale", type=float, default=1.0,
        help="Plain multiplier about the centre, when --resize is too much."
    )

    parser.add_argument(
        "--spacing", type=float, default=0.0,
        help="Re-space dots onto this grid in mm; 0 keeps every point as-is."
    )
    parser.add_argument(
        "--z-distance", type=float, default=0.0,
        help="Separate spacing along depth; 0 reuses the XY spacing."
    )
    parser.add_argument("--limit", type=int, default=0, help="Hard cap on point count; 0 is none.")

    parser.add_argument("--layers", type=int, default=0,
                        help="Snap depth onto this many engraving planes.")
    parser.add_argument("--layer-spacing", type=float, default=0.0,
                        help="Millimetres between engraving planes; overrides --layers.")
    parser.add_argument("--stagger", type=int, default=1,
                        help="Offset alternate layers so dots do not stack into columns.")

    parser.add_argument("--swap-yz", action="store_true", help="Swap Y and Z.")
    parser.add_argument("--flip", default="", help="Axes to mirror, e.g. 'x' or 'xz'.")
    parser.add_argument("--auto-orient", action="store_true",
                        help="Rotate onto the axis mapping that fills the blank best.")
    parser.add_argument("--upright", nargs="?", const="auto", default=None,
                        choices=["auto", "x", "y", "z"],
                        help="Pin a source axis to crystal height.")
    parser.add_argument("--depth-axis", default=None, choices=["x", "y", "z"],
                        help="Which source axis faces the viewer.")

    parser.add_argument("--xyz", action="store_true", help="Also write an XYZ preview file.")
    parser.add_argument("--out", default=None, help="Output directory.")
    return parser


def main():
    args = build_parser().parse_args()
    output_dir = Path(args.out) if args.out else PROJECT_ROOT / "output" / "rebuilt_dxf"
    output_dir.mkdir(parents=True, exist_ok=True)

    console.print("[bold]Rebuild Point Cloud - SSLE printable DXF[/bold]")
    console.print(f"Output: {output_dir}\n")

    for file_argument in args.file:
        source = Path(file_argument).resolve()
        if not source.exists():
            console.print(f"[red]File not found: {source}[/red]")
            sys.exit(1)
        rebuild(source, output_dir, args)
        console.print("")


if __name__ == "__main__":
    main()
