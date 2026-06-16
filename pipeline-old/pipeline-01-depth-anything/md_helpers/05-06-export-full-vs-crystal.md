# Export Strategy: Full-Size vs Crystal-Size Mesh

## The Two-Step Export Approach

Stage 05 produces two separate outputs:

| Step | Script                | Output folder           | Units                   |
| ---- | --------------------- | ----------------------- | ----------------------- |
| 05   | `05_export.py`        | `exports/full_size/`    | Model space (-1..+1 XY) |
| 06   | `06_scale_crystal.py` | `exports/crystal_size/` | Millimeters (physical)  |

The full-size file is kept as the editable master. The crystal-size file is what you import into Cockpit3D.

---

## Full-Size Export

### Pros
- **Best for editing** — mesh dimensions stay in a normalized range that Blender, Meshmixer, and MeshLab handle well without floating-point precision issues.
- **Preset-agnostic** — you can scale to any crystal size later without re-running Stages 01–04.
- **Easier validation** — geometry errors (holes, flipped normals, intersections) are easier to spot and fix when the mesh fills the viewport predictably.
- **Reuse** — one master mesh, many crystal sizes. Run `05b_scale_crystal.py --crystal s_cube` and then `--crystal l_cube` from the same full-size file.

### Cons
- **Not directly importable into Cockpit3D** — Cockpit3D expects millimeter-scale geometry. Importing a unit-scale mesh will produce an engraving the size of a grain of sand.
- **No physical reference** — you cannot compare it to a ruler or the crystal blank during review.

---

## Crystal-Size Export

### Pros
- **Cockpit3D-ready** — dimensions match the physical blank exactly. Import, position, and engrave without any manual rescaling inside the software.
- **Predictable laser depth** — because the mesh Z-axis is in real mm, you can directly verify that the deepest point does not exceed the crystal's safe engraving depth (typically D − 5 mm).
- **Client preview accuracy** — renders and previews show the actual physical proportions.

### Cons
- **Locked to one blank size** — if you switch from `m_cube` to `l_cube`, you must re-run `05b_scale_crystal.py`. The file itself carries no record of which preset it was scaled from (the report `.txt` does).
- **Harder to edit at scale** — small geometry errors become even smaller in mm space; some tools lose precision at sub-millimeter scale.
- **Risk of accidental import of wrong size** — if you have both `_crystal_s_cube.obj` and `_crystal_l_cube.obj` in the same folder it is easy to import the wrong one into Cockpit3D.

---

## Recommended Workflow

```
05_export.py          → inspect in Blender, fix any holes
       ↓
05b_scale_crystal.py  → pick preset, import directly into Cockpit3D
```

Always fix the mesh in the full-size version. Never edit the crystal-size file — treat it as a build artifact, not a source file.

---

## Crystal Preset Reference

All popular K9 blank sizes. Values are outer blank dimensions in mm.

| Preset    | W (mm) | H (mm) | D (mm) | Best use                       |
| --------- | -----: | -----: | -----: | ------------------------------ |
| `xs_cube` |     40 |     40 |     30 | Keychain, pendant              |
| `s_cube`  |     60 |     60 |     40 | Small desk, starter size       |
| `m_cube`  |     80 |     80 |     50 | Medium desk — **most popular** |
| `l_cube`  |    100 |    100 |     60 | Large desk, portrait           |
| `xl_cube` |    120 |    120 |     80 | Extra large, premium gift      |
| `s_rect`  |     80 |     60 |     40 | Small landscape                |
| `m_rect`  |    100 |     80 |     50 | Medium landscape               |
| `l_rect`  |    120 |     80 |     60 | Large landscape                |
| `s_heart` |     80 |     80 |     40 | Heart shape (bounding box)     |
| `tower`   |     60 |     60 |    100 | Tall pillar, standing portrait |

W = left–right, H = top–bottom, D = front–back (laser depth axis).

---

## PowerShell Quick Reference

```powershell
# Stage 05 — validate + full-size export (all formats from .env)
.\.venv\Scripts\python.exe .\py_step_files\05_export.py

# Stage 05 — OBJ only, no smoothing
.\.venv\Scripts\python.exe .\py_step_files\05_export.py --export-format obj --smooth 0

# Stage 05b — list all presets
.\.venv\Scripts\python.exe .\py_step_files\05b_scale_crystal.py --list-crystals

# Stage 05b — scale to medium cube (default)
.\.venv\Scripts\python.exe .\py_step_files\05b_scale_crystal.py

# Stage 05b — scale to large cube
.\.venv\Scripts\python.exe .\py_step_files\05b_scale_crystal.py --crystal l_cube

# Stage 05b — custom size (W H D in mm)
.\.venv\Scripts\python.exe .\py_step_files\05b_scale_crystal.py --crystal-size 90 70 55

# Stage 05b — OBJ only for Cockpit3D import
.\.venv\Scripts\python.exe .\py_step_files\05b_scale_crystal.py --crystal m_cube --export-format obj
```
