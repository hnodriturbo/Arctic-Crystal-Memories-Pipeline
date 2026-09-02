"""
File: code/convert_dxf.py
Purpose:
 - Convert Cockpit3D DXF point clouds to XYZ, PLY, OBJ, and STL.
 - Uses a fast native group-code parser (no ezdxf dependency required).
"""

import argparse
from pathlib import Path

from rich.console import Console

from utils.parsers import calculate_bounds, center_points, dedupe_points, parse_dxf_points_fast
from utils.writers import write_selected_formats


console = Console()
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def write_conversion_report(file_path, points, output_paths, options):
    """Write a markdown report for DXF conversion results."""
    reports_dir = PROJECT_ROOT / "output" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / f"{file_path.stem}_conversion.md"
    bounds = calculate_bounds(points)

    lines = [
        f"# DXF Conversion Report: {file_path.name}",
        "",
        "## Source",
        f"- File: `{file_path}`",
        "- Source modified: No",
        "",
        "## Options",
        f"- Formats: `{', '.join(options['formats'])}`",
        f"- Limit: `{options['limit']}`",
        f"- Scale: `{options['scale']}`",
        f"- Centered: `{options['center']}`",
        f"- Deduplicated: `{options['dedupe']}`",
        f"- STL method: `{options.get('stl_method', 'delaunay')}`",
        "",
        "## Counts",
        f"- Points exported: `{len(points):,}`",
        "",
        "## Coordinate Bounds",
    ]

    if bounds:
        for key, value in bounds.items():
            lines.append(f"- `{key}`: `{value}`")
    else:
        lines.append("- No points.")

    lines += ["", "## Output Files"]
    for fmt, path in output_paths.items():
        lines.append(f"- `{fmt}`: `{path}`")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


def main():
    parser = argparse.ArgumentParser(description="Convert Cockpit3D DXF point clouds to XYZ/PLY/OBJ/STL.")
    parser.add_argument("--file", required=True, help="Path to the .dxf file.")
    parser.add_argument("--formats", nargs="+", default=["xyz"], choices=["xyz", "ply", "obj", "stl"],
                        help="Output formats (xyz, obj, stl).")
    parser.add_argument("--limit", type=int, default=None, help="Export only the first N points.")
    parser.add_argument("--scale", type=float, default=1.0, help="Scale factor for all coordinates.")
    parser.add_argument("--center", action="store_true", help="Center point cloud around origin.")
    parser.add_argument("--dedupe", action="store_true", help="Remove duplicate XYZ rows.")
    parser.add_argument("--stl-method", default="delaunay", choices=["delaunay", "convex"],
                        help="STL mesh method: delaunay (2.5D surface) or convex (closed hull). Default: delaunay.")
    parser.add_argument("--stl-limit", type=int, default=None,
                        help="Downsample to N points before STL triangulation (large files).")
    args = parser.parse_args()

    file_path = Path(args.file).resolve()
    if not file_path.exists():
        raise FileNotFoundError(f"Input file not found: {file_path}")

    console.print(f"[bold]Parsing DXF:[/bold] {file_path.name}")
    points = parse_dxf_points_fast(file_path, limit=args.limit, scale=args.scale)
    console.print(f"  Extracted [green]{len(points):,}[/green] points.")
    if not points:
        raise ValueError(
            "No POINT entities were found. Use mesh_to_pointcloud.py for a 3DFACE mesh DXF."
        )

    if args.dedupe:
        points = dedupe_points(points)
        console.print(f"  After dedupe: [green]{len(points):,}[/green] points.")

    if args.center:
        points = center_points(points)

    output_paths = write_selected_formats(
        points, file_path.stem, args.formats, PROJECT_ROOT,
        stl_method=args.stl_method, stl_limit=args.stl_limit
    )
    options = {
        "formats": args.formats,
        "limit": args.limit,
        "scale": args.scale,
        "center": args.center,
        "dedupe": args.dedupe,
        "stl_method": args.stl_method,
    }
    report_path = write_conversion_report(file_path, points, output_paths, options)

    console.print(f"[bold green]Done.[/bold green] {len(points):,} points.")
    for fmt, path in output_paths.items():
        console.print(f"  {fmt.upper()}: {path}")
    console.print(f"  Report: {report_path}")


if __name__ == "__main__":
    main()
