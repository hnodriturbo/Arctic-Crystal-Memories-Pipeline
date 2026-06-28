# Cockpit3D Converter — INSTRUCTIONS.md

## Purpose

Convert Cockpit3D-exported `.cad` and `.dxf` point-cloud files into:

- `.xyz` — plain coordinates, opens in CloudCompare, MeshLab, Blender
- `.stl` — binary triangulated mesh for 3D printers and CAD tools
- `.obj` — real triangulated mesh with faces (optional, for Blender/other tools)

Primary use case: Cockpit3D only exports `.cad` or `.dxf`. Printer companies need `.stl`. This converter bridges that gap.

---

## Setup (Python 3.11, Windows)

```powershell
cd pipeline-converter
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Verify:
```powershell
python -c "import numpy, scipy, ezdxf, rich, tqdm; print('ok')"
```

---

## Converting DXF files

DXF files from Cockpit3D contain only `POINT` entities. The converter uses a fast native parser — no ezdxf dependency required for this step.

```powershell
# XYZ only (fast, readable)
python code/convert_dxf.py --file input/dxf/yourfile.dxf --formats xyz

# XYZ + STL (for 3D printing)
python code/convert_dxf.py --file input/dxf/yourfile.dxf --formats xyz stl

# STL only, with point limit for faster triangulation
python code/convert_dxf.py --file input/dxf/yourfile.dxf --formats stl --stl-limit 100000
```

STL methods:
- `--stl-method delaunay` (default) — 2.5D surface mesh, ideal for crystal engravings
- `--stl-method convex` — closed convex hull solid

---

## Converting CAD files

Cockpit3D `.cad` is a proprietary text format. Coordinate rows look like:
```
0 501 8.12 -47.18 -10.78
        X      Y      Z
```

```powershell
# XYZ only
python code/convert_cad.py --file input/cad/yourfile.cad --formats xyz

# XYZ + STL
python code/convert_cad.py --file input/cad/yourfile.cad --formats xyz stl
```

---

## All options

```
--formats xyz stl obj   # choose output formats
--limit N               # export first N points only
--scale 1.0             # multiply all coordinates
--center                # center cloud around origin
--dedupe                # remove duplicate XYZ rows
--stl-method delaunay   # or: convex
--stl-limit N           # subsample to N points before STL triangulation
--sample-rate N         # (CAD only) export every Nth point
```

---

## Output locations

- `output/xyz/` — `.xyz` point cloud files
- `output/stl/` — `.stl` binary mesh files
- `output/obj/` — `.obj` mesh files (triangulated)
- `output/reports/` — conversion reports (point count, bounds, paths)

---

## File format notes

**CAD format** (`eg-gudny-pabbi.cad`): Cockpit3D / CIRasterizer proprietary format. Text-readable. Fields: `0 501 X Y Z` where columns 2–4 are XYZ coordinates. Metadata lines (non-numeric) are skipped automatically.

**DXF format**: Standard DXF but Cockpit3D exports only `POINT` entities on layer `VWX`. Files can be very large (665k–4M points). Native fast parser reads group codes `10/20/30` directly.

**STL**: Binary STL. Delaunay method triangulates the XY plane with Z as depth — correct for K9 crystal engraving geometry. ConvexHull method produces a closed solid.

**OBJ**: Real mesh with `v` vertices and `f` faces. Uses same Delaunay/ConvexHull triangulation as STL.

---

## Dependencies

```
numpy>=1.26.0    — coordinate arrays, STL binary write
scipy>=1.12.0    — Delaunay/ConvexHull triangulation for STL/OBJ
rich>=13.7.0     — terminal output
tqdm>=4.66.0     — progress bars
ezdxf>=1.3.0     — fallback DXF parsing (optional, native parser preferred)
```

Do not add: PyTorch, CUDA, open3d, trimesh, GUI frameworks, web frameworks.
