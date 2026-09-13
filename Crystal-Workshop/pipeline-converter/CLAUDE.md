# pipeline-converter — Project Context

## What this project does

Converts Cockpit3D `.cad` and `.dxf` point-cloud exports to:
- `.xyz` — plain readable coordinates (CloudCompare, MeshLab, Blender)
- `.stl` — binary triangulated mesh for 3D printers and CAD tools
- `.obj` — real triangulated mesh with faces (optional, for Blender etc.)

Cockpit3D only exports `.cad` or `.dxf`. This converter bridges to `.stl` for printer companies and other tools.

It also goes the other way: `mesh_to_pointcloud.py` turns an OBJ or a
triangle-mesh DXF (Meshy, Blender, CAD) into the POINT-cloud DXF the SSLE
engraver reads, fitted to a crystal blank.

## Setup

Venv is at `.venv/` — open VSCode with `pipeline-converter/` as the workspace root.

```powershell
.\.venv\Scripts\Activate.ps1
```

## Converting files

```powershell
# Mesh (OBJ or 3DFACE DXF) to printable point-cloud DXF
python code/mesh_to_pointcloud.py --file "input/model.obj" --template 60x80x40 --points 750000 --upright y

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
- `code/mesh_to_pointcloud.py` — OBJ / 3DFACE-DXF surface sampling to printable POINT DXF
- `code/rebuild_pointcloud.py` — repair, resize, re-space and layer an existing POINT DXF
- `code/utils/printer_dxf.py` — the printer's exact DXF format, blanks, grid thinning, layering
- `code/purify_dxf.py` — minimal POINT DXF to standards-compliant AC1015
- `code/inspect_file.py` — inspect unknown files without converting

## Formats

**DXF from Cockpit3D**: POINT entities only on layer VWX. Parsed natively via group codes 10/20/30 inside ENTITIES section.

**CAD from Cockpit3D**: Proprietary CIRasterizer text format. Coordinate rows: `0 501 X Y Z`.

**STL**: Binary STL, Delaunay method triangulates XY plane with Z as depth — correct geometry for K9 crystal engravings (2.5D surfaces).

**OBJ**: Real mesh with `v` and `f` lines using same Delaunay triangulation.

## Mesh to point cloud

`purify_dxf.py` only understands `POINT` entities. A mesh DXF pushed through it
comes out empty — use `mesh_to_pointcloud.py` first.

Key options:

```
--template 60x80x40     crystal blank; also 60x80x30, 80x50x50, 120x80x40, 90x60x60
--points 750000         target dot count (0 hands control to --spacing)
--spacing 0.07          mm between dots, Cockpit3D's own PointCloudBuilder default
--min-distance 0.07     hard floor, below which the laser over-burns the glass
--upright [auto|x|y|z]  pin a source axis to crystal height
--auto-orient           maximise size, may rotate the subject
--swap-yz / --flip xz   fix Z-up or mirrored sources
--xyz                   also write an XYZ preview for CloudCompare or MeshLab
```

**Depth is usually the binding constraint.** A 60x80x40 blank with a 5 mm border
leaves only 30 mm of engravable depth, which runs out well before width or
height. The console prints which axis capped the fit.

**Orientation is not guessable.** `--auto-orient` alone picks whichever mapping
scales largest, and for Hallgrímskirkja that laid the tower on its side — the
model's longest axis was the nave, not the tower. `--upright y` gave the same
scale with the church standing correctly. Always check a preview render before
sending a job to the printer.

## Texture-driven density

Geometry alone gives an even dot field, which reads as a model in the glass.
Cockpit3D modulates dot density by image brightness - that is what makes their
output read as a photograph. `--texture` does the same job here:

```
--texture photo.jpg        image whose brightness drives density
--texture-mode uv|project  through mesh UVs, or flattened onto the XY footprint
--toning 1.8               gamma on brightness; Cockpit3D's own default
--density-floor 0.05       keeps the darkest areas sparse rather than empty
--invert-texture           treat dark as dense instead of light
```

`uv` needs a mesh that carries texture coordinates. Meshy OBJ exports often
have none, in which case the script says so and falls back to `project`, which
is the right model for a relief anyway.

Sampling oversamples by roughly 2.2x when a texture is set, because rejection
throws most of the dark-area candidates away.

## Depth layers

Real SSLE output is a stack of planes the laser focuses on in turn, not a
smooth surface. `--layers 8` matches Cockpit3D's portrait default;
`--layer-spacing` sets the gap in millimetres instead. `--stagger 2` offsets
alternate layers sideways so dots do not stack into visible columns.

## Repairing a file the printer rejects

```powershell
# Pure format repair - not a single coordinate moves
python code/rebuild_pointcloud.py --file "input/broken.dxf"

# Repair plus re-space and layer
python code/rebuild_pointcloud.py --file "input/broken.dxf" --spacing 0.09 --layers 8 --stagger 2

# Repair plus refit into a different blank
python code/rebuild_pointcloud.py --file "input/broken.dxf" --resize --template 80x50x50
```

**You cannot add detail that is not in the source cloud.** Lowering `--spacing`
keeps more of the points that already exist; once the source's own density runs
out, asking for tighter spacing changes nothing. The script prints the native
dot pitch and warns when that happens. For real extra detail, re-run
`mesh_to_pointcloud.py` from the original model.
