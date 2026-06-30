"""
code/purify_dxf.py  —  DXF Fixer

Fixes minimal Cockpit3D DXF exports into standards-compliant
AC1015 (AutoCAD 2000 / R2000) DXF files that open in all laser-engraving software.

Changes made — structural only, coordinates are never modified:
  - Adds $ACADVER = AC1015 to HEADER
  - Sets correct $EXTMIN / $EXTMAX from actual point bounds
  - Sets $INSUNITS = 4 (mm), $MEASUREMENT = 1 (metric)
  - Sets $LIMMAX from crystal template dimensions (or from bounds if unknown file)
  - Adds proper TABLES section: VPORT, LTYPE, LAYER (VWX defined),
    STYLE, VIEW, UCS, APPID, DIMSTYLE, BLOCK_RECORD
  - Adds proper BLOCKS section (*Model_Space, *Paper_Space)
  - Adds AC1015 subclass markers (100/AcDbEntity, 100/AcDbPoint) to POINT entities
  - Assigns proper hex handles to all entities

Usage:
    # Purify a single file (any DXF):
    python code/purify_dxf.py --file path/to/yourfile.dxf

    # Purify all registered files in input/new/:
    python code/purify_dxf.py
"""

import argparse
import sys
from pathlib import Path

from rich.console import Console

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).parent))

console = Console()

PURIFIED_ROOT = PROJECT_ROOT / "output" / "purified_dxf"


def next_batch_dir():
    """Return the next batch_N directory under output/purified_dxf/."""
    existing = [
        d for d in PURIFIED_ROOT.iterdir()
        if d.is_dir() and d.name.startswith("batch_") and d.name[6:].isdigit()
    ] if PURIFIED_ROOT.exists() else []
    next_n = max((int(d.name[6:]) for d in existing), default=0) + 1
    return PURIFIED_ROOT / f"batch_{next_n}"


OUTPUT_DIR = None  # resolved once in main() so multi-file runs share one batch

# Known crystal template settings from Cockpit3D screenshots.
# Used to set $LIMMAX correctly. Any file not listed here falls back
# to its actual coordinate range for $LIMMAX.
CRYSTAL_METADATA = {
    "group-photo-80mm-50mm-40mm-711839points": {
        "width": 80.0, "height": 50.0, "depth": 50.0,
        "type": "3D small", "margin": 3, "bevel": 3, "article_id": "",
    },
    "me-guitar-tenerife-60mm-80mm-40mm-549604points": {
        "width": 60.0, "height": 80.0, "depth": 40.0,
        "type": "3D small", "margin": 3, "bevel": 3, "article_id": "",
    },
    "dad-fish-60mm-80mm-40mm-725592points": {
        "width": 60.0, "height": 80.0, "depth": 40.0,
        "type": "3D large", "margin": 5, "bevel": 5, "article_id": "A0009",
    },
    "volcanic-activity-120mm-80mm-40mm-3244427points": {
        "width": 120.0, "height": 80.0, "depth": 40.0,
        "type": "3D large", "margin": 3, "bevel": 3, "article_id": "A0009",
    },
    # batch_2 — X area adjusted re-exports
    "volcanic-activity-120mm-80mm-40mm-2795289points": {
        "width": 120.0, "height": 80.0, "depth": 40.0,
        "type": "3D large", "margin": 3, "bevel": 3, "article_id": "A0009",
    },
    "me-guitar-tenerife-60mm-80mm-40mm-462706points": {
        "width": 60.0, "height": 80.0, "depth": 40.0,
        "type": "3D small", "margin": 3, "bevel": 3, "article_id": "",
    },
}


def g(code, value):
    """Write a single DXF group-code / value pair (two lines)."""
    return f"{code}\n{value}\n"


def meta_from_bounds(bounds):
    """Fallback metadata derived from actual point cloud extents."""
    return {
        "width":  round(bounds["max_x"] - bounds["min_x"], 4),
        "height": round(bounds["max_y"] - bounds["min_y"], 4),
        "depth":  round(bounds["max_z"] - bounds["min_z"], 4),
        "type": "unknown", "margin": 0, "bevel": 0, "article_id": "",
    }


