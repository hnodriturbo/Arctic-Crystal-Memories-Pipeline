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
