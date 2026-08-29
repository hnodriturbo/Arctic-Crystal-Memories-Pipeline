"""
File: code/mesh_to_pointcloud.py
Purpose:
 - Convert a surface mesh (OBJ, or DXF made of 3DFACE entities) into the
   POINT-cloud DXF that the SSLE laser engraver actually reads.

Why this exists: Cockpit3D exports POINT clouds, but Meshy/Blender exports
triangle surfaces. purify_dxf.py only understands POINT entities, so a mesh
DXF run through it comes out empty. This module is the missing stage - it
samples the mesh surface into evenly spaced dots and fits them to a crystal
template, the same job Cockpit3D's PointCloudBuilder does internally.

The one thing that separates a photograph from a wireframe in glass is dot
DENSITY following image brightness, not geometry alone. That is what
--texture does, and it is the closest thing here to Cockpit3D's Toning.
"""

import argparse
import math
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
    fit_points_to_template,
    resolve_template,
    thin_to_grid,
    write_printer_dxf,
)

console = Console()


def load_obj_mesh(source_path):
    """Read vertices, triangles and any UVs from a Wavefront OBJ, fan-triangulating n-gons."""
    vertices = []
    texture_coords = []
    faces = []
    face_uvs = []

    with open(source_path, "r", encoding="utf-8", errors="replace") as source_file:
        for line in source_file:
            if line.startswith("v "):
                parts = line.split()
                vertices.append((float(parts[1]), float(parts[2]), float(parts[3])))
            elif line.startswith("vt "):
                parts = line.split()
                texture_coords.append((float(parts[1]), float(parts[2])))
            elif line.startswith("f "):
                # Face tokens look like "v", "v/vt", "v//vn" or "v/vt/vn".
                corners = []
                uv_corners = []
                for token in line.split()[1:]:
                    pieces = token.split("/")
                    index = int(pieces[0])
                    corners.append(index - 1 if index > 0 else len(vertices) + index)
                    if len(pieces) > 1 and pieces[1]:
                        uv_index = int(pieces[1])
                        uv_corners.append(
                            uv_index - 1 if uv_index > 0 else len(texture_coords) + uv_index
                        )
                    else:
                        uv_corners.append(-1)
                for corner in range(1, len(corners) - 1):
                    faces.append((corners[0], corners[corner], corners[corner + 1]))
                    face_uvs.append((uv_corners[0], uv_corners[corner], uv_corners[corner + 1]))

    vertex_array = np.asarray(vertices, dtype=np.float64)
    face_array = np.asarray(faces, dtype=np.int64)
    uv_array = np.asarray(texture_coords, dtype=np.float64) if texture_coords else None
    face_uv_array = np.asarray(face_uvs, dtype=np.int64) if texture_coords else None
    if face_uv_array is not None and (face_uv_array < 0).any():
        face_uv_array = None

    return vertex_array, face_array, uv_array, face_uv_array


def load_dxf_mesh(source_path):
    """Read 3DFACE corners from a DXF, streaming so a 349 MB export is walked once."""
    triangles = []
    corner_x, corner_y, corner_z = {}, {}, {}
    inside_face = False

    def flush_face():
        """Emit the pending 3DFACE as one or two triangles, dropping the padded 4th corner."""
        corners = [
            (corner_x[slot], corner_y[slot], corner_z[slot])
            for slot in range(4)
            if slot in corner_x and slot in corner_y and slot in corner_z
        ]
        if len(corners) < 3:
            return
        triangles.append((corners[0], corners[1], corners[2]))
        # A real quad repeats no corner; DXF pads triangles by duplicating corner 3.
        if len(corners) == 4 and corners[3] != corners[2]:
            triangles.append((corners[0], corners[2], corners[3]))

    with open(source_path, "r", encoding="utf-8", errors="replace") as source_file:
        iterator = iter(source_file)
        for raw_code in iterator:
            code = raw_code.strip()
            try:
                value = next(iterator).strip()
            except StopIteration:
                break

            if code == "0":
                if inside_face:
                    flush_face()
                corner_x.clear()
                corner_y.clear()
                corner_z.clear()
                inside_face = value == "3DFACE"
                if value == "EOF":
                    break
            elif inside_face and len(code) == 2 and code[0] in "123" and code[1] in "0123":
                axis, slot = code[0], int(code[1])
                target = {"1": corner_x, "2": corner_y, "3": corner_z}[axis]
                target[slot] = float(value)

    if inside_face:
        flush_face()

    array = np.asarray(triangles, dtype=np.float64)
    if array.size == 0:
        return np.zeros((0, 3)), np.zeros((0, 3), dtype=np.int64), None, None

    # Triangles arrive as raw corner triples; split into a vertex list plus an index list.
    vertices = array.reshape(-1, 3)
    faces = np.arange(len(vertices), dtype=np.int64).reshape(-1, 3)
    return vertices, faces, None, None


