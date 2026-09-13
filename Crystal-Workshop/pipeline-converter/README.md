<!--
File: README.md
Purpose:
 - Explain the Cockpit3D point-cloud converter workflow and project structure.
-->

# ACM Model and Point-Cloud Converter

This project supports two related conversion paths:

- `convert_model.py` reads common 3D models, inspects and sizes them in millimetres, optionally slices them, and exports one or more model formats.
- `convert_cad.py` and `convert_dxf.py` inspect Cockpit3D point files and export readable point-cloud formats.

The main goal is to extract coordinate-like rows from Cockpit3D files and export them into formats that can be opened in external viewers.

## Universal model conversion

Supported model inputs are `.blend`, `.dxf` (`3DFACE` mesh), `.obj`, `.stl`,
`.ply`, `.glb`, `.gltf`, `.fbx`, `.dae`, `.usd`, `.usda`, `.usdc`, and `.usdz`.
Supported outputs are `.dxf` (SSLE `POINT` cloud), `.glb`, `.gltf`, `.obj`,
`.stl`, `.ply`, `.fbx`, `.usd`, and `.usdz`.

Blender 4.5 LTS or newer is required. Set `BLENDER_EXE` when Blender is not on
`PATH`. The source is never modified, and selecting multiple formats creates a
ZIP alongside the individual files.

```powershell
.\.venv\Scripts\python.exe code\convert_model.py `
    --file input\uploads\model.glb `
    --formats dxf glb stl `
    --input-unit mm `
    --fit-width 58 --fit-height 78 --fit-depth 38 `
    --placement center `
    --slice-axis z --slice-min -15 --slice-max 15 --fill-cuts
```

`POINT`-DXF is final printer data and cannot be reconstructed into a surface
model. Use the point-cloud commands below to inspect or translate it. A
`3DFACE` mesh DXF can use the universal model command.

## Point-cloud outputs

- `.xyz` - simplest point-cloud format and the best first test export.
- `.ply` - recommended for CloudCompare and future color support.
- `.obj` - vertex-only OBJ export for Blender or mesh workflows.

Viewer recommendation:

1. CloudCompare first.
2. MeshLab second.
3. Blender third.

## Important CAD Warning

Cockpit3D `.cad` files may be proprietary and are not assumed to be normal CAD files. This converter parses based on observed text-readable coordinate patterns, such as:

```text
0 501 8.12 -47.18 -10.78
```

For that row shape, the converter treats columns 3, 4, and 5 as `X`, `Y`, and `Z`.

## Folder Layout

```text
pipeline-converter/
├── INSTRUCTIONS.md
├── README.md
├── requirements.txt
├── pipeline-setup.md
├── code/
│   ├── blender_model_io.py
│   ├── convert_model.py
│   ├── convert_cad.py
│   ├── convert_dxf.py
│   ├── inspect_file.py
│   └── utils/
├── input/
│   ├── cad/
│   ├── dxf/
│   └── uploads/
├── output/
│   ├── conversions/
│   ├── xyz/
│   ├── ply/
│   ├── obj/
│   └── reports/
└── docs/
    └── format-notes.md
```

## Input Files

Place Cockpit3D `.cad` files here:

```text
input/cad/
```

Place `.dxf` files here:

```text
input/dxf/
```

## Basic Commands

Inspect a CAD file before converting:

```powershell
python code/inspect_file.py --file input/cad/example.cad
```

Convert CAD to all supported formats:

```powershell
python code/convert_cad.py --file input/cad/example.cad --formats xyz ply obj
```

Convert DXF to all supported formats:

```powershell
python code/convert_dxf.py --file input/dxf/example.dxf --formats xyz ply obj
```

## Safety Notes

- Source `.cad` and `.dxf` files are never modified.
- Outputs are written into the `output/` folders.
- Reports are written into `output/reports/`.
- No CUDA, AI models, PyTorch, or GPU dependencies are required.
- Universal model conversion uses Blender headlessly; the point-only tools do not.
