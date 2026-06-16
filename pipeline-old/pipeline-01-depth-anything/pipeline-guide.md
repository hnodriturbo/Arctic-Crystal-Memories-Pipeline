<!--
File: pipeline-01/pipeline-guide.md
Purpose: Official operator guide for pipeline-01 — Depth Anything V2 portrait-to-crystal pipeline.
-->

# pipeline-01 — Pipeline Guide

> **Crystal Clear Memories** — Portrait-to-crystal pipeline using Depth Anything V2 as the default depth model.
> For creating new pipelines or rebuilding environments, see root `md_helpers/pipeline-setup.md`.

---

## Table of Contents

- [Pipeline Purpose](#pipeline-purpose)
- [Quick Start](#quick-start)
- [Stage Status](#stage-status)
- [Folder Structure](#folder-structure)
- [Stage 01 — Upscaling](#stage-01--upscaling)
- [Stage 02 — Background Removal](#stage-02--background-removal)
- [Stage 03 — Depth Estimation](#stage-03--depth-estimation)
- [Stage 04 — Mesh Generation](#stage-04--mesh-generation)
- [Stage 05 — Export](#stage-05--export)
- [Stage 06 — Crystal Size Scaling](#stage-06--crystal-size-scaling)
- [Run Folder System](#run-folder-system)
- [.env Quick Reference](#env-quick-reference)
- [Known Limitations](#known-limitations)

---

## Pipeline Purpose

`pipeline-01` is the main general-purpose portrait-to-crystal pipeline. It is the baseline
workflow and should stay compatible with modern package versions.

Focus areas:

- Real-ESRGAN portrait upscaling
- REMBG background removal with soft-edge masking
- Depth Anything V2 depth estimation (default) with MiDaS fallback
- Open3D point cloud and Poisson mesh generation
- Full-size OBJ/STL/PLY export and physical crystal-size scaling

Use this pipeline as the default starting point. For ZoeDepth testing, use `pipeline-02-zoedepth`
(requires older `timm` pins that conflict with this env).

---

## Quick Start

```powershell
.\.venv\Scripts\Activate.ps1
python 01_upscale.py
python 02_remove_bg.py
python 03_depth_estimate.py --profile soft_edges_feathered
python 04_mesh_generate.py
python 05_export.py
python 06_scale_crystal.py --crystal m_cube
```

---

## Stage Status

| Stage | Script                 | Status      | Notes                                                                               |
| ----- | ---------------------- | ----------- | ----------------------------------------------------------------------------------- |
| 01    | `01_upscale.py`        | Implemented | Real-ESRGAN 2x/4x, CUDA/CPU support                                                 |
| 02    | `02_remove_bg.py`      | Implemented | REMBG RGBA PNG + mask export                                                        |
| 03    | `03_depth_estimate.py` | Implemented | Default `depth_anything_v2`; MiDaS fallback; experimental model registry           |
| 04    | `04_mesh_generate.py`  | Implemented | Depth map → Open3D point cloud and Poisson mesh                                     |
| 05    | `05_export.py`         | Implemented | Validate, clean, preview, report, export full-size OBJ/STL/PLY                     |
| 06    | `06_scale_crystal.py`  | Implemented | Scale full-size exports to physical crystal mm dimensions                           |

---

## Folder Structure

```text
pipeline-01/
├── input/                         # Source photos for this pipeline
├── output/
│   ├── upscaled/                  # Stage 01 output
│   ├── bg_removed/                # Stage 02 output
│   ├── depth_maps/                # Stage 03 output
│   ├── point_clouds/              # Stage 04 point cloud output
│   ├── meshes/                    # Stage 04 mesh output
│   └── exports/                   # Stage 05/06 export output
│       ├── {run}/full_size/       # Stage 05 full-size exports
│       └── {run}/crystal_size/    # Stage 06 scaled crystal exports
├── models/
├── utils/
├── .env
├── .env.example
├── requirements.txt
├── CLAUDE.md
├── pipeline-guide.md              # This file
├── md_helpers/03-depth-guide.md   # Depth profiles and depth model decisions
├── 01_upscale.py
├── 02_remove_bg.py
├── 03_depth_estimate.py
├── 04_mesh_generate.py
├── 05_export.py
└── 06_scale_crystal.py
```

---

## Stage 01 — Upscaling

**Script:** `01_upscale.py` | **Input:** `input/` | **Output:** `output/upscaled/{run}/`

```powershell
python 01_upscale.py
python 01_upscale.py --file image_01.jpg
python 01_upscale.py --factor 2
python 01_upscale.py --tile 256          # lower if GPU runs out of memory
python 01_upscale.py --run try_02
```

| Argument             | Default             | Description                                        |
| -------------------- | ------------------- | -------------------------------------------------- |
| `--file FILENAME`    | all in `input/`     | Process one file by name                           |
| `--factor 2\|4`      | `4` (from `.env`)   | Scale multiplier                                   |
| `--model MODEL`      | `RealESRGAN_x4plus` | See model table below                              |
| `--tile PIXELS`      | `400`               | Tile size for VRAM. Lower on OOM. `0` = no tiling  |
| `--device cuda\|cpu` | from `.env`         | Computation device                                 |
| `--run NAME`         | auto `try_XX`       | Output subfolder name                              |

**Models:**

| Model                        | Scale | Use                                  |
| ---------------------------- | ----- | ------------------------------------ |
| `RealESRGAN_x4plus`          | 4x    | Default — real photos and portraits  |
| `RealESRGAN_x2plus`          | 2x    | Already high-res source (≥2000px)    |
| `RealESRGAN_x4plus_anime_6B` | 4x    | Illustrations only — not for photos  |

**Output:** `{stem}_upscaled.png` — lossless PNG, always.

---

## Stage 02 — Background Removal

**Script:** `02_remove_bg.py` | **Input:** `output/upscaled/{run}/` | **Output:** `output/bg_removed/{run}/`

```powershell
python 02_remove_bg.py
python 02_remove_bg.py --file image_01_upscaled.png
python 02_remove_bg.py --model u2net
python 02_remove_bg.py --no-mask
python 02_remove_bg.py --from-run try_01 --run try_02
python 02_remove_bg.py --fg-threshold 220 --bg-threshold 15 --erode-size 8
```

| Argument           | Default             | Description                                 |
| ------------------ | ------------------- | ------------------------------------------- |
| `--file FILENAME`  | all in run          | Process one file                            |
| `--model MODEL`    | `isnet-general-use` | REMBG model (see below)                     |
| `--no-mask`        | off                 | Skip saving the alpha mask PNG              |
| `--fg-threshold N` | `240`               | Alpha matting foreground threshold (0–255)  |
| `--bg-threshold N` | `10`                | Alpha matting background threshold (0–255)  |
| `--erode-size N`   | `10`                | Erosion size in pixels at subject boundary  |
| `--from-run NAME`  | latest upscaled     | Which upscaled run to read from             |
| `--run NAME`       | auto `try_XX`       | Output subfolder name                       |

**Models:**

| Model               | Quality  | Use                                    |
| ------------------- | -------- | -------------------------------------- |
| `isnet-general-use` | ⭐⭐⭐⭐⭐  | Default — best for portraits and hair  |
| `u2net`             | ⭐⭐⭐⭐   | Faster fallback                        |
| `u2netp`            | ⭐⭐⭐    | Lightweight — batch testing only       |
| `isnet-anime`       | ⭐⭐⭐⭐   | Illustrations                          |
| `sam`               | ⭐⭐⭐⭐⭐  | Highest precision — requires CUDA      |

**Output:** `{stem}_nobg.png` (RGBA) + `{stem}_mask.png` (grayscale).

Always inspect `_mask.png` before running Stage 03. A binary (hard-edged) mask will create
geometric cliffs unless `soft_edges_feathered` is used in Stage 03.

---

## Stage 03 — Depth Estimation

**Script:** `03_depth_estimate.py` | **Input:** `output/bg_removed/{run}/` | **Output:** `output/depth_maps/{run}/`

```powershell
python 03_depth_estimate.py
python 03_depth_estimate.py --file image_01_upscaled_nobg.png
python 03_depth_estimate.py --model depth_anything_v2 --size Large
python 03_depth_estimate.py --model midas
python 03_depth_estimate.py --profile soft_edges_feathered
python 03_depth_estimate.py --profile soft_edges_feathered --feather 50
python 03_depth_estimate.py --from-run try_02 --run try_03
```

| Argument                    | Default             | Description                             |
| --------------------------- | ------------------- | --------------------------------------- |
| `--file FILENAME`           | all in run          | Process one file                        |
| `--model MODEL`             | `depth_anything_v2` | Depth model (see below)                 |
| `--size Small\|Base\|Large` | `Large`             | Model size — `depth_anything_v2` only   |
| `--profile PROFILE`         | `standard`          | Edge masking profile (see below)        |
| `--feather SIGMA`           | from profile        | Override Gaussian blur sigma in pixels  |
| `--device cuda\|cpu`        | from `.env`         | Computation device                      |
| `--from-run NAME`           | latest bg_removed   | Which bg_removed run to read from       |
| `--run NAME`                | auto `try_XX`       | Output subfolder name                   |

**Models:**

| Model               | Type           | Notes                                                       |
| ------------------- | -------------- | ----------------------------------------------------------- |
| `depth_anything_v2` | Relative depth | Default. Best portraits. ~3–6s on RTX 3060.                 |
| `midas`             | Relative depth | Reliable fallback — DPT-Large via HuggingFace               |
| `depth_pro`         | Metric depth   | Apple Depth Pro — sharp boundaries. In registry, untested   |
| `marigold`          | Diffusion      | Highest surface detail. Slow. In registry, untested         |
| `patchfusion`       | Tile fusion    | High-res. In registry, requires custom loader               |
| `zoedepth`          | Metric depth   | Blocked — requires `pipeline-02-zoedepth` (timm conflict)  |

**Edge Masking Profiles:**

| Profile                | Mask mode                    | Feather         | Use when                     |
| ---------------------- | ---------------------------- | --------------- | ---------------------------- |
| `standard`             | Binary cut at alpha=0        | none            | Baseline comparison only     |
| `soft_edges_v1`        | Alpha as linear weight       | none            | Soft mask from Stage 02      |
| `soft_edges_feathered` | Alpha weight + Gaussian blur | `10px` default  | Any mask — even binary ones  |

See `md_helpers/03-depth-guide.md` for full profile reasoning and tuning notes.

**Output:** `{stem}_{model}_{profile}[_fSIGMA]_depth.png` (16-bit) + `..._preview_depth.png` (8-bit inferno colormap).
Always inspect the `_preview` before running Stage 04 — nose tip must be the brightest point.

---

## Stage 04 — Mesh Generation

**Script:** `04_mesh_generate.py` | **Input:** `output/depth_maps/{run}/` | **Output:** `output/point_clouds/{run}/` + `output/meshes/{run}/`

```powershell
python 04_mesh_generate.py
python 04_mesh_generate.py --file image_01_upscaled_nobg_depth_anything_v2_depth.png
python 04_mesh_generate.py --z-scale 0.5 --poisson-depth 10
python 04_mesh_generate.py --from-run try_03 --run try_04
```

Converts depth pixels into XYZ points, then uses Open3D Poisson reconstruction to build mesh geometry.
Tune `Z_SCALE` conservatively — too much depth produces poor crystal results.

---

## Stage 05 — Export

**Script:** `05_export.py` | **Input:** `output/meshes/{run}/` | **Output:** `output/exports/{run}/full_size/`

```powershell
python 05_export.py
python 05_export.py --file image_01_mesh.obj
python 05_export.py --from-run try_04 --run export_01
python 05_export.py --smooth 4
python 05_export.py --export-format obj
python 05_export.py --export-format obj,stl,ply
```

Validates the mesh, applies a light cleanup pass, writes a report, saves a preview image, and exports
full-size mesh files. Does not scale to physical millimeters — that is Stage 06.

---

## Stage 06 — Crystal Size Scaling

**Script:** `06_scale_crystal.py` | **Input:** `output/exports/{run}/full_size/` | **Output:** `output/exports/{run}/crystal_size/`

Run after Stage 05. The full-size export is never modified — this creates a separate copy scaled
to exact physical millimeter dimensions for the chosen crystal blank.

```powershell
python 06_scale_crystal.py
python 06_scale_crystal.py --crystal m_cube
python 06_scale_crystal.py --crystal l_cube --export-format obj
python 06_scale_crystal.py --crystal-size 100 80 50
python 06_scale_crystal.py --from-run export_01 --crystal s_cube
python 06_scale_crystal.py --list-crystals
```

**Crystal Presets (W × H × D in mm):**

| Preset    | W   | H   | D   | Notes                            |
| --------- | --- | --- | --- | -------------------------------- |
| `xs_cube` | 40  | 40  | 30  | Keychain / pendant               |
| `s_cube`  | 60  | 60  | 40  | Small desk — common starter      |
| `m_cube`  | 80  | 80  | 50  | Medium desk — most popular       |
| `l_cube`  | 100 | 100 | 60  | Large desk — portrait quality    |
| `xl_cube` | 120 | 120 | 80  | Extra large, premium gift        |
| `s_rect`  | 80  | 60  | 40  | Small landscape rectangle        |
| `m_rect`  | 100 | 80  | 50  | Medium landscape rectangle       |
| `l_rect`  | 120 | 80  | 60  | Large landscape rectangle        |
| `s_heart` | 80  | 80  | 40  | Heart shape (bounding box)       |
| `tower`   | 60  | 60  | 100 | Tall pillar / standing portrait  |

---

## Run Folder System

Every stage auto-creates numbered run subfolders (`try_01`, `try_02`, …).

- Old results are never overwritten
- Compare outputs across runs side by side
- Use `--from-run` to read from a specific earlier run

```powershell
# Read from try_02 bg_removed, write depth maps to try_05
python 03_depth_estimate.py --from-run try_02 --run try_05
```

---

## .env Quick Reference

```dotenv
DEVICE=cuda
UPSCALE_FACTOR=4
REMBG_MODEL=isnet-general-use
DEPTH_MODEL=depth_anything_v2
DEPTH_ANYTHING_MODEL_SIZE=Large
DEPTH_PROFILE=standard
Z_SCALE=0.3
MESH_EXPORT_FORMAT=all
CRYSTAL_PRESET=m_cube
CRYSTAL_MARGIN_MM=5.0
```

CLI arguments always override `.env` values.

---

## Known Limitations

- Stage 05 exports should be inspected in Blender or MeshLab before Stage 06.
- Stage 06 depends on valid full-size export files from Stage 05.
- ZoeDepth is blocked in this pipeline (timm 1.0 incompatibility). Use `pipeline-02-zoedepth`.
