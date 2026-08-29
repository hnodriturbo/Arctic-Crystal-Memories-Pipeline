<!--
File: docs/format-notes.md
Purpose:
 - Track observed Cockpit3D CAD format details and current parser assumptions.
-->

# Cockpit3D CAD Format Notes

This document records what is currently known or assumed about Cockpit3D `.cad` files for this converter.

## Observed Coordinate Rows

Earlier inspection found rows shaped like:

```text
0 501 8.12 -47.18 -10.78
0 501 7.49 -45.5 -10.71
0 501 10.43 -51.8 -10.71
```

## Current Column Interpretation

For five-column numeric rows:

```text
0 501 8.12 -47.18 -10.78
```

The converter currently interprets the columns as:

```text
field 0 = possible object, layer, or type flag
field 1 = possible raster, layer, or index value
field 2 = X
field 3 = Y
field 4 = Z
```

Only `X`, `Y`, and `Z` are exported.

## RGB And Color Detection

No confirmed RGB or color columns have been identified yet.

Rows with six or more numeric fields are counted as `possible_rgb_or_extra_fields` during inspection, but the converter still extracts `field 2`, `field 3`, and `field 4` as XYZ for now.

## 2.5D Or Full 3D Status

Unknown.

The Z values in observed sample rows vary slightly, which suggests real depth values may be present. More inspection is needed to determine whether the point cloud behaves like:

- a 2.5D surface,
- a layered engraving/raster cloud,
- or a fuller 3D point cloud.

## Known Metadata

The file may contain metadata references such as:

```text
CIRasterizer
```

These lines are skipped by the converter because they are not numeric coordinate rows.

## Current Parser Strategy

The parser:

- Reads source files line-by-line.
- Treats all-numeric rows with three fields as direct XYZ rows.
- Treats all-numeric rows with five or more fields as prefix plus XYZ rows.
- Skips non-numeric metadata lines.
- Never modifies the source `.cad` file.

## Future Research Notes

Useful future discoveries to record here:

- Whether fields 0 and 1 represent object IDs, layer IDs, raster indexes, or point categories.
- Whether any rows contain reliable RGB values.
- Whether coordinate units are millimeters or another scale.
- Whether the output needs flipping, centering, or scaling for Cockpit3D-to-viewer alignment.


## `.cockpit` scene files (observed 2026-08-25)

A `.cockpit` file is a **ZIP archive**, not a proprietary blob. Entry names are
obfuscated 8.3 strings, but the contents are ordinary:

```txt
CockpitScene.xml     plain UTF-8 XML, fully readable
<random>.ci          geometry, see below
<random>.jpg         the source photo, a valid JPEG
<random>.png         text fallback images, valid PNGs
```

`CockpitScene.xml` carries the whole scene: rasterizer settings, the
`PointCloudBuilderSettings` (`PointXyDistance`, `PointZDistance`, `Toning`,
`TrimToTemplate`), each entity with position/rotation/scale, and the `Template`
element naming the crystal blank and its borders. `SolidEntity` references its
mesh by `Geometry="<name>.ci"` and its texture by `Texture="<name>.jpg"`.

### Direct sample verification (2026-08-29)

All nine locally owned scenes under `ACM-Company/3d_files` were checked
read-only. Each contains exactly one `.ci` mesh and one `SolidEntity` named
`Conversion`. Header counts range from 209,879–441,721 vertices and
418,134–881,089 triangles. Entity position, Euler rotation and per-axis scale
are stored in XML separately from geometry.

The scene's `PointCloudBuilderSettings` is also separate from `Conversion`.
Observed examples use XY/Z distances of `0.07/0.07` or `0.08/0.1` and toning
`1.8`. This is evidence that the imported conversion is a fitted textured mesh
and that point-cloud creation happens later; it is not evidence about the
private model or algorithm that generated the mesh.

### The `.ci` geometry container

24-byte header, then two blocks:

```txt
offset 0   char[4]  "CIBF"
offset 4   uint32   version, observed 1
offset 8   uint32   vertex count
offset 12  uint32   triangle count
offset 16  uint32   floats per vertex, observed 5
offset 20  char[4]  "CRUN"
offset 24  vertex block  = vertexCount * 20 bytes
then       index block   = triangleCount * 12 bytes
```

The size arithmetic is exact across every sample: file size always equals
`24 + 20*vertices + 12*triangles`, so the payload is stored uncompressed at
5 floats (position + UV) per vertex and 3 uint32 indices per triangle.

**But the bytes are scrambled.** Reading them as little-endian floats gives
nonsense, and no region of the file contains values below the vertex count where
the index block should be. Byte statistics per position mod 4 keep the shape of
float/uint32 data (byte 3 of the index block has the lowest entropy), so it is
not a stream cipher — but it is not raw either. Whatever transform is applied is
length-preserving and value-changing, and was not identified.

`CICockpit.exe` is a .NET assembly with its metadata packed — no `BSJB`
signature and only 95 UTF-16 strings — so the writer could not be read either.

**Conclusion: do not try to author `.cockpit` files.** Reading the scene XML for
settings is easy and useful; the geometry is not writable without solving that
transform.

### Things Cockpit3D does read as plain files

- `C:\ProgramData\Cockpit 3D\Shapes\**\*.obj` — crystal blank shapes are
  ordinary Wavefront OBJ in millimetres.
- `C:\ProgramData\Cockpit 3D\Templates\*.template` — trivial text:

```txt
SIZE
125 110 47
OFFSET
0 0 0
USES_GEOMETRY
Heart, Flat Bottom
TYPE
5
```

`USES_GEOMETRY` names a file under `Shapes/`. `TYPE` values 0-8 were observed.