def build_header(bounds, meta):
    min_x, max_x = bounds["min_x"], bounds["max_x"]
    min_y, max_y = bounds["min_y"], bounds["max_y"]
    min_z, max_z = bounds["min_z"], bounds["max_z"]
    return "".join([
        g(0, "SECTION"), g(2, "HEADER"),
        g(9, "$ACADVER"),     g(1,  "AC1015"),
        g(9, "$DWGCODEPAGE"), g(3,  "ANSI_1252"),
        g(9, "$INSBASE"),     g(10, "0.0"),  g(20, "0.0"),  g(30, "0.0"),
        g(9, "$EXTMIN"),
            g(10, f"{min_x:.8g}"), g(20, f"{min_y:.8g}"), g(30, f"{min_z:.8g}"),
        g(9, "$EXTMAX"),
            g(10, f"{max_x:.8g}"), g(20, f"{max_y:.8g}"), g(30, f"{max_z:.8g}"),
        g(9, "$LIMMIN"),      g(10, "0.0"),  g(20, "0.0"),
        g(9, "$LIMMAX"),
            g(10, str(meta["width"])), g(20, str(meta["height"])),
        g(9, "$LUNITS"),      g(70, "2"),
        g(9, "$LUPREC"),      g(70, "4"),
        g(9, "$INSUNITS"),    g(70, "4"),
        g(9, "$MEASUREMENT"), g(70, "1"),
        g(9, "$LTSCALE"),     g(40, "1.0"),
        g(9, "$TEXTSTYLE"),   g(7,  "Standard"),
        g(9, "$CLAYER"),      g(8,  "VWX"),
        g(9, "$CELTYPE"),     g(6,  "BYLAYER"),
        g(9, "$CECOLOR"),     g(62, "256"),
        g(9, "$CELTSCALE"),   g(40, "1.0"),
        g(9, "$PDMODE"),      g(70, "0"),
        g(9, "$PDSIZE"),      g(40, "0.0"),
        g(9, "$HANDSEED"),    g(5,  "FFFFFF"),
        g(0, "ENDSEC"),
    ])


