<!--
File: pipeline-02-zoedepth/pipeline-guide.md
Purpose:
 - Official operator guide for pipeline-02-zoedepth.
 - Documents the isolated ZoeDepth test pipeline and its dependency constraints.
-->

# pipeline-02-zoedepth — Pipeline Guide

> **Crystal Clear Memories** — Isolated ZoeDepth pipeline for metric-depth experiments.
> For creating new pipelines or rebuilding environments, use root `md_helpers/pipeline-setup.md`.

---

## Pipeline Purpose

`pipeline-02-zoedepth` exists because ZoeDepth currently needs dependency pins
that should not be forced into `pipeline-01`.

The key reason for this separate pipeline is `timm==0.9.16`. ZoeDepth failed in
the main environment when used with `timm >= 1.0`, so this folder keeps ZoeDepth
testing isolated and reproducible.

Use this pipeline when comparing metric ZoeDepth maps against the Depth Anything
V2 results from `pipeline-01`.

---

## Quick Start

```powershell
.\.venv\Scripts\Activate.ps1
python 01_upscale.py
python 02_remove_bg.py
python 03_depth_estimate.py --model zoedepth --profile soft_edges_feathered
python 04_mesh_generate.py
```

Stage 05 is still a TODO/stub in this pipeline. Stage 06 is not currently present
in this pipeline folder.

---

## Stage Status

| Stage | Script | Status | Notes |
| --- | --- | --- | --- |
| 01 | `01_upscale.py` | Copied/implemented | Same baseline upscaling flow as `pipeline-01`. |
| 02 | `02_remove_bg.py` | Copied/implemented | Same REMBG flow as `pipeline-01`. |
| 03 | `03_depth_estimate.py` | ZoeDepth test target | Default model is `zoedepth`; uses `torch.hub`. |
| 04 | `04_mesh_generate.py` | Copied/implemented | Same Open3D point cloud and mesh generation flow as `pipeline-01`. |
| 05 | `05_export.py` | Stub | Contains TODO/design notes only. |
| 06 | `06_scale_crystal.py` | Not included | Add only if this pipeline grows into a full export workflow. |

---

## Folder Structure

```text
pipeline-02-zoedepth/
├── input/
├── output/
│   ├── upscaled/
│   ├── bg_removed/
│   ├── depth_maps/
│   ├── point_clouds/
│   ├── meshes/
│   └── exports/
├── models/
├── py_step_files/
├── utils/
├── .env
├── .env.example
├── requirements.txt
├── CLAUDE.md
├── DEPTH_DECISIONS.md
├── pipeline-guide.md
├── 01_upscale.py
├── 02_remove_bg.py
├── 03_depth_estimate.py
├── 04_mesh_generate.py
└── 05_export.py
```

---

## Stage 01 — Upscaling

**Script:** `01_upscale.py`  
**Input:** `input/`  
**Output:** `output/upscaled/{run}/`

```powershell
python 01_upscale.py
python 01_upscale.py --file image_01.jpg
python 01_upscale.py --factor 2
python 01_upscale.py --run try_02
```

Use the same Real-ESRGAN guidance as `pipeline-01`.

---

## Stage 02 — Background Removal

**Script:** `02_remove_bg.py`  
**Input:** `output/upscaled/{run}/`  
**Output:** `output/bg_removed/{run}/`

```powershell
python 02_remove_bg.py
python 02_remove_bg.py --model isnet-general-use
python 02_remove_bg.py --from-run try_01 --run try_02
```

Inspect the mask before depth estimation. Bad masks will distort ZoeDepth output
just as much as relative-depth output.

---

## Stage 03 — ZoeDepth Estimation

**Script:** `03_depth_estimate.py`  
**Input:** `output/bg_removed/{run}/`  
**Output:** `output/depth_maps/{run}/`

```powershell
python 03_depth_estimate.py --model zoedepth
python 03_depth_estimate.py --model zoedepth --profile soft_edges_feathered
python 03_depth_estimate.py --profile soft_edges_feathered --feather 50
python 03_depth_estimate.py --from-run try_02 --run try_03
```

Default model is `zoedepth`. This pipeline keeps `timm==0.9.16` so ZoeDepth can
run without breaking the newer model environment in `pipeline-01`.

Depth profile behavior is documented in `DEPTH_DECISIONS.md`.

---

## Stage 04 — Mesh Generation

**Script:** `04_mesh_generate.py`  
**Input:** `output/depth_maps/{run}/`  
**Output:** `output/point_clouds/{run}/` and `output/meshes/{run}/`

```powershell
python 04_mesh_generate.py
python 04_mesh_generate.py --z-scale 0.5 --poisson-depth 10
python 04_mesh_generate.py --from-run try_03 --run try_04
```

This stage is copied from `pipeline-01` and should be validated with ZoeDepth
output before treating the mesh results as production-quality.

---

## Stage 05 — Export

**Script:** `05_export.py`  
**Status:** Stub/TODO

The file is present as a copied design stub. Do not rely on it until it is
implemented and tested for this pipeline.

---

## Run Folder System

Every stage creates run folders such as `try_01`, `try_02`, and `try_03`. Use
`--from-run` to compare ZoeDepth output against earlier processing runs without
overwriting results.

---

## `.env` Quick Reference

```dotenv
DEVICE=cuda
UPSCALE_FACTOR=4
REMBG_MODEL=isnet-general-use
DEPTH_MODEL=zoedepth
DEPTH_ANYTHING_MODEL_SIZE=Large
DEPTH_PROFILE=standard
Z_SCALE=0.3
```

CLI arguments override `.env` values.

---

## Known Limitations

- This is a ZoeDepth isolation pipeline, not the main production pipeline.
- Keep `timm==0.9.16` unless a newer ZoeDepth-compatible version is verified locally.
- Stage 05 is not implemented.
- Stage 06 is not included.
- Web frontend support should be added only after the CLI workflow is verified.
