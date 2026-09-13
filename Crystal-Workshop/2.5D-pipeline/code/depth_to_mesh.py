"""
File: converter/2.5D-pipeline/code/depth_to_mesh.py
Purpose:
 - Turn a 16-bit depth map plus its photograph into a relief mesh, written as
   both GLB (for the browser preview) and OBJ (for mesh_to_pointcloud.py).

No model, no cleverness - a height field on a regular grid, scaled into the
engravable box of a real crystal blank. Everything interesting already
happened in depth_map.py.

Two exports on purpose, and they are the same geometry. The GLB is what the
customer rotates; the OBJ is what becomes laser dots. If those two ever come
from different meshes, the preview stops being a promise about the product,
which is the one thing this whole pipeline is for.

Axes match what pipeline-converter expects: X = width, Y = height (up),
Z = depth toward the viewer, centred on the origin, millimetres. So the
handoff is literally:

    python code/depth_to_mesh.py ... --obj out/relief.obj
    python ../pipeline-converter/code/mesh_to_pointcloud.py \
        --file out/relief.obj --texture photo.jpg --upright y
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))

from utils import (  # noqa: E402
    DEFAULT_CRYSTAL_MARGIN,
    fail,
    prepare_output,
    report,
    usable_space,
)


def load_plane(path: Path, size: tuple[int, int], mode: str) -> np.ndarray:
    """Open an image, convert it, and resample it onto the working grid."""
    try:
        image = Image.open(path)
    except Exception as error:  # noqa: BLE001
        fail(f"Could not open {path}: {error}")
    image.load()
    return np.asarray(image.convert(mode).resize(size, Image.LANCZOS))


def grid_size(width_px: int, height_px: int, long_edge: int) -> tuple[int, int]:
    """
    Working grid, capped on the long edge and never below 2 in either axis.

    This is the vertex count, not a pixel count: 512 means roughly 512x400
    quads, which is ~400k vertices. That is plenty for a preview and plenty
    for the sampler to read, and it keeps the GLB small enough to send to a
    phone.
    """
    if long_edge <= 0:
        return max(2, width_px), max(2, height_px)
    scale = long_edge / max(width_px, height_px)
    return max(2, round(width_px * scale)), max(2, round(height_px * scale))


def fit_into(usable_width: float, usable_height: float, columns: int, rows: int) -> tuple[float, float]:
    """
    Millimetres the relief will actually occupy, preserving the photo's aspect.

    'Contain', never 'cover'. Cropping a customer's photograph to fill the
    glass is a decision they did not make; letterboxing inside the engravable
    area is the safe default and matches what the mask-based viewer on the
    website already does.
    """
    aspect = columns / rows
    if usable_width / usable_height > aspect:
        return usable_height * aspect, usable_height
    return usable_width, usable_width / aspect


def build_surface(
    depth: np.ndarray, mask: np.ndarray | None, alpha_threshold: float
) -> tuple[np.ndarray, np.ndarray]:
    """
    Two triangles per grid cell, skipping any cell whose corners are not all
    inside the subject.

    Dropping whole quads rather than clipping them leaves a slightly stepped
    silhouette at grid resolution. That is deliberate: a clipped edge produces
    long thin triangles, and the point sampler distributes dots by triangle
    area, so slivers become visible bright seams around the subject.
    """
    rows, columns = depth.shape
    row_index, column_index = np.meshgrid(np.arange(rows - 1), np.arange(columns - 1), indexing="ij")

    top_left = (row_index * columns + column_index).ravel()
    top_right = top_left + 1
    bottom_left = top_left + columns
    bottom_right = bottom_left + 1

    if mask is None:
        keep = np.ones(top_left.shape, dtype=bool)
    else:
        inside = (mask >= alpha_threshold).ravel()
        keep = inside[top_left] & inside[top_right] & inside[bottom_left] & inside[bottom_right]

    # Counter-clockwise seen from +Z, so the surface faces the viewer.
    lower = np.stack([top_left[keep], bottom_left[keep], bottom_right[keep]], axis=1)
    upper = np.stack([top_left[keep], bottom_right[keep], top_right[keep]], axis=1)
    return np.concatenate([lower, upper]), keep


def smoothstep(values: np.ndarray) -> np.ndarray:
    """Cubic easing with zero slope at both ends."""
    clipped = np.clip(values, 0.0, 1.0)
    return clipped * clipped * (3.0 - 2.0 * clipped)


def automatic_fillet_mm(width_mm: float, height_mm: float) -> float:
    """Scale the bend radius linearly with the physical image footprint.

    A 77.8 x 77.8 mm relief resolves to 0.01 mm. The clamp prevents tiny
    products from losing their fillet and very large blanks from washing away
    recognisable anatomy.
    """
    equivalent_square_edge = math.sqrt(max(width_mm * height_mm, 1e-6))
    return float(np.clip(equivalent_square_edge * (0.01 / 77.8), 0.01, 7.0))


def smooth_depth_flow(
    depth: np.ndarray,
    mask: np.ndarray | None,
    alpha_threshold: float,
    width_mm: float,
    height_mm: float,
    relief_mm: float,
    fillet_mm: float,
    boundary_fillet_mm: float,
    step_threshold_mm: float,
) -> tuple[np.ndarray, dict[str, float]]:
    """Merge abrupt depth layers into one physically smooth relief surface.

    The low-frequency geometry is eased over a distance measured in real
    millimetres. Every bend receives a small amount of regularization, while
    depth changes large enough to resemble a near-vertical wall receive the
    full fillet. Sub-millimetre surface detail is separated first and restored
    afterwards, preserving beard, hair, skin, and fabric texture.
    """
    if fillet_mm <= 0 and boundary_fillet_mm <= 0:
        return depth, {"changed_fraction": 0.0, "maximum_change_mm": 0.0}

    rows, columns = depth.shape
    subject = (
        np.ones(depth.shape, dtype=bool)
        if mask is None
        else mask >= alpha_threshold
    )
    if not subject.any():
        return depth, {"changed_fraction": 0.0, "maximum_change_mm": 0.0}

    millimetres_per_pixel_x = width_mm / max(columns - 1, 1)
    millimetres_per_pixel_y = height_mm / max(rows - 1, 1)
    back_plane = float(np.percentile(depth[subject], 2.0))
    working = np.where(subject, depth, back_plane).astype(np.float32)

    # Separate only very fine relief texture. It will be restored after the
    # common low-frequency surface has been regularized.
    micro_sigma_x = max(0.55, 0.18 / max(millimetres_per_pixel_x, 1e-6))
    micro_sigma_y = max(0.55, 0.18 / max(millimetres_per_pixel_y, 1e-6))
    low_geometry = cv2.GaussianBlur(
        working,
        (0, 0),
        sigmaX=micro_sigma_x,
        sigmaY=micro_sigma_y,
        borderType=cv2.BORDER_REPLICATE,
    )
    micro_detail = working - low_geometry

    if fillet_mm > 0:
        # A Gaussian sigma of fillet/2.35 places almost the whole transition
        # inside the requested physical width, giving an S-shaped turn rather
        # than a softened but still visibly square step.
        flow_sigma_x = max(0.01, fillet_mm / (2.35 * max(millimetres_per_pixel_x, 1e-6)))
        flow_sigma_y = max(0.01, fillet_mm / (2.35 * max(millimetres_per_pixel_y, 1e-6)))
        common_flow = cv2.GaussianBlur(
            low_geometry,
            (0, 0),
            sigmaX=flow_sigma_x,
            sigmaY=flow_sigma_y,
            borderType=cv2.BORDER_REPLICATE,
        )
        change_mm = np.abs(low_geometry - common_flow) * relief_mm
        sharpness = smoothstep(change_mm / max(step_threshold_mm, 1e-4))
        # All bends receive a light flow pass. Near-vertical transitions ramp
        # continuously to the full fillet strength.
        flow_strength = 0.18 + 0.82 * sharpness
        smoothed = low_geometry * (1.0 - flow_strength) + common_flow * flow_strength
        smoothed += micro_detail * (0.96 - 0.24 * flow_strength)
    else:
        smoothed = working.copy()

    if boundary_fillet_mm > 0:
        # Padding the alpha mask with zero makes the image frame an explicit
        # exterior boundary. A subject touching the crop therefore bends back
        # over the requested distance instead of ending in a vertical wall.
        padded = cv2.copyMakeBorder(
            subject.astype(np.uint8),
            1,
            1,
            1,
            1,
            cv2.BORDER_CONSTANT,
            value=0,
        )
        distance_pixels = cv2.distanceTransform(padded, cv2.DIST_L2, 5)[1:-1, 1:-1]
        average_mm_per_pixel = math.sqrt(
            millimetres_per_pixel_x * millimetres_per_pixel_y
        )
        boundary_weight = smoothstep(
            distance_pixels * average_mm_per_pixel / boundary_fillet_mm
        )
        smoothed = back_plane * (1.0 - boundary_weight) + smoothed * boundary_weight

    result = depth.copy()
    result[subject] = np.clip(smoothed[subject], 0.0, 1.0)
    difference_mm = np.abs(result - depth) * relief_mm
    return result, {
        "changed_fraction": float(np.mean(difference_mm[subject] > 0.05)),
        "maximum_change_mm": float(np.max(difference_mm[subject])),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a relief mesh from a depth map.")
    parser.add_argument("--depth", required=True, type=Path, help="16-bit depth PNG from depth_map.py.")
    parser.add_argument("--photo", type=Path, help="Photograph, for vertex colour and the alpha mask.")
    parser.add_argument(
        "--texture-image",
        type=Path,
        help="Optional visual texture separate from --photo; --photo still supplies the alpha mask.",
    )
    parser.add_argument(
        "--mask-image",
        type=Path,
        help=(
            "Optional explicit L/RGBA geometry mask. White/opaque pixels become mesh; "
            "this overrides --photo alpha and lets print-empty black border regions stay transparent."
        ),
    )
    parser.add_argument("--output", required=True, type=Path, help="GLB to write.")
    parser.add_argument("--obj", type=Path, help="Also write this OBJ, for mesh_to_pointcloud.py.")

    parser.add_argument("--template", default="60x80x40", help="Crystal blank, WIDTHxHEIGHTxDEPTH in mm.")
    parser.add_argument("--border", type=float, default=DEFAULT_CRYSTAL_MARGIN, help="Unengraved margin per side, mm.")
    parser.add_argument(
        "--relief-depth",
        type=float,
        default=0.0,
        help="Millimetres from the deepest point to the nearest. 0 uses the blank's whole usable depth.",
    )
    parser.add_argument("--grid", type=int, default=512, help="Vertices along the long edge. 0 keeps full resolution.")
    parser.add_argument(
        "--alpha-threshold",
        type=float,
        default=0.5,
        help="Cut-out alpha below this is background and gets no geometry.",
    )
    parser.add_argument(
        "--backing",
        type=float,
        default=0.0,
        help="Millimetres of flat backing behind the relief. 0 leaves an open surface.",
    )
    parser.add_argument(
        "--edge-fillet-mm",
        type=float,
        default=-1.0,
        help="Physical width used to merge every depth bend. Negative selects the crystal-size formula; 0 disables it.",
    )
    parser.add_argument(
        "--boundary-fillet-mm",
        type=float,
        default=-1.0,
        help="Physical roll-off at cut-out/image-frame boundaries. Negative uses the size formula; 0 disables it.",
    )
    parser.add_argument(
        "--depth-step-threshold-mm",
        type=float,
        default=0.65,
        help="Low-frequency deviation that receives the full fillet strength.",
    )
    parser.add_argument(
        "--flow-depth-output",
        type=Path,
        help="Optional 16-bit QA depth PNG after smooth-flow regularization.",
    )
    parser.add_argument(
        "--vertex-color",
        choices=["texture", "luma", "rgb", "none"],
        default="luma",
        help=(
            "Visual appearance for GLB/OBJ approval. texture embeds the full photo as a UV/base-color "
            "texture; luma/rgb store per-vertex colours; none writes geometry only."
        ),
    )
    args = parser.parse_args()

    try:
        import trimesh
    except ImportError:
        fail("trimesh is not installed. Run: pip install -r requirements.txt")

    space = usable_space(args.template, args.border)
    report(
        f"[mesh] blank {args.template} margin {space['border']:g}mm "
        f"-> usable {space['width']:g} x {space['height']:g} x {space['depth']:g} mm"
    )

    # ── Working grid ─────────────────────────────────────────────────────────
    with Image.open(args.depth) as probe:
        source_width, source_height = probe.size
    columns, rows = grid_size(source_width, source_height, args.grid)
    report(f"[mesh] grid {columns} x {rows} from a {source_width} x {source_height} depth map")

    # PNG 16-bit arrives as int32 through "I"; scale to 0..1 explicitly rather
    # than trusting a mode conversion to normalise it.
    depth = load_plane(args.depth, (columns, rows), "I").astype(np.float64) / 65535.0

    mask = None
    colours = None
    texture_image = None
    if args.mask_image:
        with Image.open(args.mask_image) as mask_source:
            mask_source.load()
            if mask_source.mode in ("RGBA", "LA") or "transparency" in mask_source.info:
                mask_plane = mask_source.convert("RGBA").getchannel("A")
            else:
                mask_plane = mask_source.convert("L")
            mask = np.asarray(
                mask_plane.resize((columns, rows), Image.Resampling.LANCZOS),
                dtype=np.float64,
            ) / 255.0
        report(
            f"[mesh] explicit mask subject covers "
            f"{(mask >= args.alpha_threshold).mean() * 100:.1f}% of the frame"
        )

    if args.photo:
        with Image.open(args.photo) as probe:
            has_alpha = probe.mode in ("RGBA", "LA") or "transparency" in probe.info
        if has_alpha and mask is None:
            mask = load_plane(args.photo, (columns, rows), "RGBA")[:, :, 3].astype(np.float64) / 255.0
            report(f"[mesh] subject covers {(mask >= args.alpha_threshold).mean() * 100:.1f}% of the frame")
        elif not has_alpha and mask is None:
            report("[mesh] photo has no alpha channel - the whole rectangle gets geometry.")

        if args.vertex_color == "luma":
            luma = load_plane(args.photo, (columns, rows), "L").astype(np.uint8)
            colours = np.repeat(luma.reshape(-1, 1), 3, axis=1)
        elif args.vertex_color == "rgb":
            colours = load_plane(args.photo, (columns, rows), "RGB").reshape(-1, 3).astype(np.uint8)
        elif args.vertex_color == "texture":
            texture_path = args.texture_image or args.photo
            with Image.open(texture_path) as source_texture:
                source_texture.load()
                texture_image = source_texture.convert("RGB").copy()

    # ── Vertices ─────────────────────────────────────────────────────────────
    width_mm, height_mm = fit_into(space["width"], space["height"], columns, rows)
    relief_mm = args.relief_depth if args.relief_depth > 0 else space["depth"]
    if relief_mm > space["depth"]:
        fail(
            f"--relief-depth {relief_mm:g}mm does not fit the {space['depth']:g}mm usable depth of {args.template}."
        )
    report(f"[mesh] relief {width_mm:.2f} x {height_mm:.2f} x {relief_mm:.2f} mm")

    # ── Physical smooth-flow regularization ─────────────────────────────────
    formula_fillet_mm = automatic_fillet_mm(width_mm, height_mm)
    resolved_edge_fillet_mm = (
        formula_fillet_mm if args.edge_fillet_mm < 0 else args.edge_fillet_mm
    )
    resolved_boundary_fillet_mm = (
        formula_fillet_mm
        if args.boundary_fillet_mm < 0
        else args.boundary_fillet_mm
    )
    depth, flow_report = smooth_depth_flow(
        depth,
        mask,
        args.alpha_threshold,
        width_mm,
        height_mm,
        relief_mm,
        max(0.0, resolved_edge_fillet_mm),
        max(0.0, resolved_boundary_fillet_mm),
        max(0.01, args.depth_step_threshold_mm),
    )
    report(
        f"[mesh] smooth flow formula={formula_fillet_mm:.2f}mm "
        f"edge={resolved_edge_fillet_mm:.2f}mm "
        f"boundary={resolved_boundary_fillet_mm:.2f}mm "
        f"changed={flow_report['changed_fraction'] * 100:.1f}% "
        f"max={flow_report['maximum_change_mm']:.2f}mm"
    )
    if args.flow_depth_output:
        prepare_output(args.flow_depth_output)
        Image.fromarray(
            np.round(np.clip(depth, 0.0, 1.0) * 65535.0).astype(np.uint16),
            mode="I;16",
        ).save(args.flow_depth_output)
        report(f"[mesh] wrote smooth-flow QA depth {args.flow_depth_output}")

    # Image row 0 is the top of the picture; +Y is up in the crystal.
    x = np.linspace(-width_mm / 2, width_mm / 2, columns)
    y = np.linspace(height_mm / 2, -height_mm / 2, rows)
    grid_x, grid_y = np.meshgrid(x, y)
    grid_z = (depth - 0.5) * relief_mm

    vertices = np.stack([grid_x.ravel(), grid_y.ravel(), grid_z.ravel()], axis=1)
    grid_u, grid_v = np.meshgrid(
        np.linspace(0.0, 1.0, columns),
        np.linspace(1.0, 0.0, rows),
    )
    texture_uv = np.stack([grid_u.ravel(), grid_v.ravel()], axis=1)
    faces, kept = build_surface(depth, mask, args.alpha_threshold)
    if not len(faces):
        fail("Every cell was masked out - check --alpha-threshold, or the cut-out itself.")
    report(f"[mesh] {kept.sum()} of {kept.size} cells kept")

    # ── Optional backing ─────────────────────────────────────────────────────
    # A relief with a flat back reads as a solid object in the preview and can
    # go to a 3D printer. The engraver does not need it - the point sampler
    # would happily fill it with dots nobody asked for - so it is off by
    # default and simply omitted from the OBJ handed downstream.
    backing_faces = None
    if args.backing > 0:
        offset = len(vertices)
        back = vertices.copy()
        back[:, 2] = grid_z.min() - args.backing
        mirrored = faces[:, ::-1] + offset  # reversed winding, so it faces away
        vertices = np.concatenate([vertices, back])
        if colours is not None:
            colours = np.concatenate([colours, colours])
        if texture_image is not None:
            texture_uv = np.concatenate([texture_uv, texture_uv])
        backing_faces = mirrored
        report(f"[mesh] backing plane {args.backing:g}mm behind the deepest point")

    all_faces = faces if backing_faces is None else np.concatenate([faces, backing_faces])

    visual = None
    if texture_image is not None:
        visual = trimesh.visual.texture.TextureVisuals(uv=texture_uv, image=texture_image)
    mesh = trimesh.Trimesh(
        vertices=vertices,
        faces=all_faces,
        vertex_colors=colours if colours is not None else None,
        visual=visual,
        process=False,
    )
    mesh.remove_unreferenced_vertices()
    report(f"[mesh] {len(mesh.vertices)} vertices, {len(mesh.faces)} triangles")

    prepare_output(args.output)
    mesh.export(args.output)
    report(f"[mesh] wrote {args.output}")

    if args.obj:
        # The OBJ deliberately carries only the relief surface, never the
        # backing, because this file's next stop is the point sampler.
        surface_visual = None
        if texture_image is not None:
            surface_visual = trimesh.visual.texture.TextureVisuals(
                uv=texture_uv[: columns * rows],
                image=texture_image,
            )
        surface = trimesh.Trimesh(
            vertices=vertices[: columns * rows],
            faces=faces,
            visual=surface_visual,
            process=False,
        )
        surface.remove_unreferenced_vertices()
        prepare_output(args.obj)
        surface.export(args.obj)
        report(f"[mesh] wrote {args.obj} ({len(surface.faces)} triangles, relief surface only)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
