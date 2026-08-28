<!--
File: pipeline-setup.md
Purpose:
 - Provide manual Windows setup steps for the Cockpit3D point-cloud converter.
-->

# Pipeline Converter Setup

This converter should use **Python 3.11**.

Python 3.11 is the recommended version because it matches the current K9 Crystal Pipeline standard and avoids dependency compatibility surprises. Newer Python versions may work for this lightweight converter, but the supported setup target is **Python 3.11**.

During this build, the local shell did not find a usable `python` or `py -3.11` installation. Install Python 3.11 first if these commands do not work on your machine.

## 1. Open PowerShell In The Project Folder

```powershell
cd D:\Hnodri\Repos\K9-Crystal-Pipeline\pipeline-converter
```

## 2. Verify Python 3.11

```powershell
py -3.11 --version
```

Expected style of output:

```text
Python 3.11.x
```

If this fails, install Python 3.11 from the official Python installer and enable the Python launcher during installation.

## 3. Create Virtual Environment

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

After activation, your prompt should show `(.venv)`.

## 4. Upgrade pip

```powershell
python -m pip install --upgrade pip
```

## 5. Install Requirements

```powershell
pip install -r requirements.txt
```

Installed packages:

- `numpy` for numeric support.
- `rich` for readable terminal output.
- `tqdm` for future progress bars on large files.
- `ezdxf` for DXF parsing.

## 6. Verify Installation

```powershell
python -c "import numpy, ezdxf, rich, tqdm; print('converter environment ok')"
```

Expected output:

```text
converter environment ok
```

## 7. Add Input Files

Place Cockpit3D CAD files here:

```text
input/cad/example.cad
```

Place DXF files here:

```text
input/dxf/example.dxf
```

## 8. Run First Inspection

```powershell
python code/inspect_file.py --file input/cad/example.cad
```

The inspection report will be created here:

```text
output/reports/example_inspection.md
```

## 9. Convert CAD To XYZ, PLY, And OBJ

```powershell
python code/convert_cad.py --file input/cad/example.cad --formats xyz ply obj
```

Outputs:

```text
output/xyz/example.xyz
output/ply/example.ply
output/obj/example.obj
output/reports/example_conversion.md
```

## 10. Convert DXF To XYZ, PLY, And OBJ

```powershell
python code/convert_dxf.py --file input/dxf/example.dxf --formats xyz ply obj
```

Outputs:

```text
output/xyz/example.xyz
output/ply/example.ply
output/obj/example.obj
output/reports/example_conversion.md
```

## Optional Conversion Arguments

Limit exported points for a small test:

```powershell
python code/convert_cad.py --file input/cad/example.cad --formats xyz ply --limit 100000
```

Export every 10th point:

```powershell
python code/convert_cad.py --file input/cad/example.cad --formats xyz --sample-rate 10
```

Scale coordinates:

```powershell
python code/convert_cad.py --file input/cad/example.cad --formats xyz --scale 1.0
```

Center around origin:

```powershell
python code/convert_cad.py --file input/cad/example.cad --formats xyz ply --center
```

Remove duplicate points:

```powershell
python code/convert_cad.py --file input/cad/example.cad --formats xyz ply --dedupe
```

## Recommended Viewer Workflow

1. Open `.xyz` in CloudCompare.
2. Open `.ply` in CloudCompare.
3. Test `.obj` only if needed for Blender or a mesh workflow.

OBJ exports are vertex-only because this converter extracts points, not mesh faces.
