<!--
File: README.md
Purpose:
 - Explain the Cockpit3D point-cloud converter workflow and project structure.
-->

# Cockpit3D Point Cloud Converter

This project is a lightweight Python utility for inspecting and converting Cockpit3D-exported `.cad` files and standard `.dxf` files into readable point-cloud formats.

The main goal is to extract coordinate-like rows from Cockpit3D files and export them into formats that can be opened in external viewers.

## Supported Outputs

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
│   ├── convert_cad.py
│   ├── convert_dxf.py
│   ├── inspect_file.py
│   └── utils/
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