def build_tables():
    return "".join([
        g(0, "SECTION"), g(2, "TABLES"),

        # --- VPORT ---
        g(0, "TABLE"), g(2, "VPORT"), g(5, "8"),
        g(100, "AcDbSymbolTable"), g(70, "1"),
        g(0, "VPORT"), g(5, "9"),
        g(100, "AcDbSymbolTableRecord"), g(100, "AcDbViewportTableRecord"),
        g(2,  "*Active"), g(70, "0"),
        g(10, "0.0"),   g(20, "0.0"),
        g(11, "1.0"),   g(21, "1.0"),
        g(12, "0.0"),   g(22, "0.0"),
        g(13, "0.0"),   g(23, "0.0"),
        g(14, "10.0"),  g(24, "10.0"),
        g(15, "10.0"),  g(25, "10.0"),
        g(16, "0.0"),   g(26, "0.0"),  g(36, "1.0"),
        g(17, "0.0"),   g(27, "0.0"),  g(37, "0.0"),
        g(40, "70.0"),  g(41, "1.34"), g(42, "50.0"),
        g(43, "0.0"),   g(44, "0.0"),
        g(50, "0.0"),   g(51, "0.0"),
        g(71, "0"), g(72, "100"), g(73, "1"), g(74, "3"),
        g(75, "0"), g(76, "0"),   g(77, "0"), g(78, "0"),
        g(0, "ENDTAB"),

        # --- LTYPE ---
        g(0, "TABLE"), g(2, "LTYPE"), g(5, "A"),
        g(100, "AcDbSymbolTable"), g(70, "3"),
        g(0, "LTYPE"), g(5, "B"),
        g(100, "AcDbSymbolTableRecord"), g(100, "AcDbLinetypeTableRecord"),
        g(2, "BYLAYER"),    g(70, "0"), g(3, ""), g(72, "65"), g(73, "0"), g(40, "0.0"),
        g(0, "LTYPE"), g(5, "C"),
        g(100, "AcDbSymbolTableRecord"), g(100, "AcDbLinetypeTableRecord"),
        g(2, "BYBLOCK"),    g(70, "0"), g(3, ""), g(72, "65"), g(73, "0"), g(40, "0.0"),
        g(0, "LTYPE"), g(5, "D"),
        g(100, "AcDbSymbolTableRecord"), g(100, "AcDbLinetypeTableRecord"),
        g(2, "Continuous"), g(70, "0"), g(3, "Solid line"), g(72, "65"), g(73, "0"), g(40, "0.0"),
        g(0, "ENDTAB"),

        # --- LAYER ---
        g(0, "TABLE"), g(2, "LAYER"), g(5, "E"),
        g(100, "AcDbSymbolTable"), g(70, "2"),
        g(0, "LAYER"), g(5, "F"),
        g(100, "AcDbSymbolTableRecord"), g(100, "AcDbLayerTableRecord"),
        g(2, "0"),   g(70, "0"), g(62, "7"), g(6, "Continuous"),
        g(0, "LAYER"), g(5, "10"),
        g(100, "AcDbSymbolTableRecord"), g(100, "AcDbLayerTableRecord"),
        g(2, "VWX"), g(70, "0"), g(62, "7"), g(6, "Continuous"),
        g(0, "ENDTAB"),

        # --- STYLE ---
        g(0, "TABLE"), g(2, "STYLE"), g(5, "11"),
        g(100, "AcDbSymbolTable"), g(70, "1"),
        g(0, "STYLE"), g(5, "12"),
        g(100, "AcDbSymbolTableRecord"), g(100, "AcDbTextStyleTableRecord"),
        g(2, "Standard"), g(70, "0"),
        g(40, "0.0"), g(41, "1.0"), g(50, "0.0"), g(71, "0"), g(42, "2.5"),
        g(3, "txt"), g(4, ""),
        g(0, "ENDTAB"),

        # --- VIEW (empty) ---
        g(0, "TABLE"), g(2, "VIEW"), g(5, "13"),
        g(100, "AcDbSymbolTable"), g(70, "0"),
        g(0, "ENDTAB"),

        # --- UCS (empty) ---
        g(0, "TABLE"), g(2, "UCS"), g(5, "14"),
        g(100, "AcDbSymbolTable"), g(70, "0"),
        g(0, "ENDTAB"),

        # --- APPID ---
        g(0, "TABLE"), g(2, "APPID"), g(5, "15"),
        g(100, "AcDbSymbolTable"), g(70, "1"),
        g(0, "APPID"), g(5, "16"),
        g(100, "AcDbSymbolTableRecord"), g(100, "AcDbRegAppTableRecord"),
        g(2, "ACAD"), g(70, "0"),
        g(0, "ENDTAB"),

        # --- DIMSTYLE ---
        g(0, "TABLE"), g(2, "DIMSTYLE"), g(5, "17"),
        g(100, "AcDbSymbolTable"), g(70, "1"),
        g(100, "AcDbDimStyleTable"), g(71, "0"),
        g(0, "DIMSTYLE"), g(5, "18"),
        g(100, "AcDbSymbolTableRecord"), g(100, "AcDbDimStyleTableRecord"),
        g(2, "Standard"), g(70, "0"),
        g(40, "1.0"), g(41, "2.5"), g(42, "0.625"), g(43, "3.75"), g(44, "1.25"),
        g(45, "0.0"), g(46, "0.0"), g(47, "0.0"), g(48, "1.0"),
        g(140, "2.5"), g(141, "2.5"), g(142, "0.0"), g(143, "25.4"),
        g(144, "1.0"), g(145, "0.0"), g(146, "1.0"), g(147, "0.625"),
        g(71, "0"),  g(72, "0"),  g(73, "1"),  g(74, "1"),
        g(75, "0"),  g(76, "0"),  g(77, "0"),  g(78, "0"),
        g(170, "0"), g(171, "2"), g(172, "0"), g(173, "0"),
        g(174, "0"), g(175, "0"), g(176, "0"), g(177, "0"), g(178, "0"),
        g(0, "ENDTAB"),

        # --- BLOCK_RECORD ---
        g(0, "TABLE"), g(2, "BLOCK_RECORD"), g(5, "19"),
        g(100, "AcDbSymbolTable"), g(70, "2"),
        g(0, "BLOCK_RECORD"), g(5, "1A"),
        g(100, "AcDbSymbolTableRecord"), g(100, "AcDbBlockTableRecord"),
        g(2, "*Model_Space"),
        g(0, "BLOCK_RECORD"), g(5, "1B"),
        g(100, "AcDbSymbolTableRecord"), g(100, "AcDbBlockTableRecord"),
        g(2, "*Paper_Space"),
        g(0, "ENDTAB"),

        g(0, "ENDSEC"),
    ])


