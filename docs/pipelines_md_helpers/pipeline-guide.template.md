<!--
File: Markdown_Helpers/pipeline-guide.template.md
Purpose:
  - Master template for all pipeline-XX pipeline-guide.md files.
  - Describes the full 7-phase conceptual framework mapped to the 6 script stages.
  - Replace all bracketed placeholders before using as an official pipeline guide.
  - Do not edit the phase/stage structure without updating all active pipeline guides.
-->

# [pipeline-name] — Pipeline Guide

> **[Project Name]** — [One-sentence purpose of this pipeline.]
> Default depth model: `[model-name]`
> Conceptual framework: 7-phase portrait-to-crystal process mapped to 6 executable stages.
> Setup reference: root `Markdown_Helpers/pipeline-setup.md`

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
- [Package Reference](#package-reference)
- [.env Quick Reference](#env-quick-reference)
- [Known Limitations](#known-limitations)
- [Maintenance Rules](#maintenance-rules)

---

## Conceptual Framework

The full portrait-to-crystal workflow is organized into **7 conceptual phases**. These phases are mapped
to the **6 executable script stages** in this pipeline. Phases 6 and 7 (SSLE Preparation and
Manufacturing) are partially or fully deferred until the business is operational.

```
PHASE 1 — Image Preparation
    Image Acquisition
    Image Quality Inspection
    AI Upscaling                      ← Stage 01
    Image Enhancement                 ← Stage 01
    Automatic Background Removal      ← Stage 02
    Manual Background Cleanup         ← Stage 02 (manual step, not automated)

PHASE 2 — Geometry Creation
    Depth Estimation                  ← Stage 03
    Initial Point Cloud Generation    ← Stage 03
    Texture Projection                ← Stage 03 (color projection onto initial point cloud)

PHASE 3 — Human Reconstruction        ← Stage 04 (sub-step A — runs from image + depth, not mesh)
    Facial Landmark Detection
    3D Face / Body Reconstruction
    Reconstruction Merge with Geometry

PHASE 4 — 3D Asset Creation           ← Stage 04 (sub-step B — runs after Phase 3)
    Textured Point Cloud
    Mesh Generation
    Textured Mesh

PHASE 5 — Artist Stage                ← Stage 05
    Artist Correction
    Topology Cleanup
    Mesh Validation and Export

PHASE 6 — SSLE Preparation            ← Stage 06 (partial — crystal scaling only for now)
    SSLE Optimization                 [deferred — business stage]
    Point Density Optimization        [deferred — business stage]
    Laser Preview                     [deferred — business stage]

PHASE 7 — Manufacturing               [deferred — business stage]
    Crystal Output
```

### Flow Rationale — Human and Facial Reconstruction

Human and facial reconstruction (Phase 3) operates **on the source image and depth map**, not on
the exported mesh. This is critical: tools like MediaPipe, DECA, and face-alignment produce a
parametric face/body model directly from the 2D image and optional depth data. The output of
Phase 3 feeds into Phase 4 — either replacing or augmenting the coarse point cloud geometry from
Phase 2 before a textured mesh is generated.

The correct sub-stage order within Stage 04:
1. (Optional) Run human reconstruction from image + depth → produces refined facial geometry
2. Merge reconstruction geometry with coarse point cloud (or use reconstruction geometry directly)
3. Project texture (RGB from source image) onto the geometry
4. Run Poisson or alpha-wrapping mesh reconstruction → textured mesh

The facial reconstruction sub-step does **not** require an exported mesh as input. It is the
geometry source, not a consumer of geometry.

---

## Pipeline Purpose

`[pipeline-name]` is [describe: what depth model is being tested, what hypothesis this pipeline
validates, and when it should be used over other pipelines].

Focus areas:
- [Upscaling strategy and model]
- [Background removal model and edge handling]
- [Depth estimation model and profile rationale]
- [Mesh reconstruction strategy]
- [Human/facial reconstruction: included / stub / deferred]
- [Export formats and use case]

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

Update this block if the pipeline intentionally stops before Stage 06 (e.g., during depth model testing).

---

## Stage Status

| Stage | Script                 | Phase Coverage          | Status              | Notes                                        |
| ----- | ---------------------- | ----------------------- | ------------------- | -------------------------------------------- |
| 01    | `01_upscale.py`        | Phase 1a (Image Prep)   | [done/pending/stub] | [upscaling model and strategy]               |
| 02    | `02_remove_bg.py`      | Phase 1b (Background)   | [done/pending/stub] | [BG removal model, edge handling]            |
| 03    | `03_depth_estimate.py` | Phase 2 (Geometry)      | [done/pending/stub] | [depth model, profile, point cloud output]   |
| 04    | `04_mesh_generate.py`  | Phase 3+4 (Recon + 3D)  | [done/pending/stub] | [reconstruction: active/stub, mesh strategy] |
| 05    | `05_export.py`         | Phase 5 (Artist/Export) | [done/pending/stub] | [cleanup, formats, inspection]               |
| 06    | `06_scale_crystal.py`  | Phase 6 (SSLE Prep)     | [done/pending/stub] | [crystal preset, margin, scaling]            |

---

## Folder Structure

```text
[pipeline-name]/
├── input/                              # Source photos — JPEG, PNG
├── output/
│   ├── upscaled/                       # Stage 01 — upscaled PNGs
│   ├── bg_removed/                     # Stage 02 — RGBA PNGs + alpha masks
│   ├── depth_maps/                     # Stage 03 — 16-bit depth + preview
│   ├── point_clouds/                   # Stage 04 — PLY point clouds
│   ├── meshes/                         # Stage 04 — OBJ/PLY meshes
│   └── exports/
│       ├── {run}/full_size/            # Stage 05 — validated full-size exports
│       └── {run}/crystal_size/         # Stage 06 — scaled to crystal mm dimensions
├── models/                             # Downloaded model weights (gitignored)
├── utils/                              # Shared utilities
├── .env                                # Active configuration
├── .env.example                        # Config reference
├── requirements.txt
├── CLAUDE.md                           # AI context for this pipeline
├── pipeline-guide.md                   # This file
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
| `RealESRGAN_x4plus_anime_6B` | 4x    | Illustrations only                  |

**Output:** `{stem}_upscaled.png` — lossless PNG, always.

**Quality check before Stage 02:** Verify the upscaled image has no tiling artifacts and facial
detail is sharp. Reject if ears, hair, or eyes show ringing.

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
| `u2net`             | ★★★★    | Faster fallback                        |
| `u2netp`            | ★★★     | Lightweight — batch testing only      |
| `isnet-anime`       | ★★★★    | Illustrations                          |
| `sam`               | ★★★★★   | Highest precision — requires CUDA     |

**Output:** `{stem}_nobg.png` (RGBA) + `{stem}_mask.png` (grayscale).

**Manual cleanup note (Phase 1b):** Always inspect `_mask.png` after this stage. Use an image
editor to clean stray pixels at hair edges or transparent body parts before continuing. A binary
(hard-edged) mask will produce geometric cliff artifacts in Stage 03 unless `soft_edges_feathered`
is used.

---

## Stage 03 — Depth Estimation and Initial Geometry

**Covers:** Phase 2 — Depth Estimation, Initial Point Cloud Generation, Texture Projection
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
| `--model MODEL`             | `[model-name]`      | Depth model (see below)                |
| `--size Small\|Base\|Large` | `Large`             | Model size — `depth_anything_v2` only  |
| `--profile PROFILE`         | `standard`          | Edge masking profile (see below)       |
| `--feather SIGMA`           | from profile        | Override Gaussian blur sigma in pixels |
| `--device cuda\|cpu`        | from `.env`         | Computation device                     |
| `--from-run NAME`           | latest bg_removed   | Which bg_removed run to read from      |
| `--run NAME`                | auto `try_XX`       | Output subfolder name                  |

**Models:**

| Model               | Type           | Notes                                                      |
| ------------------- | -------------- | ---------------------------------------------------------- |
| `depth_anything_v2` | Relative depth | Default for pipeline-01. Best for portraits. Fast.         |
| `zoedepth`          | Metric depth   | pipeline-02 only — requires older timm pin                 |
| `midas`             | Relative depth | Reliable fallback — DPT-Large via HuggingFace              |
| `depth_pro`         | Metric depth   | Apple Depth Pro — sharp boundaries. Registry, untested.    |
| `marigold`          | Diffusion      | Highest surface detail. Slow. Registry, untested.          |
| `patchfusion`       | Tile fusion    | High-res. Registry — requires custom loader.               |

**Edge Masking Profiles:**

| Profile                | Mask mode                    | Feather        | Use when                    |
| ---------------------- | ---------------------------- | -------------- | --------------------------- |
| `standard`             | Binary cut at alpha=0        | none           | Baseline comparison only    |
| `soft_edges_v1`        | Alpha as linear weight       | none           | Soft mask from Stage 02     |
| `soft_edges_feathered` | Alpha weight + Gaussian blur | `10px` default | Any mask — even binary ones |

See `md_helpers/03-depth-guide.md` for full profile reasoning and tuning notes.

**Output:** `{stem}_{model}_{profile}[_fSIGMA]_depth.png` (16-bit) + `..._preview_depth.png`
(8-bit inferno colormap). Always inspect the `_preview` before Stage 04 — the nose tip must be the
brightest point in the depth map.

**Phase 2 note — Texture Projection:** Color projection from the source RGBA image onto the
initial point cloud happens inside Stage 04. The depth map produced here is the geometric
foundation for that projection.

---

## Stage 04 — Reconstruction and 3D Asset Creation

**Covers:** Phase 3 (Human Reconstruction) and Phase 4 (Textured Point Cloud → Mesh → Textured Mesh)
**Script:** `04_mesh_generate.py` | **Input:** `output/depth_maps/{run}/`
**Output:** `output/point_clouds/{run}/` + `output/meshes/{run}/`

```powershell
python 04_mesh_generate.py
python 04_mesh_generate.py --file image_01_upscaled_nobg_depth_anything_v2_depth.png
python 04_mesh_generate.py --z-scale 0.5 --poisson-depth 10
python 04_mesh_generate.py --from-run try_03 --run try_04
```

### Sub-Stage A — Human Reconstruction (Phase 3)

Runs **before** mesh generation. Uses the source image and depth map as inputs — not the mesh.

When active, this sub-stage:
1. Detects facial landmarks and estimates 3D face geometry from the 2D image + depth
2. Optionally estimates body pose / silhouette
3. Merges the reconstructed geometry with the coarse point cloud from depth estimation

When stubbed, this sub-stage is skipped and Stage 04 proceeds with only the coarse depth geometry.

**Status:** `[active / stub / deferred]`

### Sub-Stage B — 3D Asset Creation (Phase 4)

1. Projects RGB texture from the source RGBA image onto XYZ point positions (textured point cloud)
2. Runs Poisson surface reconstruction to produce a closed mesh
3. Transfers or bakes texture from point cloud onto the mesh (textured mesh)

Tune `Z_SCALE` conservatively. Too much depth exaggeration produces a caricature-like result that
engraves poorly.

**Output:** `{stem}_pointcloud.ply` + `{stem}_mesh.obj` (or `.ply`)

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

This stage validates the mesh, applies a programmable cleanup pass, generates a preview image,
writes a mesh report, and exports full-size files. It does not scale to physical millimeters —
that is Stage 06.

**Artist correction note (Phase 5):** For production-quality output, inspect the exported mesh in
Blender or MeshLab before Stage 06. Automated cleanup handles common issues (non-manifold edges,
isolated vertices, small holes) but cannot substitute for human review on facial geometry.

---

## Stage 06 — Crystal Size Scaling

**Covers:** Phase 6 (partial) — Crystal Scaling (SSLE Optimization and Laser Preview deferred)
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

**Deferred Phase 6 tasks (future business stage):**
- SSLE-specific point density optimization (points/mm³ target for the chosen laser)
- Laser preview render (simulate engraving result before burning)
- DXF export for Green Beam lasers; GLB export for UV lasers

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

## Package Reference

Recommended packages by phase. Packages already installed in the pipeline venv are marked ✓.

### Phase 1 — Image Preparation

| Package                | Purpose                                     | Notes                    |
| ---------------------- | ------------------------------------------- | ------------------------ |
| `realesrgan` ✓         | AI upscaling — Real-ESRGAN 2x/4x            | Default upscaler         |
| `rembg` ✓              | Automatic background removal                | Default BG tool          |
| `transparent-background` | Alternative BG removal — lighter          | Optional fallback        |
| `Pillow` ✓             | Image I/O, enhancement, format conversion   | Core utility             |
| `opencv-python` ✓      | Advanced filtering, morphological cleanup   | Mask cleanup             |

### Phase 2 — Geometry Creation

| Package                  | Purpose                                    | Notes                      |
| ------------------------ | ------------------------------------------ | -------------------------- |
| `transformers` ✓         | Depth Anything V2, MiDaS via HuggingFace   | Core depth inference       |
| `depth-anything-v2` ✓    | Best general-purpose relative depth        | Default depth model        |
| `open3d` ✓               | Point cloud generation, normals, Poisson   | Core 3D library            |
| `trimesh`                | Geometry utilities, mesh I/O               | Useful alongside Open3D    |
| `pytorch3d`              | Texture projection, differentiable render  | GPU-heavy — optional       |

### Phase 3 — Human Reconstruction

| Package              | Purpose                                       | Notes                                   |
| -------------------- | --------------------------------------------- | --------------------------------------- |
| `mediapipe`          | Face mesh (468 landmarks) + body pose         | Lightweight, no CUDA required           |
| `face-alignment`     | 3D facial landmark detection — 68/98 pts      | `pip install face-alignment`            |
| `insightface`        | Face analysis + 3D reconstruction             | Fast, good for portraits                |
| `gfpgan` ✓           | Face restoration — enhances facial detail     | Already installed                       |
| `smplx`              | Full body SMPL-X parametric model             | Heavy — full body only                  |
| DECA (HuggingFace)   | Detailed expression capture from single image | `flame-deca` on HF Hub                  |
| 3DDFA_V2             | 3D dense face alignment                       | `cleardusk/3DDFA_V2` on GitHub          |

**Recommended starting point for facial reconstruction:** `mediapipe` (face mesh) + `face-alignment`
(3D landmarks). Both are lightweight and work from a single portrait image without heavy model setup.

### Phase 4 — 3D Asset Creation

| Package         | Purpose                                      | Notes                        |
| --------------- | -------------------------------------------- | ---------------------------- |
| `open3d` ✓      | Textured point cloud, Poisson mesh           | Core 3D engine               |
| `trimesh`       | Mesh repair, UV generation, I/O              | Complements Open3D           |
| `xatlas`        | UV unwrapping for texture baking             | `pip install xatlas`         |
| `pymeshlab`     | Programmatic MeshLab — topology cleanup      | `pip install pymeshlab`      |
| `pytorch3d`     | Differentiable textured mesh generation      | Optional, GPU-heavy          |

### Phase 5 — Artist Stage

| Package      | Purpose                                        | Notes                        |
| ------------ | ---------------------------------------------- | ---------------------------- |
| `pymeshlab`  | Automated topology cleanup, hole filling       | Best for programmatic repair |
| `trimesh`    | Mesh validation, watertight check, simplify    | Lightweight utility          |
| `open3d` ✓   | Statistical outlier removal, geometry filter   | Already in pipeline          |

---

## Model and Dependency Notes

- Python version: `3.11`
- Default depth model: `[model-name]`
- Important dependency pins: `[list pins or state "none beyond requirements.txt"]`
- Compatibility notes: `[model-specific setup issues, e.g., timm version conflicts]`
- Human reconstruction status: `[active / stub / deferred]`

---

## `.env` Quick Reference

```dotenv
DEVICE=cuda
UPSCALE_FACTOR=4
REMBG_MODEL=isnet-general-use
DEPTH_MODEL=[model-name]
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

- `[List: incomplete stages, untested models, dependency risks, quality limitations]`
- Human reconstruction (Phase 3) is [active/stub/deferred] in this pipeline.
- Texture baking (Phase 4) currently [projects RGB from source image / not yet implemented].
- Phase 6 SSLE optimization and laser preview are deferred until the business stage.
- Stage 05 exports should be reviewed in Blender or MeshLab before Stage 06.

---

## Maintenance Rules

- Keep this guide aligned with the actual scripts and CLI arguments.
- Update `md_helpers/03-depth-guide.md` when depth models, profiles, or processing rules change.
- Do not add a local `INSTRUCTIONS.md`; this file is the pipeline's official operator guide.
- Keep reusable setup instructions in root `Markdown_Helpers/pipeline-setup.md`.
- When Stage 04 is split into 04a (reconstruction) and 04b (mesh), update the Stage Status table.
- Phase 3 (Human Reconstruction) runs from image + depth — never from the exported mesh.
