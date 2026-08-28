"""
File: code/utils/printer_dxf.py
Purpose:
 - Shared building blocks for producing the POINT-cloud DXF the SSLE
   engraver reads: the exact Cockpit3D byte format, crystal blanks,
   laser-grid thinning, and depth layering.

Kept separate because two entry points need it - mesh_to_pointcloud.py
(mesh in) and rebuild_pointcloud.py (existing cloud in). Any change to the
printer's expected format belongs here and nowhere else.
"""

import itertools

import numpy as np

# ACM's current Cockpit3D production reference. Treat this as a safe starting
# point rather than a universal hardware limit; smaller gaps need a real glass
# test on the target laser.
DEFAULT_POINT_DISTANCE = 0.08

# Crystal blanks. Keys are WIDTHxHEIGHTxDEPTH in millimetres.
#
# NOTE ON ORDER. The acm.is product catalogue labels its sizes
# HEIGHT x WIDTH x DEPTH - "rectangle-crystal-large-landscape" is listed as
# "60 x 90 x 60 mm" and described as wide-format, so 90 is its width. These
# keys therefore have the first two numbers swapped relative to the shop
# listing. Getting that backwards stands a landscape blank on its end, which
# is exactly the failure this file's orientation options exist to prevent.
#
# The first five entries predate the catalogue import and keep their original
# borders so nothing already in production shifts. Everything added since uses
# a 5 mm border, which is the common case; override it per job with --border.
CRYSTAL_TEMPLATES = {
    # ── Original set, unchanged ──────────────────────────────────────────────
    "60x80x30": {"width": 60.0, "height": 80.0, "depth": 30.0, "border": 5.0},
    "60x80x40": {"width": 60.0, "height": 80.0, "depth": 40.0, "border": 5.0},
    "80x50x50": {"width": 80.0, "height": 50.0, "depth": 50.0, "border": 3.0},
    "120x80x40": {"width": 120.0, "height": 80.0, "depth": 40.0, "border": 3.0},
    "90x60x60": {"width": 90.0, "height": 60.0, "depth": 60.0, "border": 5.0},

    # ── Rectangle, portrait (taller than wide) ───────────────────────────────
    "40x60x40": {"width": 40.0, "height": 60.0, "depth": 40.0, "border": 5.0},
    "50x80x50": {"width": 50.0, "height": 80.0, "depth": 50.0, "border": 5.0},
    "60x90x60": {"width": 60.0, "height": 90.0, "depth": 60.0, "border": 5.0},
    "80x120x60": {"width": 80.0, "height": 120.0, "depth": 60.0, "border": 5.0},
    "100x150x80": {"width": 100.0, "height": 150.0, "depth": 80.0, "border": 5.0},
    "120x180x80": {"width": 120.0, "height": 180.0, "depth": 80.0, "border": 5.0},

    # ── Rectangle, landscape (wider than tall) ───────────────────────────────
    "60x40x40": {"width": 60.0, "height": 40.0, "depth": 40.0, "border": 5.0},
    "120x80x60": {"width": 120.0, "height": 80.0, "depth": 60.0, "border": 5.0},
    "150x100x80": {"width": 150.0, "height": 100.0, "depth": 80.0, "border": 5.0},
    "180x120x80": {"width": 180.0, "height": 120.0, "depth": 80.0, "border": 5.0},

    # ── Prestige ─────────────────────────────────────────────────────────────
    "100x130x50": {"width": 100.0, "height": 130.0, "depth": 50.0, "border": 5.0},
    "140x170x60": {"width": 140.0, "height": 170.0, "depth": 60.0, "border": 5.0},
    "160x200x60": {"width": 160.0, "height": 200.0, "depth": 60.0, "border": 5.0},

    # ── Notched. Treated as its plain bounding box; the notch is at the base
    #    and outside the engravable area anyway. ──────────────────────────────
    "100x150x30": {"width": 100.0, "height": 150.0, "depth": 30.0, "border": 5.0},
    "130x180x30": {"width": 130.0, "height": 180.0, "depth": 30.0, "border": 5.0},
    "150x100x30": {"width": 150.0, "height": 100.0, "depth": 30.0, "border": 5.0},
    "180x130x30": {"width": 180.0, "height": 130.0, "depth": 30.0, "border": 5.0},

    # ── Cubes ────────────────────────────────────────────────────────────────
    "40x40x40": {"width": 40.0, "height": 40.0, "depth": 40.0, "border": 5.0},
    "50x50x50": {"width": 50.0, "height": 50.0, "depth": 50.0, "border": 5.0},
    "60x60x60": {"width": 60.0, "height": 60.0, "depth": 60.0, "border": 5.0},
    "80x80x80": {"width": 80.0, "height": 80.0, "depth": 80.0, "border": 5.0},
    "100x100x100": {"width": 100.0, "height": 100.0, "depth": 100.0, "border": 5.0},

    # ── Keychains ────────────────────────────────────────────────────────────
    "20x30x15": {"width": 20.0, "height": 30.0, "depth": 15.0, "border": 2.0},
    "35x35x12": {"width": 35.0, "height": 35.0, "depth": 12.0, "border": 2.0},
}