def build_blocks():
    return "".join([
        g(0, "SECTION"), g(2, "BLOCKS"),
        g(0, "BLOCK"),   g(5, "1C"),
        g(100, "AcDbEntity"), g(8, "0"),
        g(100, "AcDbBlockBegin"),
        g(2, "*Model_Space"), g(70, "0"),
        g(10, "0.0"), g(20, "0.0"), g(30, "0.0"),
        g(3, "*Model_Space"), g(1, ""),
        g(0, "ENDBLK"), g(5, "1D"),
        g(100, "AcDbEntity"), g(8, "0"),
        g(100, "AcDbBlockEnd"),
        g(0, "BLOCK"),   g(5, "1E"),
        g(100, "AcDbEntity"), g(8, "0"),
        g(100, "AcDbBlockBegin"),
        g(2, "*Paper_Space"), g(70, "0"),
        g(10, "0.0"), g(20, "0.0"), g(30, "0.0"),
        g(3, "*Paper_Space"), g(1, ""),
        g(0, "ENDBLK"), g(5, "1F"),
        g(100, "AcDbEntity"), g(8, "0"),
        g(100, "AcDbBlockEnd"),
        g(0, "ENDSEC"),
    ])


def scan_dxf_bounds(file_path):
    """First pass over DXF: find actual coordinate extents and total point count."""
    min_x = min_y = min_z = float("inf")
    max_x = max_y = max_z = float("-inf")
    count = 0
    in_entities = False
    cur_x = cur_y = None

    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        it = iter(f)
        for raw_code in it:
            code = raw_code.strip()
            try:
                val = next(it).strip()
            except StopIteration:
                break
            if code == "2" and val == "ENTITIES":
                in_entities = True
            elif code == "0" and val == "ENDSEC" and in_entities:
                break
            elif in_entities:
                if code == "10":
                    cur_x = float(val)
                elif code == "20" and cur_x is not None:
                    cur_y = float(val)
                elif code == "30" and cur_x is not None and cur_y is not None:
                    z = float(val)
                    if cur_x < min_x: min_x = cur_x
                    if cur_x > max_x: max_x = cur_x
                    if cur_y < min_y: min_y = cur_y
                    if cur_y > max_y: max_y = cur_y
                    if z < min_z: min_z = z
                    if z > max_z: max_z = z
                    count += 1
                    cur_x = cur_y = None

    return {
        "min_x": min_x, "max_x": max_x,
        "min_y": min_y, "max_y": max_y,
        "min_z": min_z, "max_z": max_z,
        "count": count,
    }


