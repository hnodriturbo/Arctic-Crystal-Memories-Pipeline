# Cockpit3D CAD/DXF Point Cloud Converter — INSTRUCTIONS.md

## Project Purpose

This project is a small, focused Python utility for inspecting and converting Cockpit3D-exported `.cad` and `.dxf` files into readable point-cloud formats.

The goal is to take files exported from Cockpit3D and convert them into formats that can be opened in external viewers such as CloudCompare, MeshLab, or Blender.

Primary target outputs:

- `.xyz` — simplest point-cloud format, best first export.
- `.ply` — recommended for CloudCompare and color support later.
- `.obj` — possible, but point-only OBJ exports contain vertices only, not mesh faces.

Important: this project is **not** an image enhancement pipeline. Do not add AI upscaling, background removal, PyTorch, RealESRGAN, GFPGAN, or CUDA dependencies. This converter should stay lightweight and focused.

---

## Main Research Context

The user has a Cockpit3D `.cad` file around 56 MB. Earlier inspection showed that the file appears to be text-readable and contains many coordinate-like rows such as:

```text
0 501 8.12 -47.18 -10.78
0 501 7.49 -45.5 -10.71
0 501 10.43 -51.8 -10.71
```

The file also contains references such as:

```text
CIRasterizer
```

Working assumption:

- The `.cad` file is likely a Cockpit3D / CI proprietary engraving format.
- It may contain a final or near-final SSLE point cloud.
- Rows matching numeric coordinate patterns should be extracted carefully.
- The converter must preserve the original file and never overwrite it.

This project should help reveal what Cockpit3D considers a valid SSLE point cloud.

---

## Python Version

Use **Python 3.11**.

Reason:

- Python 3.11 is already the project standard in the user's K9 Crystal Pipeline work.
- It avoids dependency compatibility surprises.
- This converter does not require Python 3.12+ features.
- It should work on Windows PowerShell with `py -3.11`.

Do not require CUDA or GPU support.

---

## Required Folder Structure

Create this structure in the project root:

```text
cockpit3d-pointcloud-converter/
├── INSTRUCTIONS.md
├── README.md
├── requirements.txt
├── pipeline-setup.md
├── code/
│   ├── convert_cad.py
│   ├── convert_dxf.py
│   ├── inspect_file.py
│   └── utils/
│       ├── __init__.py
│       ├── parsers.py
│       └── writers.py
├── input/
│   ├── cad/
│   └── dxf/
├── output/
│   ├── xyz/
│   ├── ply/
│   ├── obj/
│   └── reports/
└── docs/
    └── format-notes.md
```

PowerShell command to create folders:

```powershell
New-Item -ItemType Directory -Force code, code\utils, input\cad, input\dxf, output\xyz, output\ply, output\obj, output\reports, docs
```

---

## requirements.txt

Create `requirements.txt` with only lightweight dependencies:

```txt
numpy>=1.26.0
rich>=13.7.0
tqdm>=4.66.0
ezdxf>=1.3.0
```

Dependency purpose:

- `numpy` — efficient coordinate storage and numeric cleanup.
- `rich` — readable terminal output and reports.
- `tqdm` — progress bars for large files.
- `ezdxf` — DXF parsing.

Do not add heavy 3D libraries unless truly needed.

Avoid these unless the user explicitly asks later:

- `open3d`
- `torch`
- `trimesh`
- `pymeshlab`
- `laspy`

---

## Setup Guide Required: pipeline-setup.md

Create a `pipeline-setup.md` file explaining exactly how to set up the project on Windows.

It must include:

### 1. Create virtual environment

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Upgrade pip

```powershell
python -m pip install --upgrade pip
```

### 3. Install requirements

```powershell
pip install -r requirements.txt
```

### 4. Verify installation

```powershell
python -c "import numpy, ezdxf, rich, tqdm; print('converter environment ok')"
```

### 5. Add input files

```text
input/cad/example.cad
input/dxf/example.dxf
```

### 6. Run first inspection

```powershell
python code/inspect_file.py --file input/cad/example.cad
```

### 7. Convert CAD to XYZ, PLY, and OBJ

```powershell
python code/convert_cad.py --file input/cad/example.cad --formats xyz ply obj
```

### 8. Convert DXF to XYZ, PLY, and OBJ

```powershell
python code/convert_dxf.py --file input/dxf/example.dxf --formats xyz ply obj
```

---

## Script Requirements

### `inspect_file.py`

Purpose: inspect unknown `.cad`, `.dxf`, or text-like point files without converting yet.

Required behavior:

- Accept `--file` argument.
- Print file size.
- Detect whether file is likely text or binary.
- Count total lines if text-readable.
- Show first safe sample lines.
- Count candidate coordinate rows.
- Detect whether rows appear to contain:
  - XYZ only
  - prefix + XYZ
  - possible RGB values
  - possible layer/index values
- Write a report to `output/reports/<filename>_inspection.md`.

Example command:

```powershell
python code/inspect_file.py --file input/cad/eg_gudny_pabbi.cad
```

---

### `convert_cad.py`

Purpose: parse Cockpit3D-style `.cad` files and export point clouds.

Required behavior:

- Accept `--file` argument.
- Accept `--formats xyz ply obj` argument.
- Read large files safely line-by-line.
- Extract numeric coordinate rows.
- Support rows shaped like:

```text
0 501 8.12 -47.18 -10.78
```

For this pattern, treat:

```text
field 0 = possible object/layer/type flag
field 1 = possible raster/layer/index value
field 2 = X
field 3 = Y
field 4 = Z
```

