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


def reconstruct_mesh(points, method="delaunay", stl_limit=None):
    """Build one bounded surface shared by STL and GLB exports."""
    from scipy.spatial import Delaunay, ConvexHull

    pts = np.asarray(points, dtype=np.float32)
    if pts.ndim != 2 or pts.shape[1] != 3 or len(pts) < 3 or not np.isfinite(pts).all():
        raise ValueError("A surface needs at least three finite XYZ points.")
    if stl_limit is not None:
        if stl_limit < 3:
            raise ValueError("Mesh limit must be at least 3.")
        if len(pts) > stl_limit:
            pts = pts[np.linspace(0, len(pts) - 1, stl_limit, dtype=int)]
    if method == "convex":
        faces = ConvexHull(pts).simplices
    else:
        # The established reconstruction is a single XY relief, with Z depth.
        faces = Delaunay(pts[:, :2]).simplices
    return pts, faces.astype(np.int32)


def write_glb(mesh, output_path, texture_from=None, texture_plane="auto", flip_u=False, flip_v=False, color_mode="vertex"):
    """Export actual triangles; optional photo colors never read CI geometry."""
    import trimesh
    from .photo_projection import vertex_colors, photo_uv

    vertices, faces = mesh
    colors = vertex_colors(vertices, texture_from, texture_plane, flip_u, flip_v) if texture_from and color_mode == "vertex" else None
    model = trimesh.Trimesh(vertices=vertices, faces=faces, vertex_colors=colors, process=False)
    if texture_from and color_mode == "texture":
        photo, uv = photo_uv(vertices, texture_from, texture_plane, flip_u, flip_v)
        # A full photo texture preserves detail independently of surface resolution.
        material = trimesh.visual.material.PBRMaterial(baseColorTexture=photo,
            metallicFactor=0.0, roughnessFactor=1.0, doubleSided=True)
        model.visual = trimesh.visual.TextureVisuals(uv=uv, material=material)
    elif colors is None:
        model.visual.vertex_colors = [220, 226, 232, 255]
    # GLTF uses metres; source exports and STL remain in millimetres.
    model.apply_scale(0.001)
    ensure_parent_directory(output_path)
    model.export(str(output_path), file_type="glb", include_normals=True)


def write_stl(points, output_path, method="delaunay", stl_limit=None, mesh=None):
    """Write a binary STL mesh from a point cloud using Delaunay or ConvexHull triangulation."""
    from scipy.spatial import Delaunay, ConvexHull  # noqa: PLC0415

    ensure_parent_directory(output_path)
    pts, simplices = mesh if mesh is not None else reconstruct_mesh(points, method, stl_limit)

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


def write_selected_formats(points, source_name, formats, project_root, stl_method="delaunay", stl_limit=None,
                           texture_from=None, texture_plane="auto", flip_u=False, flip_v=False):
    """Write requested formats and return their output paths."""
    output_paths = {}
    mesh = reconstruct_mesh(points, stl_method, stl_limit) if {"stl", "glb"}.intersection(formats) else None

    if "glb" in formats:
        glb_path = project_root / "output" / "cockpit-reconstruct" / f"{source_name}.glb"
        write_glb(mesh, glb_path, texture_from, texture_plane, flip_u, flip_v)
        output_paths["glb"] = glb_path

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
        write_stl(points, stl_path, mesh=mesh)
        output_paths["stl"] = stl_path

    return output_paths