def stream_dxf_entities(src_path, out_file, start_handle=0x100):
    """
    Second pass over DXF: stream POINT entities to out_file verbatim.
    Coordinates are copied as raw strings — zero precision change.
    Adds AC1015 subclass markers and proper hex handles.
    """
    handle = start_handle
    in_entities = False
    in_point = False
    x_str = y_str = None

    with open(src_path, "r", encoding="utf-8", errors="replace") as f:
        it = iter(f)
        for raw_code in it:
            code = raw_code.strip()
            try:
                val = next(it).strip()
            except StopIteration:
                break
            if code == "2" and val == "ENTITIES":
                in_entities = True
                continue
            if code == "0" and val == "ENDSEC" and in_entities:
                break
            if not in_entities:
                continue
            if code == "0" and val == "POINT":
                in_point = True
                x_str = y_str = None
                continue
            if in_point:
                if code == "10":
                    x_str = val
                elif code == "20":
                    y_str = val
                elif code == "30" and x_str is not None and y_str is not None:
                    out_file.write(
                        f"0\nPOINT\n5\n{handle:X}\n"
                        f"100\nAcDbEntity\n8\nVWX\n"
                        f"100\nAcDbPoint\n"
                        f"10\n{x_str}\n20\n{y_str}\n30\n{val}\n"
                    )
                    handle += 1
                    in_point = False

    return handle


def purify_from_dxf(src_path, out_dir, meta=None):
    """DXF → standards-compliant AC1015 DXF. Two-pass streaming, no full file in memory."""
    out_path = out_dir / f"{src_path.stem}_purified.dxf"
    console.print(f"[bold cyan]DXF source:[/bold cyan] {src_path.name}")

    console.print("  Pass 1: scanning bounds...")
    bounds = scan_dxf_bounds(src_path)
    console.print(
        f"  [green]{bounds['count']:,}[/green] points  |  "
        f"X [{bounds['min_x']:.4g}, {bounds['max_x']:.4g}]  "
        f"Y [{bounds['min_y']:.4g}, {bounds['max_y']:.4g}]  "
        f"Z [{bounds['min_z']:.4g}, {bounds['max_z']:.4g}]"
    )

    if meta is None:
        meta = meta_from_bounds(bounds)
        console.print(
            f"  [yellow]No registered metadata — using bounds as template size "
            f"({meta['width']} x {meta['height']} mm)[/yellow]"
        )
    else:
        console.print(
            f"  Template: {meta['type']}  {meta['width']} x {meta['height']} x {meta['depth']} mm"
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    console.print("  Pass 2: writing purified DXF...")
    with open(out_path, "w", encoding="utf-8", newline="\n") as out:
        out.write(build_header(bounds, meta))
        out.write(build_tables())
        out.write(build_blocks())
        out.write(g(0, "SECTION"))
        out.write(g(2, "ENTITIES"))
        stream_dxf_entities(src_path, out)
        out.write(g(0, "ENDSEC"))
        out.write(g(0, "EOF"))

    size_mb = out_path.stat().st_size / 1_048_576
    console.print(f"  [green]Done[/green] → {out_path.name} ({size_mb:.1f} MB)\n")
    return out_path


def main():
    parser = argparse.ArgumentParser(
        description="DXF Fixer — convert minimal Cockpit3D DXF exports to standards-compliant AC1015 DXF."
    )
    parser.add_argument(
        "--file", nargs="+", default=None,
        help="One or more .dxf files to fix. All land in the same new batch folder."
    )
    args = parser.parse_args()

    out_dir = next_batch_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    console.print("[bold]K9 Crystal Pipeline — DXF Fixer[/bold]")
    console.print(f"Output: {out_dir}\n")

    if args.file:
        for file_arg in args.file:
            src = Path(file_arg).resolve()
            if not src.exists():
                console.print(f"[red]File not found: {src}[/red]")
                sys.exit(1)
            meta = CRYSTAL_METADATA.get(src.stem)
            purify_from_dxf(src, out_dir, meta)
    else:
        INPUT_DIR = PROJECT_ROOT / "input" / "dxf"
        console.print(f"Input:  {INPUT_DIR}\n")
        dxf_files = [f for f in INPUT_DIR.glob("*.dxf") if f.is_file()]
        if not dxf_files:
            console.print("[yellow]No .dxf files found in input/dxf/[/yellow]")
        for src in sorted(dxf_files):
            meta = CRYSTAL_METADATA.get(src.stem)
            purify_from_dxf(src, out_dir, meta)
        console.print("[bold green]All DXF files processed.[/bold green]")


if __name__ == "__main__":
    main()
