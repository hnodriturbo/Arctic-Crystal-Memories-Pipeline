"""
File: converter/2.5D-pipeline/code/import_blanks.py
Purpose:
 - Import the real crystal blank shapes and their templates from a local
   Cockpit 3D installation into blanks/, as centred millimetre GLBs plus one
   catalogue JSON.

Why this matters: the viewer's RoundedBoxGeometry is an approximation. These
are the actual blanks Arctic Crystal Memories buys, so a preview built on them
is a preview of the real product - hearts, ornaments and Prestige shapes
included, none of which is a box at all.

Internal use only. These are Cockpit3D's asset files, imported here because
the crystals themselves are purchased from them; do not ship blanks/ in a
public web bundle without deciding that separately.

Two things the source files do NOT do for you, both handled here:

1. The OBJ is not at template scale. "Heart, Flat Bottom.obj" measures
   102.78 x 89.36 x 60 in its own units while its template says 125 x 110 x 47,
   and the three ratios differ - so the mesh is fitted to SIZE per axis, not
   uniformly.
2. The OBJ is not centred. Z runs 0..depth rather than -depth/2..+depth/2.

Usage:
    python code/import_blanks.py
    python code/import_blanks.py --source "C:/ProgramData/Cockpit 3D" --force
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from utils import PIPELINE_ROOT, fail, report  # noqa: E402

DEFAULT_SOURCE = Path("C:/ProgramData/Cockpit 3D")
BLANKS_DIR = PIPELINE_ROOT / "blanks"

# The .template grammar: a bare keyword line, then its values on the next line.
KEYWORDS = ("SIZE", "OFFSET", "BORDER", "BEVEL", "USES_GEOMETRY", "TYPE")


def slugify(name: str) -> str:
    """Filesystem- and URL-safe id for a blank, from its template name."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def parse_template(path: Path) -> dict | None:
    """
    Read one .template file.

    Trivial format, but every field except SIZE and TYPE is optional, so a
    missing BORDER means "no documented margin" rather than zero - the caller
    decides what to do about that.
    """
    lines = [line.strip() for line in path.read_text(encoding="utf-8", errors="replace").splitlines()]
    fields: dict[str, str] = {}

    for index, line in enumerate(lines):
        if line in KEYWORDS and index + 1 < len(lines):
            fields[line] = lines[index + 1].strip()

    if "SIZE" not in fields:
        return None

    def numbers(key: str) -> list[float] | None:
        if key not in fields:
            return None
        try:
            return [float(part) for part in fields[key].split()]
        except ValueError:
            return None

    size = numbers("SIZE")
    if not size or len(size) != 3:
        return None

    blank = {
        "name": path.stem,
        "id": slugify(path.stem),
        "width": size[0],
        "height": size[1],
        "depth": size[2],
        "type": int(fields["TYPE"]) if fields.get("TYPE", "").isdigit() else None,
        "geometry": fields.get("USES_GEOMETRY"),
    }

    offset = numbers("OFFSET")
    if offset and len(offset) == 3 and any(offset):
        blank["offset"] = offset

    # Per-axis, and far larger than a uniform 1 mm - the notched crystal
    # documents 10 10 2. This is the authoritative margin for these blanks.
    border = numbers("BORDER")
    if border and len(border) == 3:
        blank["border"] = border

    bevel = numbers("BEVEL")
    if bevel:
        blank["bevel"] = bevel[0]

    return blank


def load_obj(path: Path) -> tuple[np.ndarray, list[list[int]]]:
    """Read vertices and triangulated faces from a Wavefront OBJ."""
    vertices: list[tuple[float, float, float]] = []
    faces: list[list[int]] = []

    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("v "):
            parts = line.split()
            vertices.append((float(parts[1]), float(parts[2]), float(parts[3])))
        elif line.startswith("f "):
            # Tokens are v, v/vt, v//vn or v/vt/vn; only the vertex index matters.
            corners = [int(token.split("/")[0]) - 1 for token in line.split()[1:]]
            for corner in range(1, len(corners) - 1):
                faces.append([corners[0], corners[corner], corners[corner + 1]])

    return np.asarray(vertices, dtype=np.float64), faces


def fit_to_size(vertices: np.ndarray, size: tuple[float, float, float]) -> np.ndarray:
    """
    Scale a shape's bounding box onto the template's millimetres and centre it.

    Per-axis, because the source ratios genuinely differ - the same heart mesh
    is reused across several template sizes with different proportions.
    """
    low = vertices.min(axis=0)
    span = vertices.max(axis=0) - low
    span[span == 0] = 1.0  # a flat axis would otherwise divide by zero

    normalised = (vertices - low) / span
    return (normalised - 0.5) * np.asarray(size, dtype=np.float64)


def main() -> int:
    parser = argparse.ArgumentParser(description="Import Cockpit 3D blank shapes and templates.")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--force", action="store_true", help="Rewrite GLBs that already exist.")
    args = parser.parse_args()

    try:
        import trimesh
    except ImportError:
        fail("trimesh is not installed. Run: pip install -r requirements.txt")

    templates_dir = args.source / "Templates"
    shapes_dir = args.source / "Shapes"
    if not templates_dir.is_dir():
        fail(f"No Templates folder under {args.source}. Is Cockpit 3D installed on this machine?")

    # Shapes are filed under a category folder, but templates reference them by
    # bare name, so build one lookup across every subfolder.
    shape_files = {path.stem: path for path in shapes_dir.rglob("*.obj")} if shapes_dir.is_dir() else {}
    report(f"[blanks] {len(shape_files)} shape meshes available")

    BLANKS_DIR.mkdir(parents=True, exist_ok=True)
    catalogue = []
    written = 0
    missing = []

    for template_path in sorted(templates_dir.glob("*.template")):
        blank = parse_template(template_path)
        if blank is None:
            report(f"[blanks] skipped unreadable template: {template_path.name}")
            continue

        geometry_name = blank.pop("geometry", None)
        if geometry_name:
            source_mesh = shape_files.get(geometry_name)
            if source_mesh is None:
                # A template naming a shape this installation does not have is
                # worth reporting, not worth failing on.
                missing.append(f"{blank['name']} -> {geometry_name}")
            else:
                target = BLANKS_DIR / f"{blank['id']}.glb"
                if args.force or not target.exists():
                    vertices, faces = load_obj(source_mesh)
                    fitted = fit_to_size(vertices, (blank["width"], blank["height"], blank["depth"]))
                    trimesh.Trimesh(vertices=fitted, faces=faces, process=False).export(target)
                    written += 1
                blank["model"] = target.name
                blank["sourceShape"] = geometry_name

        catalogue.append(blank)

    catalogue.sort(key=lambda entry: entry["name"])
    manifest = BLANKS_DIR / "blanks.json"
    manifest.write_text(
        json.dumps(
            {
                "source": str(args.source),
                "note": "Imported from a local Cockpit 3D installation for internal preview use.",
                "convention": "Millimetres, centred on the origin. X=width, Y=height, Z=depth.",
                "blanks": catalogue,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    shaped = sum(1 for entry in catalogue if entry.get("model"))
    bordered = sum(1 for entry in catalogue if entry.get("border"))
    report(f"[blanks] {len(catalogue)} templates, {shaped} with real geometry, {written} GLBs written")
    report(f"[blanks] {bordered} templates document a per-axis BORDER")
    for entry in missing:
        report(f"[blanks] shape not installed: {entry}")
    report(f"[blanks] wrote {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
