"""
File: code/convert_dxf.py
Purpose:
 - Convert DXF point-like geometry into XYZ, PLY, and OBJ point-cloud files.
"""

import argparse
from pathlib import Path

import ezdxf
from rich.console import Console

from utils.parsers import calculate_bounds, center_points, dedupe_points
from utils.writers import write_selected_formats


console = Console()
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def append_point(points, point):
    """Normalize an ezdxf point-like value into a plain XYZ tuple."""
    points.append((float(point[0]), float(point[1]), float(point[2]) if len(point) > 2 else 0.0))


def extract_polyline_points(entity, points):
    """Extract vertices from legacy POLYLINE entities."""
    for vertex in entity.vertices:
        append_point(points, vertex.dxf.location)


def extract_lwpolyline_points(entity, points):
    """Extract XY vertices from lightweight polylines and set Z from elevation."""
    elevation = float(getattr(entity.dxf, "elevation", 0.0))
    for vertex in entity.get_points("xy"):
        points.append((float(vertex[0]), float(vertex[1]), elevation))


def extract_dxf_points(file_path):
    """Extract point-like geometry from DXF modelspace."""
    document = ezdxf.readfile(file_path)
    modelspace = document.modelspace()
    points = []
    entity_counts = {}

    for entity in modelspace:
        entity_type = entity.dxftype()
        entity_counts[entity_type] = entity_counts.get(entity_type, 0) + 1

        if entity_type == "POINT":
            append_point(points, entity.dxf.location)
        elif entity_type == "LINE":
            append_point(points, entity.dxf.start)
            append_point(points, entity.dxf.end)
        elif entity_type == "3DFACE":
            append_point(points, entity.dxf.vtx0)
            append_point(points, entity.dxf.vtx1)
            append_point(points, entity.dxf.vtx2)
            append_point(points, entity.dxf.vtx3)
        elif entity_type == "POLYLINE":
            extract_polyline_points(entity, points)
        elif entity_type == "LWPOLYLINE":
            extract_lwpolyline_points(entity, points)

    return points, entity_counts


def write_conversion_report(file_path, points, entity_counts, output_paths, options):
    """Write a markdown report for DXF conversion results."""
    reports_dir = PROJECT_ROOT / "output" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / f"{file_path.stem}_conversion.md"
    bounds = calculate_bounds(points)

    lines = [
        f"# DXF Conversion Report: {file_path.name}",
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
        f"- Scale: `{options['scale']}`",
        f"- Centered: `{options['center']}`",
        f"- Deduplicated: `{options['dedupe']}`",
        "",
        "## Counts",
        "",
        f"- Exported points: `{len(points):,}`",
        "",
        "## DXF Entity Counts",
        "",
    ]

    for entity_type, count in sorted(entity_counts.items()):
        lines.append(f"- `{entity_type}`: `{count:,}`")

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
    parser = argparse.ArgumentParser(description="Convert DXF point-like geometry to point clouds.")
    parser.add_argument("--file", required=True, help="Path to the .dxf file to convert.")
    parser.add_argument("--formats", nargs="+", default=["xyz"], choices=["xyz", "ply", "obj"], help="Output formats.")
    parser.add_argument("--limit", type=int, default=None, help="Export only the first N points.")
    parser.add_argument("--scale", type=float, default=1.0, help="Multiply all coordinates by this scale factor.")
    parser.add_argument("--center", action="store_true", help="Center point cloud around the origin.")
    parser.add_argument("--dedupe", action="store_true", help="Remove duplicate XYZ rows.")
    args = parser.parse_args()

    file_path = Path(args.file).resolve()
    if not file_path.exists():
        raise FileNotFoundError(f"Input file not found: {file_path}")

    console.print(f"[bold]Reading DXF file:[/bold] {file_path}")
    points, entity_counts = extract_dxf_points(file_path)

    if args.scale != 1.0:
        points = [
            (x_coord * args.scale, y_coord * args.scale, z_coord * args.scale)
            for x_coord, y_coord, z_coord in points
        ]

    if args.dedupe:
        points = dedupe_points(points)

    if args.center:
        points = center_points(points)

    if args.limit is not None:
        points = points[: args.limit]

    output_paths = write_selected_formats(points, file_path.stem, args.formats, PROJECT_ROOT)
    options = {
        "formats": args.formats,
        "limit": args.limit,
        "scale": args.scale,
        "center": args.center,
        "dedupe": args.dedupe,
    }
    report_path = write_conversion_report(file_path, points, entity_counts, output_paths, options)

    console.print(f"[bold green]DXF conversion complete.[/bold green] Exported {len(points):,} points.")
    for format_name, output_path in output_paths.items():
        console.print(f"{format_name.upper()}: {output_path}")
    console.print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
