"""
File: code/utils/writers.py
Purpose:
 - Write extracted point clouds to simple viewer-friendly output formats.
"""

from pathlib import Path


def ensure_parent_directory(output_path):
    """Create the output folder before writing a generated point-cloud file."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)


def format_float(value):
    """Format coordinates cleanly while preserving useful decimal precision."""
    return f"{float(value):.8f}".rstrip("0").rstrip(".")


def write_xyz(points, output_path):
    """Write points to a plain XYZ file."""
    ensure_parent_directory(output_path)

    with open(output_path, "w", encoding="utf-8", newline="\n") as output_file:
        for x_coord, y_coord, z_coord in points:
            output_file.write(
                f"{format_float(x_coord)} {format_float(y_coord)} {format_float(z_coord)}\n"
            )


def write_ply(points, output_path):
    """Write points to an ASCII PLY point cloud file."""
    ensure_parent_directory(output_path)

    with open(output_path, "w", encoding="utf-8", newline="\n") as output_file:
        output_file.write("ply\n")
        output_file.write("format ascii 1.0\n")
        output_file.write(f"element vertex {len(points)}\n")
        output_file.write("property float x\n")
        output_file.write("property float y\n")
        output_file.write("property float z\n")
        output_file.write("end_header\n")

        for x_coord, y_coord, z_coord in points:
            output_file.write(
                f"{format_float(x_coord)} {format_float(y_coord)} {format_float(z_coord)}\n"
            )


def write_obj(points, output_path):
    """Write points as vertex-only OBJ rows."""
    ensure_parent_directory(output_path)

    with open(output_path, "w", encoding="utf-8", newline="\n") as output_file:
        output_file.write("# Vertex-only OBJ point cloud export.\n")
        output_file.write("# No mesh faces are included because source data contains points only.\n")

        for x_coord, y_coord, z_coord in points:
            output_file.write(
                f"v {format_float(x_coord)} {format_float(y_coord)} {format_float(z_coord)}\n"
            )


def write_selected_formats(points, source_name, formats, project_root):
    """Write requested point-cloud formats and return their output paths."""
    output_paths = {}

    if "xyz" in formats:
        xyz_path = project_root / "output" / "xyz" / f"{source_name}.xyz"
        write_xyz(points, xyz_path)
        output_paths["xyz"] = xyz_path

    if "ply" in formats:
        ply_path = project_root / "output" / "ply" / f"{source_name}.ply"
        write_ply(points, ply_path)
        output_paths["ply"] = ply_path

    if "obj" in formats:
        obj_path = project_root / "output" / "obj" / f"{source_name}.obj"
        write_obj(points, obj_path)
        output_paths["obj"] = obj_path

    return output_paths
