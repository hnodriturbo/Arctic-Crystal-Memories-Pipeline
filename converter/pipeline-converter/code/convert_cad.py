"""
File: code/convert_cad.py
Purpose:
 - Convert Cockpit3D-style CAD coordinate rows into XYZ, PLY, and OBJ point clouds.
"""

import argparse
from pathlib import Path

from rich.console import Console

from utils.parsers import calculate_bounds, center_points, dedupe_points, parse_cad_points
from utils.writers import write_selected_formats


console = Console()
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def write_conversion_report(file_path, points, stats, output_paths, options):
    """Write a markdown conversion report with counts, bounds, and output paths."""
    reports_dir = PROJECT_ROOT / "output" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / f"{file_path.stem}_conversion.md"
    bounds = calculate_bounds(points)

    lines = [
        f"# CAD Conversion Report: {file_path.name}",
        "",
        "## Source",
        "",
        f"- Source file: `{file_path}`",
        "- Source file modified: `No`",
        "",
        "## Conversion Options",
        "",
        f"- Formats: `{', '.join(options['formats'])}`",
        f"- Limit: `{options['limit']}`",
        f"- Sample rate: `{options['sample_rate']}`",
        f"- Scale: `{options['scale']}`",
        f"- Centered: `{options['center']}`",
        f"- Deduplicated: `{options['dedupe']}`",
        "",
        "## Counts",
        "",
        f"- Total scanned lines: `{stats['total_lines']:,}`",
        f"- Skipped lines: `{stats['skipped_lines']:,}`",
        f"- Candidate coordinate rows: `{stats['candidate_rows']:,}`",
        f"- Exported points: `{len(points):,}`",
        "",
        "## Row Shape Counts",
        "",
    ]

    for row_shape, count in stats["row_shape_counts"].items():
        lines.append(f"- `{row_shape}`: `{count:,}`")

    lines.extend(["", "## Coordinate Bounds", ""])
    if bounds:
        for key, value in bounds.items():
            lines.append(f"- `{key}`: `{value}`")
    else:
        lines.append("- No points exported.")

    lines.extend(["", "## Output Files", ""])
    for format_name, output_path in output_paths.items():
        lines.append(f"- `{format_name}`: `{output_path}`")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


def main():
    parser = argparse.ArgumentParser(description="Convert Cockpit3D-style CAD files to point clouds.")
    parser.add_argument("--file", required=True, help="Path to the .cad file to convert.")
    parser.add_argument("--formats", nargs="+", default=["xyz"], choices=["xyz", "ply", "obj", "stl"],
                        help="Output formats (xyz, obj, stl).")
    parser.add_argument("--limit", type=int, default=None, help="Export only the first N points.")
    parser.add_argument("--sample-rate", type=int, default=1, help="Export every Nth candidate point.")
    parser.add_argument("--scale", type=float, default=1.0, help="Multiply all coordinates by this scale factor.")
    parser.add_argument("--center", action="store_true", help="Center point cloud around the origin.")
    parser.add_argument("--dedupe", action="store_true", help="Remove duplicate XYZ rows.")
    parser.add_argument("--stl-method", default="delaunay", choices=["delaunay", "convex"],
                        help="STL mesh method: delaunay (2.5D surface) or convex (closed hull). Default: delaunay.")
    parser.add_argument("--stl-limit", type=int, default=None,
                        help="Downsample to N points before STL triangulation.")
    args = parser.parse_args()

    file_path = Path(args.file).resolve()
    if not file_path.exists():
        raise FileNotFoundError(f"Input file not found: {file_path}")

    if args.sample_rate < 1:
        raise ValueError("--sample-rate must be 1 or greater.")

    console.print(f"[bold]Reading CAD file safely:[/bold] {file_path}")
    points, stats = parse_cad_points(
        file_path,
        limit=args.limit,
        sample_rate=args.sample_rate,
        scale=args.scale,
    )

    if args.dedupe:
        points = dedupe_points(points)

    if args.center:
        points = center_points(points)

    output_paths = write_selected_formats(points, file_path.stem, args.formats, PROJECT_ROOT,
                                          stl_method=getattr(args, "stl_method", "delaunay"),
                                          stl_limit=getattr(args, "stl_limit", None))
    options = {
        "formats": args.formats,
        "limit": args.limit,
        "sample_rate": args.sample_rate,
        "scale": args.scale,
        "center": args.center,
        "dedupe": args.dedupe,
    }
    report_path = write_conversion_report(file_path, points, stats, output_paths, options)

    console.print(f"[bold green]CAD conversion complete.[/bold green] Exported {len(points):,} points.")
    for format_name, output_path in output_paths.items():
        console.print(f"{format_name.upper()}: {output_path}")
    console.print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
