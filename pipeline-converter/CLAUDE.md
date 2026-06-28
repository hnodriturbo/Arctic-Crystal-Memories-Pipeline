# pipeline-converter — Project Context

## What this project does

Converts Cockpit3D `.cad` and `.dxf` point-cloud exports to:
- `.xyz` — plain readable coordinates (CloudCompare, MeshLab, Blender)
- `.stl` — binary triangulated mesh for 3D printers and CAD tools
- `.obj` — real triangulated mesh with faces (optional, for Blender etc.)

Cockpit3D only exports `.cad` or `.dxf`. This converter bridges to `.stl` for printer companies and other tools.

## Setup

Venv is at `.venv/` — open VSCode with `pipeline-converter/` as the workspace root.

```powershell
.\.venv\Scripts\Activate.ps1
```

## Converting files

```powershell
# DXF to XYZ + STL (full point count)
python code/convert_dxf.py --file "input/dxf/yourfile.dxf" --formats xyz stl

# CAD to XYZ + STL
python code/convert_cad.py --file "input/cad/yourfile.cad" --formats xyz stl
```

## Key options

```
--formats xyz stl obj   output formats
--limit N               first N points only
--scale 1.0             coordinate scale factor
--center                center cloud at origin
--dedupe                remove duplicate XYZ rows
--stl-method delaunay   2.5D surface mesh (default, best for engravings)
--stl-method convex     closed convex hull solid
--sample-rate N         (CAD only) every Nth point
```

## Architecture

- `code/utils/parsers.py` — `parse_cad_points()` for CAD, `parse_dxf_points_fast()` for DXF (native group-code scanner, no ezdxf needed for POINT-only files)
- `code/utils/writers.py` — `write_xyz()`, `write_stl()` (binary, numpy+scipy Delaunay), `write_obj()` (triangulated mesh)
- `code/convert_dxf.py` — CLI for DXF conversion
- `code/convert_cad.py` — CLI for CAD conversion
- `code/inspect_file.py` — inspect unknown files without converting

## Formats

**DXF from Cockpit3D**: POINT entities only on layer VWX. Parsed natively via group codes 10/20/30 inside ENTITIES section.

**CAD from Cockpit3D**: Proprietary CIRasterizer text format. Coordinate rows: `0 501 X Y Z`.

**STL**: Binary STL, Delaunay method triangulates XY plane with Z as depth — correct geometry for K9 crystal engravings (2.5D surfaces).

**OBJ**: Real mesh with `v` and `f` lines using same Delaunay triangulation.
