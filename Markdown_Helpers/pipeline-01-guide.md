<!--
File: Markdown_Helpers/pipeline-01-guide.md
Purpose: Official operator guide for pipeline-01 — Depth Anything V2 portrait-to-crystal pipeline.
Phase framework: 7 conceptual phases mapped to 6 executable stages.
-->

# pipeline-01 — Pipeline Guide

> **Crystal Clear Memories** — Portrait-to-crystal pipeline using Depth Anything V2 as the default depth model.
> Conceptual framework: 7-phase portrait-to-crystal process mapped to 6 executable stages.
> For creating new pipelines or rebuilding environments, see root `Markdown_Helpers/pipeline-setup.md`.

---

## Table of Contents

- [Conceptual Framework](#conceptual-framework)
- [Pipeline Purpose](#pipeline-purpose)
- [Quick Start](#quick-start)
- [Stage Status](#stage-status)
- [Folder Structure](#folder-structure)
- [Stage 01 — Image Preparation](#stage-01--image-preparation)
- [Stage 02 — Background Removal](#stage-02--background-removal)
- [Stage 03 — Depth Estimation and Initial Geometry](#stage-03--depth-estimation-and-initial-geometry)
- [Stage 04 — Reconstruction and 3D Asset Creation](#stage-04--reconstruction-and-3d-asset-creation)
- [Stage 05 — Artist Stage and Export](#stage-05--artist-stage-and-export)
- [Stage 06 — Crystal Size Scaling](#stage-06--crystal-size-scaling)
- [Run Folder System](#run-folder-system)
- [.env Quick Reference](#env-quick-reference)
- [Known Limitations](#known-limitations)

---

## Conceptual Framework

The full portrait-to-crystal workflow is organized into **7 conceptual phases** mapped to
**6 executable script stages**. Phases 6 and 7 are partially deferred until the business
is operational.

```
PHASE 1 — Image Preparation
    AI Upscaling + Enhancement        ← Stage 01
    Automatic Background Removal      ← Stage 02
    Manual Background Cleanup         ← Stage 02 (manual inspection step)

PHASE 2 — Geometry Creation
    Depth Estimation                  ← Stage 03
    Initial Point Cloud Generation    ← Stage 03
    Texture Projection                ← Stage 03 → carried into Stage 04

PHASE 3 — Human Reconstruction        ← Stage 04 sub-step A [STUB in pipeline-01]
    Facial Landmark Detection         [deferred to future pipeline version]
    3D Face Reconstruction            [deferred to future pipeline version]

PHASE 4 — 3D Asset Creation           ← Stage 04 sub-step B
    Textured Point Cloud
    Mesh Generation (Poisson)
    Textured Mesh

PHASE 5 — Artist Stage                ← Stage 05
    Mesh Validation, Cleanup, Export

PHASE 6 — SSLE Preparation            ← Stage 06 (crystal scaling only)
    Crystal Size Scaling              ← Stage 06
    SSLE Optimization                 [deferred — business stage]
    Laser Preview                     [deferred — business stage]

PHASE 7 — Manufacturing               [deferred — business stage]
```

**Phase 3 note:** Human and facial reconstruction runs from the **source image + depth map**,
not from the exported mesh. It feeds geometry into Phase 4 before the mesh is built.
pipeline-01 stubs this phase — geometry comes entirely from the depth map.

---

## Pipeline Purpose

`pipeline-01` is the baseline general-purpose portrait-to-crystal pipeline. It is the
default starting point and should stay compatible with current package versions.

Focus areas:
- Real-ESRGAN portrait upscaling (Phase 1)
- REMBG background removal with soft-edge masking (Phase 1)
- Depth Anything V2 depth estimation, default Large model (Phase 2)
- Open3D point cloud and Poisson mesh generation — no human reconstruction (Phase 3 stubbed, Phase 4)
- Full-size OBJ/STL/PLY export with mesh validation (Phase 5)
- Physical crystal-size scaling to standard presets (Phase 6 partial)

For ZoeDepth testing, use `pipeline-02-zoedepth` (requires older `timm` pins that conflict
with this environment).

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

| Stage | Script                 | Phase Coverage          | Status      | Notes                                                             |
| ----- | ---------------------- | ----------------------- | ----------- | ----------------------------------------------------------------- |
| 01    | `01_upscale.py`        | Phase 1a (Image Prep)   | Implemented | Real-ESRGAN 2x/4x, CUDA/CPU support                              |
| 02    | `02_remove_bg.py`      | Phase 1b (Background)   | Implemented | REMBG RGBA PNG + mask export                                      |
| 03    | `03_depth_estimate.py` | Phase 2 (Geometry)      | Implemented | Default `depth_anything_v2`; MiDaS fallback; model registry       |
| 04    | `04_mesh_generate.py`  | Phase 3+4 (Recon + 3D)  | Implemented | Phase 3 stubbed — geometry from depth only; Poisson mesh          |
| 05    | `05_export.py`         | Phase 5 (Artist/Export) | Implemented | Validate, clean, preview, report, export full-size OBJ/STL/PLY   |
| 06    | `06_scale_crystal.py`  | Phase 6 (SSLE Prep)     | Implemented | Crystal scaling only — SSLE optimization deferred                 |

---

## Folder Structure

```text
pipeline-01/
├── input/                              # Source photos for this pipeline
├── output/
│   ├── upscaled/                       # Stage 01 output
│   ├── bg_removed/                     # Stage 02 output
│   ├── depth_maps/                     # Stage 03 output
│   ├── point_clouds/                   # Stage 04 point cloud output
│   ├── meshes/                         # Stage 04 mesh output
│   └── exports/
│       ├── {run}/full_size/            # Stage 05 full-size exports
│       └── {run}/crystal_size/         # Stage 06 scaled crystal exports
├── models/
├── utils/
├── .env
├── .env.example
├── requirements.txt
├── CLAUDE.md
├── pipeline-guide.md                   # Active guide (copy of this file)
├── md_helpers/03-depth-guide.md        # Depth profiles and depth model decisions
├── 01_upscale.py
├── 02_remove_bg.py
├── 03_depth_estimate.py
├── 04_mesh_generate.py
├── 05_export.py
└── 06_scale_crystal.py
```

---

## Stage 01 — Image Preparation

**Covers:** Phase 1a — AI Upscaling, Image Enhancement
**Script:** `01_upscale.py` | **Input:** `input/` | **Output:** `output/upscaled/{run}/`

```powershell
python 01_upscale.py
python 01_upscale.py --file image_01.jpg
python 01_upscale.py --factor 2
python 01_upscale.py --tile 256          # lower if GPU runs out of memory
python 01_upscale.py --run try_02
```

| Argument             | Default             | Description                                       |
| -------------------- | ------------------- | ------------------------------------------------- |
| `--file FILENAME`    | all in `input/`     | Process one file by name                          |
| `--factor 2\|4`      | `4` (from `.env`)   | Scale multiplier                                  |
| `--model MODEL`      | `RealESRGAN_x4plus` | See model table below                             |
| `--tile PIXELS`      | `400`               | Tile size for VRAM. Lower on OOM. `0` = no tiling |
| `--device cuda\|cpu` | from `.env`         | Computation device                                |
| `--run NAME`         | auto `try_XX`       | Output subfolder name                             |

**Models:**

| Model                        | Scale | Use                                 |
| ---------------------------- | ----- | ----------------------------------- |
| `RealESRGAN_x4plus`          | 4x    | Default — real photos and portraits |
| `RealESRGAN_x2plus`          | 2x    | Already high-res source (≥2000px)   |
| `RealESRGAN_x4plus_anime_6B` | 4x    | Illustrations only — not for photos |

**Output:** `{stem}_upscaled.png` — lossless PNG, always.

---

## Stage 02 — Background Removal

**Covers:** Phase 1b — Automatic Background Removal, Manual Background Cleanup
**Script:** `02_remove_bg.py` | **Input:** `output/upscaled/{run}/` | **Output:** `output/bg_removed/{run}/`

```powershell
python 02_remove_bg.py
python 02_remove_bg.py --file image_01_upscaled.png
python 02_remove_bg.py --model u2net
python 02_remove_bg.py --no-mask
python 02_remove_bg.py --from-run try_01 --run try_02
python 02_remove_bg.py --fg-threshold 220 --bg-threshold 15 --erode-size 8
```

| Argument           | Default             | Description                                |
| ------------------ | ------------------- | ------------------------------------------ |
| `--file FILENAME`  | all in run          | Process one file                           |
| `--model MODEL`    | `isnet-general-use` | REMBG model (see below)                    |
| `--no-mask`        | off                 | Skip saving the alpha mask PNG             |
| `--fg-threshold N` | `240`               | Alpha matting foreground threshold (0–255) |
| `--bg-threshold N` | `10`                | Alpha matting background threshold (0–255) |
| `--erode-size N`   | `10`                | Erosion size in pixels at subject boundary |
| `--from-run NAME`  | latest upscaled     | Which upscaled run to read from            |
| `--run NAME`       | auto `try_XX`       | Output subfolder name                      |

**Models:**

| Model               | Quality | Use                                   |
| ------------------- | ------- | ------------------------------------- |
| `isnet-general-use` | ★★★★★   | Default — best for portraits and hair |
| `u2net`             | ★★★★    | Faster fallback                       |
| `u2netp`            | ★★★     | Lightweight — batch testing only      |
| `isnet-anime`       | ★★★★    | Illustrations                         |
| `sam`               | ★★★★★   | Highest precision — requires CUDA     |

**Output:** `{stem}_nobg.png` (RGBA) + `{stem}_mask.png` (grayscale).

Always inspect `_mask.png` before Stage 03. A binary (hard-edged) mask will create geometric
cliffs unless `soft_edges_feathered` is used in Stage 03.

---

## Stage 03 — Depth Estimation and Initial Geometry

**Covers:** Phase 2 — Depth Estimation, Initial Point Cloud, Texture Projection setup
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

| Argument                    | Default             | Description                            |
| --------------------------- | ------------------- | -------------------------------------- |
| `--file FILENAME`           | all in run          | Process one file                       |
| `--model MODEL`             | `depth_anything_v2` | Depth model (see below)                |
| `--size Small\|Base\|Large` | `Large`             | Model size — `depth_anything_v2` only  |
| `--profile PROFILE`         | `standard`          | Edge masking profile (see below)       |
| `--feather SIGMA`           | from profile        | Override Gaussian blur sigma in pixels |
| `--device cuda\|cpu`        | from `.env`         | Computation device                     |
| `--from-run NAME`           | latest bg_removed   | Which bg_removed run to read from      |
| `--run NAME`                | auto `try_XX`       | Output subfolder name                  |

**Models:**

| Model               | Type           | Notes                                                      |
| ------------------- | -------------- | ---------------------------------------------------------- |
| `depth_anything_v2` | Relative depth | Default. Best portraits. ~3–6s on RTX 3060.                |
| `midas`             | Relative depth | Reliable fallback — DPT-Large via HuggingFace              |
| `depth_pro`         | Metric depth   | Apple Depth Pro — sharp boundaries. Registry, untested.    |
| `marigold`          | Diffusion      | Highest surface detail. Slow. Registry, untested.          |
| `patchfusion`       | Tile fusion    | High-res. Registry — requires custom loader.               |
| `zoedepth`          | Metric depth   | Blocked — requires `pipeline-02-zoedepth` (timm conflict). |

**Edge Masking Profiles:**

| Profile                | Mask mode                    | Feather        | Use when                    |
| ---------------------- | ---------------------------- | -------------- | --------------------------- |
| `standard`             | Binary cut at alpha=0        | none           | Baseline comparison only    |
| `soft_edges_v1`        | Alpha as linear weight       | none           | Soft mask from Stage 02     |
| `soft_edges_feathered` | Alpha weight + Gaussian blur | `10px` default | Any mask — even binary ones |

See `md_helpers/03-depth-guide.md` for full profile reasoning and tuning notes.

**Output:** `{stem}_{model}_{profile}[_fSIGMA]_depth.png` (16-bit) + `..._preview_depth.png`
(8-bit inferno colormap). Always inspect the `_preview` before Stage 04 — nose tip must be
the brightest point.

---

## Stage 04 — Reconstruction and 3D Asset Creation

**Covers:** Phase 3 (Human Reconstruction — stubbed) + Phase 4 (Textured Point Cloud → Mesh)
**Script:** `04_mesh_generate.py` | **Input:** `output/depth_maps/{run}/`
**Output:** `output/point_clouds/{run}/` + `output/meshes/{run}/`

```powershell
python 04_mesh_generate.py
python 04_mesh_generate.py --file image_01_upscaled_nobg_depth_anything_v2_depth.png
python 04_mesh_generate.py --z-scale 0.5 --poisson-depth 10
python 04_mesh_generate.py --from-run try_03 --run try_04
```

**Phase 3 (Human Reconstruction) — STUBBED in pipeline-01.**
Geometry comes entirely from the depth map. No facial landmark detection or parametric face
reconstruction is performed. This is a known quality limitation for portrait work — human
reconstruction is planned for a future pipeline version.

**Phase 4 execution:**
1. Depth pixels → XYZ point positions (initial point cloud)
2. Project RGB from source RGBA image onto point positions (textured point cloud)
3. Estimate surface normals
4. Poisson surface reconstruction → mesh
5. Transfer color to mesh vertices (textured mesh)

Tune `Z_SCALE` conservatively — too much depth exaggeration engraves poorly.

---

## Stage 05 — Artist Stage and Export

**Covers:** Phase 5 — Artist Correction, Topology Cleanup, Mesh Validation, Export
**Script:** `05_export.py` | **Input:** `output/meshes/{run}/`
**Output:** `output/exports/{run}/full_size/`

```powershell
python 05_export.py
python 05_export.py --file image_01_mesh.obj
python 05_export.py --from-run try_04 --run export_01
python 05_export.py --smooth 4
python 05_export.py --export-format obj
python 05_export.py --export-format obj,stl,ply
```

Validates the mesh, applies a light cleanup pass, writes a report, saves a preview image, and
exports full-size mesh files. Does not scale to physical millimeters — that is Stage 06.

Inspect the exported mesh in Blender or MeshLab before Stage 06 for production-quality work.

---

## Stage 06 — Crystal Size Scaling

**Covers:** Phase 6 (partial) — Crystal Scaling
**Script:** `06_scale_crystal.py` | **Input:** `output/exports/{run}/full_size/`
**Output:** `output/exports/{run}/crystal_size/`

```powershell
python 06_scale_crystal.py
python 06_scale_crystal.py --crystal m_cube
python 06_scale_crystal.py --crystal l_cube --export-format obj
python 06_scale_crystal.py --crystal-size 100 80 50
python 06_scale_crystal.py --from-run export_01 --crystal s_cube
python 06_scale_crystal.py --list-crystals
```

**Crystal Presets (W × H × D in mm):**

| Preset    | W   | H   | D   | Notes                           |
| --------- | --- | --- | --- | ------------------------------- |
| `xs_cube` | 40  | 40  | 30  | Keychain / pendant              |
| `s_cube`  | 60  | 60  | 40  | Small desk — common starter     |
| `m_cube`  | 80  | 80  | 50  | Medium desk — most popular      |
| `l_cube`  | 100 | 100 | 60  | Large desk — portrait quality   |
| `xl_cube` | 120 | 120 | 80  | Extra large, premium gift       |
| `s_rect`  | 80  | 60  | 40  | Small landscape rectangle       |
| `m_rect`  | 100 | 80  | 50  | Medium landscape rectangle      |
| `l_rect`  | 120 | 80  | 60  | Large landscape rectangle       |
| `s_heart` | 80  | 80  | 40  | Heart shape (bounding box)      |
| `tower`   | 60  | 60  | 100 | Tall pillar / standing portrait |

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

- Phase 3 (Human Reconstruction) is **stubbed** — no facial geometry enhancement in this pipeline.
- Texture baking projects RGB from the source image directly onto depth-derived point positions.
  Quality depends on depth map accuracy, not facial geometry.
- Phase 6 SSLE optimization and laser preview are deferred until the business stage.
- Stage 05 exports should be inspected in Blender or MeshLab before Stage 06.
- ZoeDepth is blocked in this pipeline (timm 1.0 incompatibility). Use `pipeline-02-zoedepth`.
