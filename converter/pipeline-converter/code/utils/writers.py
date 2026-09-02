"""
File: code/utils/writers.py
Purpose:
 - Write extracted point clouds to XYZ, PLY, OBJ, and STL formats.
"""

from pathlib import Path

import numpy as np


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


def write_obj(points, output_path, method="delaunay", stl_limit=None):
    """Write a triangulated mesh OBJ using Delaunay or ConvexHull — produces real faces, not vertex-only."""
    from scipy.spatial import Delaunay, ConvexHull  # noqa: PLC0415

    ensure_parent_directory(output_path)
    pts = np.array(points, dtype=np.float64)

    if stl_limit and len(pts) > stl_limit:
        step = len(pts) // stl_limit
        pts = pts[::step]

    if method == "convex":
        hull = ConvexHull(pts)
        simplices = hull.simplices
    else:
        tri = Delaunay(pts[:, :2])
        simplices = tri.simplices

    with open(output_path, "w", encoding="utf-8", newline="\n") as f:
        for x, y, z in pts:
            f.write(f"v {format_float(x)} {format_float(y)} {format_float(z)}\n")
        for face in simplices:
            f.write(f"f {face[0]+1} {face[1]+1} {face[2]+1}\n")


def write_stl(points, output_path, method="delaunay", stl_limit=None):
    """Write a binary STL mesh from a point cloud using Delaunay or ConvexHull triangulation."""
    from scipy.spatial import Delaunay, ConvexHull  # noqa: PLC0415

    ensure_parent_directory(output_path)
    pts = np.array(points, dtype=np.float32)

    if stl_limit and len(pts) > stl_limit:
        step = len(pts) // stl_limit
        pts = pts[::step]

    if method == "convex":
        hull = ConvexHull(pts)
        simplices = hull.simplices.astype(np.int32)
    else:
        # 2.5D Delaunay on XY plane — best for K9 crystal engravings
        tri = Delaunay(pts[:, :2])
        simplices = tri.simplices.astype(np.int32)

    v0 = pts[simplices[:, 0]]
    v1 = pts[simplices[:, 1]]
    v2 = pts[simplices[:, 2]]

    normals = np.cross(v1 - v0, v2 - v0).astype(np.float32)
    norms = np.linalg.norm(normals, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    normals /= norms

    n_faces = len(simplices)
    stl_dtype = np.dtype([
        ("normal", np.float32, (3,)),
        ("v0", np.float32, (3,)),
        ("v1", np.float32, (3,)),
        ("v2", np.float32, (3,)),
        ("attr", np.uint16),
    ])
    stl_data = np.zeros(n_faces, dtype=stl_dtype)
    stl_data["normal"] = normals
    stl_data["v0"] = v0
    stl_data["v1"] = v1
    stl_data["v2"] = v2

    header = b"K9-Crystal-Pipeline STL export"
    header = header + b"\0" * (80 - len(header))

    with open(output_path, "wb") as f:
        f.write(header)
        f.write(np.uint32(n_faces).tobytes())
        stl_data.tofile(f)


def write_selected_formats(points, source_name, formats, project_root, stl_method="delaunay", stl_limit=None):
    """Write requested formats and return their output paths."""
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
        write_obj(points, obj_path, method=stl_method, stl_limit=stl_limit)
        output_paths["obj"] = obj_path

    if "stl" in formats:
        stl_path = project_root / "output" / "stl" / f"{source_name}.stl"
        write_stl(points, stl_path, method=stl_method, stl_limit=stl_limit)
        output_paths["stl"] = stl_path

    return output_paths