def load_brightness_map(texture_path):
    """Load a texture as a greyscale array in 0..1, used to drive dot density."""
    from PIL import Image  # noqa: PLC0415

    with Image.open(texture_path) as image:
        grey = image.convert("L")
        return np.asarray(grey, dtype=np.float32) / 255.0


def sample_brightness_uv(brightness, uv_values):
    """Look brightness up by UV coordinate, with V flipped to image row order."""
    height, width = brightness.shape
    columns = np.clip((uv_values[:, 0] % 1.0) * (width - 1), 0, width - 1).astype(np.int32)
    rows = np.clip((1.0 - (uv_values[:, 1] % 1.0)) * (height - 1), 0, height - 1).astype(np.int32)
    return brightness[rows, columns]


def sample_brightness_projected(brightness, points):
    """Look brightness up by projecting the image flat onto the model's XY footprint.

    The fallback for meshes with no UVs - Meshy exports often have none - and the
    right model for a relief anyway, where the picture faces the viewer.
    """
    height, width = brightness.shape
    lower = points.min(axis=0)
    upper = points.max(axis=0)
    span = np.maximum(upper - lower, 1e-9)

    normalised_x = (points[:, 0] - lower[0]) / span[0]
    normalised_y = (points[:, 1] - lower[1]) / span[1]
    columns = np.clip(normalised_x * (width - 1), 0, width - 1).astype(np.int32)
    rows = np.clip((1.0 - normalised_y) * (height - 1), 0, height - 1).astype(np.int32)
    return brightness[rows, columns]


def sample_surface(vertices, faces, spacing, target_points=None, seed=7,
                   uv_coords=None, uv_faces=None, oversample=1.35):
    """Scatter points across the mesh surface, area-weighted so density stays even everywhere.

    Returns the samples plus their interpolated UVs, so a caller can look up
    texture brightness per dot afterwards.
    """
    corner_a = vertices[faces[:, 0]]
    corner_b = vertices[faces[:, 1]]
    corner_c = vertices[faces[:, 2]]

    areas = 0.5 * np.linalg.norm(np.cross(corner_b - corner_a, corner_c - corner_a), axis=1)
    total_area = float(areas.sum())

    # A point budget is easier to reason about than spacing, so let it win when given.
    if target_points:
        spacing = math.sqrt(total_area / max(target_points, 1))

    # Oversample, because grid thinning and texture rejection both discard a share.
    density = 1.0 / (spacing * spacing)
    expected = areas * density * oversample
    counts = np.floor(expected).astype(np.int64)
    remainder = expected - counts
    rng = np.random.default_rng(seed)
    counts += (rng.random(len(counts)) < remainder).astype(np.int64)

    keep = counts > 0
    if not keep.any():
        return np.zeros((0, 3)), None, spacing, total_area

    face_index = np.repeat(np.nonzero(keep)[0], counts[keep])
    sample_total = len(face_index)

    # Uniform barycentric coordinates over each triangle.
    root_u = np.sqrt(rng.random(sample_total))
    weight_v = rng.random(sample_total)
    weight_a = (1.0 - root_u)[:, None]
    weight_b = (root_u * (1.0 - weight_v))[:, None]
    weight_c = (root_u * weight_v)[:, None]

    points = (
        weight_a * corner_a[face_index]
        + weight_b * corner_b[face_index]
        + weight_c * corner_c[face_index]
    )

    sampled_uvs = None
    if uv_coords is not None and uv_faces is not None:
        sampled_uvs = (
            weight_a * uv_coords[uv_faces[face_index, 0]]
            + weight_b * uv_coords[uv_faces[face_index, 1]]
            + weight_c * uv_coords[uv_faces[face_index, 2]]
        )

    return points, sampled_uvs, spacing, total_area