- Store extracted points as XYZ.
- Skip non-coordinate metadata lines.
- Count skipped lines.
- Write a conversion report.
- Never modify the source `.cad` file.

Required output naming:

```text
output/xyz/<source_name>.xyz
output/ply/<source_name>.ply
output/obj/<source_name>.obj
output/reports/<source_name>_conversion.md
```

Example command:

```powershell
python code/convert_cad.py --file input/cad/eg_gudny_pabbi.cad --formats xyz ply obj
```

---

### `convert_dxf.py`

Purpose: parse DXF files and extract point-like geometry.

Required behavior:

- Use `ezdxf`.
- Read modelspace.
- Extract at minimum:
  - `POINT`
  - `3DFACE` vertices
  - `LINE` start/end points
  - `POLYLINE` / `LWPOLYLINE` vertices where available
- De-duplicate repeated points optionally.
- Export XYZ, PLY, and OBJ.
- Write a conversion report.

Example command:

```powershell
python code/convert_dxf.py --file input/dxf/example.dxf --formats xyz ply obj
```

---

## Output Format Details

### XYZ Export

Simple text format:

```text
x y z
x y z
x y z
```

This is the safest first output for CloudCompare.

---

### PLY Export

Use ASCII PLY first.

Minimum header:

```text
ply
format ascii 1.0
element vertex <POINT_COUNT>
property float x
property float y
property float z
end_header
```

Then write one point per line:

```text
x y z
```

PLY is preferred because RGB/color fields can be added later if discovered in the Cockpit3D file.

---

### OBJ Export

Yes, OBJ can be generated.

For point clouds, OBJ will be vertex-only:

```text
v x y z
v x y z
v x y z
```

Important documentation note:

- OBJ is normally a mesh format.
- If the converter only has points and no faces, the OBJ file will contain vertices but no `f` face rows.
- Some viewers may show vertex-only OBJ poorly or not at all.
- CloudCompare and MeshLab should handle XYZ/PLY better.

Recommended viewing order:

1. Open `.xyz` in CloudCompare.
2. Open `.ply` in CloudCompare.
3. Test `.obj` only if needed for Blender or mesh workflows.

---

## Minimum CLI Design

Use simple arguments.

Example:

```powershell
python code/convert_cad.py --file input/cad/eg_gudny_pabbi.cad --formats xyz ply obj
```

Optional arguments to implement if practical:

```powershell
--limit 100000
--sample-rate 10
--scale 1.0
--center
--dedupe
```

Meaning:

- `--limit` — export only first N points for testing.
- `--sample-rate` — export every Nth point for lighter previews.
- `--scale` — multiply coordinates by a scale factor.
- `--center` — center point cloud around origin.
- `--dedupe` — remove duplicate XYZ rows.

---

## Documentation Requirements

Create or update these docs:

### `README.md`

Must explain:

- What the project does.
- Which files go into `input/cad` and `input/dxf`.
- Which outputs are created.
- Best viewer recommendation: CloudCompare first, MeshLab second, Blender third.
- Warning that Cockpit3D `.cad` may be proprietary and parsing is based on observed text patterns.

### `pipeline-setup.md`

Must include setup and run commands from this instruction file.

### `docs/format-notes.md`

Must document discoveries about the `.cad` file format, including:

- Example coordinate rows found.
- Which columns are interpreted as X/Y/Z.
- Whether RGB/color/texture is detected.
- Whether the cloud appears 2.5D or full 3D.
- Any unknown metadata blocks.

---

## Coding Style

Use clean, readable Python.

Rules:

- Add comments explaining every important block.
- Prefer descriptive variable names.
- Keep scripts small and direct.
- Avoid over-engineering.
- Print clear summaries after conversion.
- Never delete, rewrite, or mutate source files.
- All output paths should be created automatically if missing.

Suggested shared functions in `code/utils/writers.py`:

```python
def write_xyz(points, output_path):
    """Write points to a plain XYZ file."""


def write_ply(points, output_path):
    """Write points to an ASCII PLY point cloud file."""


def write_obj(points, output_path):
    """Write points as vertex-only OBJ rows."""
```

Suggested shared functions in `code/utils/parsers.py`:

```python
def parse_cad_points(file_path):
    """Extract XYZ points from text-readable Cockpit3D CAD rows."""


def is_numeric_row(parts):
    """Return True when all tokens in a split row are numeric."""
```

---

## Success Criteria

The project is successful when:

- A `.cad` file can be inspected.
- Candidate XYZ rows can be counted.
- A `.cad` file can be converted to `.xyz`.
- A `.cad` file can be converted to ASCII `.ply`.
- A `.cad` file can be converted to vertex-only `.obj`.
- A `.dxf` file can be converted to at least `.xyz` and `.ply`.
- Reports are created explaining point count, skipped line count, coordinate bounds, and output paths.
- The outputs can be opened in CloudCompare.

---

## Important Notes for Codex

This is a research/conversion project for a K9 crystal engraving pipeline.

Do not assume the Cockpit3D `.cad` file is a normal CAD format. Treat it as an unknown text-based/proprietary point-cloud-like format until proven otherwise.

Prioritize:

1. Safe inspection.
2. Reliable coordinate extraction.
3. Simple CloudCompare-compatible outputs.
4. Clear documentation of discoveries.

Do not build a GUI.
Do not add web frameworks.
Do not add AI models.
Do not add GPU requirements.
Do not modify original exported files.