# Circle and heart blanks are deliberately absent. This fitter scales a model
# into a rectangular box, so a curved blank would take a cloud that overflows
# its edges. They need a mask, not a bounding box.


def format_coordinate(value):
    """Match Cockpit3D's number style exactly: 2 decimals, trailing zeros trimmed, never bare."""
    text = f"{round(float(value), 2):.2f}".rstrip("0")
    return text + "0" if text.endswith(".") else text


def write_printer_dxf(points, output_path):
    """Write the minimal POINT DXF flavour Cockpit3D emits and the SSLE printer accepts.

    The odd `0 / $EXTMAX` pair instead of `9 / $EXTMAX` is reproduced deliberately -
    it is what Cockpit3D writes, and the printer is known to accept it.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8", newline="\n") as output_file:
        output_file.write(
            "0\nSECTION\n2\nHEADER\n"
            "9\n$EXTMIN\n10\n0.0\n20\n0.0\n30\n0.0\n"
            "0\n$EXTMAX\n10\n0.0\n20\n0.0\n30\n0.0\n"
            "0\nENDSEC\n0\nSECTION\n2\nENTITIES\n"
        )
        write = output_file.write
        for handle, (x_value, y_value, z_value) in enumerate(points, start=1):
            write(
                f"0\nPOINT\n8\nVWX\n5\n{handle}\n"
                f"10\n{format_coordinate(x_value)}\n"
                f"20\n{format_coordinate(y_value)}\n"
                f"30\n{format_coordinate(z_value)}\n"
            )
        write("0\nENDSEC\n0\nEOF")


def detect_dxf_kind(source_path):
    """Report whether a DXF holds POINT entities, a 3DFACE mesh, or neither."""
    points = faces = 0
    with open(source_path, "r", encoding="utf-8", errors="replace") as source_file:
        iterator = iter(source_file)
        for raw_code in iterator:
            try:
                value = next(iterator).strip()
            except StopIteration:
                break
            if raw_code.strip() != "0":
                continue
            if value == "POINT":
                points += 1
            elif value in ("3DFACE", "POLYFACE", "MESH"):
                faces += 1
            # A few hundred entities is plenty to tell the two apart.
            if points + faces >= 500:
                break
    if points and points >= faces:
        return "points"
    if faces:
        return "mesh"
    return "unknown"


def read_point_dxf(source_path):
    """Stream POINT coordinates out of a DXF, ignoring header extents and everything else."""
    xs, ys, zs = [], [], []
    in_entities = False
    in_point = False
    pending_x = pending_y = None

    with open(source_path, "r", encoding="utf-8", errors="replace") as source_file:
        iterator = iter(source_file)
        for raw_code in iterator:
            code = raw_code.strip()
            try:
                value = next(iterator).strip()
            except StopIteration:
                break

            if code == "2" and value == "ENTITIES":
                in_entities = True
                continue
            if not in_entities:
                continue
            if code == "0":
                in_point = value == "POINT"
                pending_x = pending_y = None
                if value == "EOF":
                    break
                continue
            if not in_point:
                continue
            if code == "10":
                pending_x = float(value)
            elif code == "20":
                pending_y = float(value)
            elif code == "30" and pending_x is not None and pending_y is not None:
                xs.append(pending_x)
                ys.append(pending_y)
                zs.append(float(value))
                pending_x = pending_y = None

    return np.column_stack([xs, ys, zs]) if xs else np.zeros((0, 3))


def thin_to_grid(points, xy_distance, z_distance, weights=None):
    """Keep one point per lattice cell so no two dots sit closer than the laser can safely fire.

    Pass weights to bias which candidate survives each cell - the texture-driven
    sampler uses it so bright areas keep their brightest sample rather than a
    random one, which stops highlights from crawling between runs.
    """
    if len(points) == 0:
        return points, np.zeros(0, dtype=np.int64)

    cells = np.empty((len(points), 3), dtype=np.int64)
    cells[:, 0] = np.floor(points[:, 0] / xy_distance)
    cells[:, 1] = np.floor(points[:, 1] / xy_distance)
    cells[:, 2] = np.floor(points[:, 2] / z_distance)

    if weights is None:
        _, keep = np.unique(cells, axis=0, return_index=True)
    else:
        # Sort by weight so np.unique's first-seen index lands on the best candidate.
        order = np.argsort(-weights, kind="stable")
        _, first = np.unique(cells[order], axis=0, return_index=True)
        keep = order[first]

    keep = np.sort(keep)
    return points[keep], keep


def apply_depth_layers(points, layer_count=0, layer_spacing=None, stagger=1,
                       xy_spacing=DEFAULT_POINT_DISTANCE):
    """Snap Z onto discrete engraving layers, the way Cockpit3D's rasterizer does.

    Real SSLE output is not a smooth surface - it is a stack of planes the laser
    focuses on in turn. Staggering nudges alternate layers sideways so the dots
    do not stack into visible columns, which is what Stagger="2" buys in
    Cockpit3D's own settings.
    """
    if len(points) == 0:
        return points

    result = points.copy()
    lower = float(result[:, 2].min())
    upper = float(result[:, 2].max())
    span = max(upper - lower, 1e-9)

    # Either knob can drive this; an explicit spacing in mm wins when both are set.
    if layer_spacing and layer_spacing > 0:
        layer_count = max(int(round(span / layer_spacing)) + 1, 1)
    if not layer_count or layer_count < 1:
        return result

    if layer_count == 1:
        index = np.zeros(len(result))
    else:
        index = np.rint((result[:, 2] - lower) / span * (layer_count - 1))
        index = np.clip(index, 0, layer_count - 1)

    result[:, 2] = lower + index * (span / max(layer_count - 1, 1))

    if stagger and stagger > 1:
        # Offset each layer by a fraction of a cell, cycling every `stagger` layers.
        phase = (index.astype(np.int64) % stagger) / float(stagger)
        result[:, 0] += phase * xy_spacing
        result[:, 1] += phase * xy_spacing

    return result


def choose_orientation(extent, usable, keep_up=None, keep_depth=None):
    """Pick the axis mapping that lets the mesh sit largest inside the blank.

    Pass keep_up to pin one source axis to crystal height - without it a tall
    subject such as a church tower gets laid on its side to win a bigger scale.
    Pass keep_depth to also choose which elevation faces the viewer, since two
    mappings often tie on scale while showing completely different sides.
    """
    best_mapping, best_scale = (0, 1, 2), 0.0
    for mapping in itertools.permutations(range(3)):
        if keep_up is not None and mapping[1] != keep_up:
            continue
        if keep_depth is not None and mapping[2] != keep_depth:
            continue
        scale = min(usable[axis] / extent[mapping[axis]] for axis in range(3))
        if scale > best_scale:
            best_mapping, best_scale = mapping, scale
    return best_mapping


def fit_points_to_template(points, template, swap_yz=False, flip_axes="",
                           auto_orient=False, upright=None, depth_axis=None):
    """Scale a cloud or mesh to fill the engravable box, centred, aspect ratio intact.

    One uniform scale factor is applied to all three axes - never per-axis - so a
    subject can never come out stretched, only surrounded by more empty glass.
    """
    result = points.copy()

    if swap_yz:
        result = result[:, [0, 2, 1]]
    for axis_name in flip_axes.lower():
        if axis_name in "xyz":
            result[:, "xyz".index(axis_name)] *= -1.0

    usable = np.array([
        template["width"] - 2 * template["border"],
        template["height"] - 2 * template["border"],
        template["depth"] - 2 * template["border"],
    ])

    lower = result.min(axis=0)
    upper = result.max(axis=0)
    extent = np.maximum(upper - lower, 1e-12)

    mapping = (0, 1, 2)
    if auto_orient or upright is not None or depth_axis:
        # "auto" means trust the longest axis to be the subject's up direction.
        keep_up = int(np.argmax(extent)) if upright == "auto" else (
            "xyz".index(upright) if upright else None
        )
        keep_depth = "xyz".index(depth_axis) if depth_axis else None
        mapping = choose_orientation(extent, usable, keep_up, keep_depth)
        result = result[:, list(mapping)]
        lower, upper = lower[list(mapping)], upper[list(mapping)]
        extent = extent[list(mapping)]

    scale = float(np.min(usable / extent))
    centre = (upper + lower) / 2.0

    # Name whichever axis ran out of room first, since that is what caps the size.
    binding = "XYZ"[int(np.argmin(usable / extent))]
    return (result - centre) * scale, scale, mapping, binding


def resolve_template(name, width=None, height=None, depth=None, border=None):
    """Start from a named blank and let any explicit dimension override it."""
    template = dict(CRYSTAL_TEMPLATES.get(name, CRYSTAL_TEMPLATES["60x80x40"]))
    for key, value in (("width", width), ("height", height),
                       ("depth", depth), ("border", border)):
        if value:
            template[key] = float(value)
    return template