def apply_texture_density(points, weights, rng, floor):
    """Thin the cloud so surviving dot density follows image brightness.

    Rejection sampling rather than a weighted grid, because the point is to make
    dark regions genuinely sparse - that tonal range is what makes engraved glass
    read as a photograph instead of a wireframe.
    """
    keep_probability = np.clip(floor + (1.0 - floor) * weights, 0.0, 1.0)
    survivors = rng.random(len(points)) < keep_probability
    return points[survivors], keep_probability[survivors]


def write_xyz(points, output_path):
    """Write a plain XYZ copy so the result can be eyeballed in CloudCompare or MeshLab."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savetxt(output_path, points, fmt="%.4f", delimiter=" ")


def convert(source_path, output_dir, template, args):
    """Run the whole mesh to printable point-cloud pipeline for one source file."""
    console.print(f"[bold cyan]Source:[/bold cyan] {source_path.name}")

    console.print("  Loading mesh...")
    suffix = source_path.suffix.lower()
    if suffix == ".obj":
        vertices, faces, uv_coords, uv_faces = load_obj_mesh(source_path)
    elif suffix == ".dxf":
        vertices, faces, uv_coords, uv_faces = load_dxf_mesh(source_path)
    else:
        console.print(f"[red]Unsupported input type: {source_path.suffix}[/red]")
        return None

    if len(faces) == 0:
        console.print(
            "[red]No triangles found. A POINT-only DXF belongs in "
            "rebuild_pointcloud.py, not here.[/red]"
        )
        return None

    console.print(
        f"  [green]{len(vertices):,}[/green] vertices  "
        f"[green]{len(faces):,}[/green] triangles"
        + ("  [green]with UVs[/green]" if uv_coords is not None else "  no UVs")
    )

    fitted, scale, mapping, binding = fit_points_to_template(
        vertices, template, args.swap_yz, args.flip,
        args.auto_orient, args.upright, args.depth_axis,
    )
    console.print(
        f"  Fitted to {template['width']:g} x {template['height']:g} x {template['depth']:g} mm "
        f"(border {template['border']:g} mm, scale x{scale:.4g}, limited by {binding})"
    )
    if args.auto_orient or args.upright or args.depth_axis:
        console.print(f"  Oriented source axes {''.join('XYZ'[a] for a in mapping)} to XYZ")

    # Texture rejection throws away roughly half, so ask for more up front.
    oversample = 1.35 * (2.2 if args.texture else 1.0)

    console.print("  Sampling surface...")
    sampled, sampled_uvs, spacing, area = sample_surface(
        fitted, faces, args.spacing, args.points,
        uv_coords=uv_coords, uv_faces=uv_faces, oversample=oversample,
    )
    console.print(
        f"  Surface area {area:,.1f} mm2  spacing {spacing:.4f} mm  "
        f"{len(sampled):,} raw samples"
    )

    if args.texture:
        texture_path = Path(args.texture)
        if not texture_path.exists():
            console.print(f"[red]Texture not found: {texture_path}[/red]")
            return None

        brightness_map = load_brightness_map(texture_path)
        mode = args.texture_mode
        if mode == "uv" and sampled_uvs is None:
            console.print("  [yellow]No UVs on this mesh - projecting the image instead[/yellow]")
            mode = "project"

        raw = (
            sample_brightness_uv(brightness_map, sampled_uvs)
            if mode == "uv"
            else sample_brightness_projected(brightness_map, sampled)
        )
        if args.invert_texture:
            raw = 1.0 - raw

        # Toning is a gamma curve: >1 darkens midtones and widens the tonal range.
        toned = np.power(np.clip(raw, 0.0, 1.0), args.toning)
        rng = np.random.default_rng(args.seed + 1)
        sampled, _ = apply_texture_density(sampled, toned, rng, args.density_floor)
        console.print(
            f"  Texture ({mode}, toning {args.toning:g}, floor {args.density_floor:g}) "
            f"-> [green]{len(sampled):,}[/green] samples kept"
        )

    console.print("  Thinning to laser grid...")
    grid_step = max(spacing, args.min_distance)
    z_step = args.z_distance if args.z_distance else grid_step
    points, _ = thin_to_grid(sampled, grid_step, z_step)

    if args.layers or args.layer_spacing:
        points = apply_depth_layers(
            points, args.layers, args.layer_spacing, args.stagger, grid_step
        )
        layer_note = (
            f"{args.layer_spacing:g} mm apart" if args.layer_spacing else f"{args.layers} layers"
        )
        console.print(f"  Depth layering: {layer_note}, stagger {args.stagger}")

    # Cockpit3D avoids needlessly dense clouds. Spacing remains the primary
    # geometric control, while this deterministic final cap prevents a deep or
    # highly detailed mesh from unexpectedly growing into millions of dots.
    if args.max_points and len(points) > args.max_points:
        before = len(points)
        rng = np.random.default_rng(args.seed + 2)
        keep = np.sort(rng.choice(before, size=args.max_points, replace=False))
        points = points[keep]
        console.print(
            f"  Point cap: [yellow]{before:,}[/yellow] -> "
            f"[green]{len(points):,}[/green] (seed {args.seed})"
        )

    console.print(f"  [green]{len(points):,}[/green] final points")
    if len(points) == 0:
        console.print("[red]Nothing survived. Loosen the texture floor or raise the budget.[/red]")
        return None

    lower = points.min(axis=0)
    upper = points.max(axis=0)
    console.print(
        f"  X [{lower[0]:.2f}, {upper[0]:.2f}]  "
        f"Y [{lower[1]:.2f}, {upper[1]:.2f}]  "
        f"Z [{lower[2]:.2f}, {upper[2]:.2f}]"
    )

    stem = (
        f"{source_path.stem}-{template['width']:g}mm-{template['height']:g}mm-"
        f"{template['depth']:g}mm-{len(points)}points"
    )
    dxf_path = output_dir / f"{stem}.dxf"
    write_printer_dxf(points, dxf_path)
    console.print(
        f"  [green]Wrote[/green] {dxf_path.name} "
        f"({dxf_path.stat().st_size / 1_048_576:.1f} MB)"
    )

    if args.xyz:
        xyz_path = output_dir / f"{stem}.xyz"
        write_xyz(points, xyz_path)
        console.print(f"  [green]Wrote[/green] {xyz_path.name}")

    return dxf_path


def build_parser():
    """CLI surface; the web UI mirrors these flags from its own catalogue."""
    parser = argparse.ArgumentParser(
        description="Mesh (OBJ / 3DFACE DXF) to printable POINT-cloud DXF for the SSLE engraver."
    )
    parser.add_argument("--file", nargs="+", required=True, help="OBJ or DXF mesh files.")
    parser.add_argument(
        "--template", default="60x80x40", choices=sorted(CRYSTAL_TEMPLATES),
        help="Crystal blank to fit into."
    )
    parser.add_argument("--width", type=float, help="Override template width in mm.")
    parser.add_argument("--height", type=float, help="Override template height in mm.")
    parser.add_argument("--depth", type=float, help="Override template depth in mm.")
    parser.add_argument(
        "--border", type=float,
        help="Unengraved margin per side in mm (default 1; minimum 0.1)."
    )

    parser.add_argument(
        "--points", type=int, default=0,
        help="Target point budget; set 0 to drive density from --spacing instead."
    )
    parser.add_argument(
        "--spacing", type=float, default=DEFAULT_POINT_DISTANCE,
        help="Point spacing in mm, used when --points is 0."
    )
    parser.add_argument(
        "--min-distance", type=float, default=DEFAULT_POINT_DISTANCE,
        help="Hard floor on dot spacing so the laser never over-burns."
    )
    parser.add_argument(
        "--z-distance", type=float, default=0.0,
        help="Separate spacing along depth; 0 reuses the XY spacing."
    )
    parser.add_argument(
        "--max-points", type=int, default=500000,
        help="Final deterministic point cap after thinning/layers; 0 disables it."
    )

    parser.add_argument(
        "--layers", type=int, default=0,
        help="Snap depth onto this many engraving planes; 0 leaves depth continuous."
    )
    parser.add_argument(
        "--layer-spacing", type=float, default=0.08,
        help="Millimetres between engraving planes; overrides --layers when set."
    )
    parser.add_argument(
        "--stagger", type=int, default=1,
        help="Offset alternate layers sideways so dots do not stack into columns."
    )

    parser.add_argument(
        "--texture", default=None,
        help="Image whose brightness drives dot density - the photograph effect."
    )
    parser.add_argument(
        "--texture-mode", default="uv", choices=["uv", "project"],
        help="Look brightness up through mesh UVs, or project the image onto the XY footprint."
    )
    parser.add_argument(
        "--toning", type=float, default=1.8,
        help="Gamma on brightness. Cockpit3D's own default is 1.8; higher deepens shadows."
    )
    parser.add_argument(
        "--density-floor", type=float, default=0.05,
        help="Minimum keep probability, so the darkest areas are sparse rather than empty."
    )
    parser.add_argument(
        "--invert-texture", action="store_true",
        help="Treat dark as dense instead of light."
    )

    parser.add_argument("--swap-yz", action="store_true",
                        help="Swap Y and Z for Z-up sources such as CAD exports.")
    parser.add_argument("--flip", default="", help="Axes to mirror, e.g. 'x' or 'xz'.")
    parser.add_argument(
        "--auto-orient", action="store_true",
        help="Rotate the mesh onto the axis mapping that fills the blank best."
    )
    parser.add_argument(
        "--upright", nargs="?", const="auto", default=None, choices=["auto", "x", "y", "z"],
        help="Keep the subject standing: pins a source axis to crystal height."
    )
    parser.add_argument(
        "--depth-axis", default=None, choices=["x", "y", "z"],
        help="Which source axis runs into the crystal's depth, i.e. which face faces the viewer."
    )

    parser.add_argument("--seed", type=int, default=7, help="Sampling seed, for repeatable runs.")
    parser.add_argument("--xyz", action="store_true", help="Also write an XYZ preview file.")
    parser.add_argument("--out", default=None, help="Output directory.")
    return parser


def main():
    args = build_parser().parse_args()
    template = resolve_template(args.template, args.width, args.height, args.depth, args.border)

    output_dir = Path(args.out) if args.out else PROJECT_ROOT / "output" / "printable_dxf"
    output_dir.mkdir(parents=True, exist_ok=True)

    console.print("[bold]Mesh to Point Cloud - SSLE printable DXF[/bold]")
    console.print(f"Output: {output_dir}\n")

    for file_argument in args.file:
        source = Path(file_argument).resolve()
        if not source.exists():
            console.print(f"[red]File not found: {source}[/red]")
            sys.exit(1)
        convert(source, output_dir, template, args)
        console.print("")


if __name__ == "__main__":
    main()
