<!--
File: Markdown_Helpers/pipeline-pro-setup.md
Purpose:
  - Master creation guide for building a new K9 Crystal Pipeline instance using
    the full 7-phase / 7-script professional workflow.
  - Written for Claude Code. Follow every section in order without skipping steps.
  - This file supersedes pipeline-setup.md for new pipelines that implement the
    full professional workflow including texture baking and reconstruction stubs.
  - Do not copy this file into individual pipeline folders.

When to use this file vs pipeline-setup.md:
  - pipeline-setup.md   → creating a quick research pipeline (stages 01–06, geometry only)
  - pipeline-pro-setup.md → creating a full-quality pipeline (stages 01–06 + stage 04b,
                            texture baking, reconstruction sub-stage, production path)
-->

# Pipeline Pro Setup Guide

This is the canonical creation guide for building a new professional K9 Crystal Pipeline
that implements the complete 7-phase portrait-to-crystal workflow.

**Read the entire file before creating any files or writing any code.**
The pipeline has interdependencies that will cause problems if stages are built out of order.

---

## Table of Contents

1. [The 7-Phase Framework — What You Are Building](#1-the-7-phase-framework--what-you-are-building)
2. [Pre-Creation Checklist](#2-pre-creation-checklist)
3. [Folder Structure](#3-folder-structure)
4. [PowerShell Environment Setup](#4-powershell-environment-setup)
5. [Requirements and Packages](#5-requirements-and-packages)
6. [Script Architecture Standards](#6-script-architecture-standards)
7. [Stage-by-Stage Build Specification](#7-stage-by-stage-build-specification)
8. [Utils Module Specification](#8-utils-module-specification)
9. [Configuration Files](#9-configuration-files)
10. [Quality Checkpoints](#10-quality-checkpoints)
11. [Pipeline Guide and Documentation](#11-pipeline-guide-and-documentation)
12. [Known Compatibility Issues](#12-known-compatibility-issues)
13. [Final Verification Checklist](#13-final-verification-checklist)

---

## 1. The 7-Phase Framework — What You Are Building

This pipeline implements 7 conceptual phases across 7 Python scripts. Understand this
mapping before writing a single line of code.

```
PHASE 1a — Image Preparation (Upscaling + Enhancement)
    Script: 01_upscale.py

PHASE 1b — Background Removal
    Script: 02_remove_bg.py

PHASE 2 — Geometry Creation (Depth Estimation + Initial Point Cloud)
    Script: 03_depth_estimate.py

PHASE 3 — Human Reconstruction  [Sub-stage A inside 04_mesh_generate.py]
    Sub-script logic runs BEFORE mesh generation
    Input: source RGBA image + depth map
    Output: refined face geometry merged into point cloud
    Status in new pipelines: STUB unless explicitly activated
    CRITICAL RULE: This phase runs from the IMAGE, not from the exported mesh.

PHASE 4 — 3D Asset Creation (Textured Point Cloud → Mesh → Textured Mesh)
    Script A: 04_mesh_generate.py       (point cloud + Poisson mesh + vertex colors)
    Script B: 04b_texture_bake.py       (UV unwrap + photo texture projection + export)

PHASE 5 — Artist Stage (Mesh Validation + Cleanup + Export)
    Script: 05_export.py

PHASE 6 — SSLE Preparation (Crystal Scaling + future SSLE optimization)
    Script: 06_scale_crystal.py
    NOTE: Full SSLE optimization (point density, laser preview) is deferred to
    the business stage. Implement crystal scaling only for now.

PHASE 7 — Manufacturing
    DEFERRED — handled by Cockpit3D and the SSLE machine.
    Do not implement this phase in Python.
```

### The Two Output Paths

Every pipeline produces **two export paths**:

- **Path A — Geometry Only (editing-ready):** Open3D vertex-colored PLY/OBJ. For
  Blender/MeshLab manual review and correction. This is what `04_mesh_generate.py`
  produces and `05_export.py` validates.

- **Path B — Textured Production (SSLE-ready):** UV-mapped mesh with photo texture
  baked to a texture atlas, exported as OBJ+MTL and GLB. This is what
  `04b_texture_bake.py` produces. This is the path that goes to Cockpit3D.

Both paths must be implemented. Path A is required before Path B can run.

### Why Texture Matters for Crystal Quality

The SSLE machine assigns laser power per point. Without texture, power is estimated
from geometry alone. With a texture-mapped mesh, every surface point carries its actual
photo color, and Cockpit3D samples that to assign precise power values — encoding the
portrait's shading directly into the crystal. Texture is not a visual enhancement.
It is the mechanism by which photo likeness survives into the crystal.

---

## 2. Pre-Creation Checklist

Before creating any files, confirm these decisions. Do not guess. Ask the user if any
answer is unknown.

| Decision | Why it matters |
| -------- | -------------- |
| Pipeline folder name? | Convention: `pipeline-XX-name` e.g. `pipeline-03-depthpro` |
| Pipeline purpose? | Depth model test / texture experiment / production baseline / other |
| Default depth model? | `depth_anything_v2`, `midas`, `depth_pro`, `marigold`, `patchfusion` |
| Human reconstruction active or stub? | Determines whether Phase 3 logic is built or stubbed |
| Which source pipeline to copy scripts from? | Usually `pipeline-01-depth-anything`. Copy then modify. |
| UV tool preference? | `xatlas` (default, free, Python), `rizomuv` (commercial, best quality), `mof` (free CLI) |
| Stages to include? | Full (01–06 + 04b), or stop earlier for research pipelines |
| Any special dependency pins? | ZoeDepth needs `timm==0.9.16`. Other models may need custom pins. |

Copy the answer to each question into the new pipeline's `CLAUDE.md` before writing code.

---

## 3. Folder Structure

Create exactly this structure. Do not add or rename folders without updating the
utils module and this guide.

```text
[pipeline-name]/
├── input/                              # Source photos — JPEG, PNG only
│                                       # Copy all images from input_image_samples/
├── output/
│   ├── upscaled/                       # Stage 01 output (PNG, lossless)
│   ├── bg_removed/                     # Stage 02 output (RGBA PNG + alpha mask PNG)
│   ├── depth_maps/                     # Stage 03 output (16-bit PNG + preview PNG)
│   ├── point_clouds/                   # Stage 04 output (PLY vertex-colored)
│   ├── meshes/                         # Stage 04 output (OBJ or PLY mesh)
│   │   └── {run}/
│   │       ├── geometry/               # Path A — vertex-colored geometry mesh
│   │       └── textured/               # Path B — UV-mapped textured mesh (04b output)
│   └── exports/
│       ├── {run}/full_size/            # Stage 05 — validated full-size exports
│       └── {run}/crystal_size/         # Stage 06 — scaled to crystal mm dimensions
├── models/
│   └── realesrgan/                     # Auto-downloaded Real-ESRGAN weights
├── utils/
│   ├── __init__.py
│   ├── file_utils.py                   # Path resolution, run management, directory helpers
│   └── image_utils.py                  # Image I/O, depth save/load, color conversion
├── .env                                # Active local configuration (not committed)
├── .env.example                        # Safe configuration reference
├── requirements.txt                    # All package dependencies
├── CLAUDE.md                           # AI session memory for this pipeline
├── pipeline-guide.md                   # Operator guide (copy from template, then fill)
├── md_helpers/
│   └── 03-depth-guide.md              # Depth model and profile decisions for this pipeline
├── 01_upscale.py
├── 02_remove_bg.py
├── 03_depth_estimate.py
├── 04_mesh_generate.py                 # Phase 3 stub + Phase 4 Path A
├── 04b_texture_bake.py                 # Phase 4 Path B (UV + texture projection)
├── 05_export.py
└── 06_scale_crystal.py
```

### PowerShell — Create All Folders

Run from inside the new pipeline folder:

```powershell
New-Item -ItemType Directory -Force input
New-Item -ItemType Directory -Force output\upscaled
New-Item -ItemType Directory -Force output\bg_removed
New-Item -ItemType Directory -Force output\depth_maps
New-Item -ItemType Directory -Force output\point_clouds
New-Item -ItemType Directory -Force output\meshes
New-Item -ItemType Directory -Force output\exports
New-Item -ItemType Directory -Force models\realesrgan
New-Item -ItemType Directory -Force utils
New-Item -ItemType Directory -Force md_helpers
```

---

## 4. PowerShell Environment Setup

Run every command in order. Do not skip any step. Each step has a verification.

### Step 1 — Create the Python virtual environment

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Python 3.11 is mandatory. Python 3.12+ breaks several ML packages used in this pipeline.
Verify: `python --version` must print `Python 3.11.x`.

### Step 2 — Configure VS Code interpreter

```powershell
mkdir .vscode -Force
Set-Content .vscode\settings.json '{ "python.defaultInterpreterPath": ".venv\\Scripts\\python.exe", "python.terminal.activateEnvironment": true }'
```

### Step 3 — Install PyTorch with CUDA support (do this FIRST before requirements.txt)

```powershell
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
python -c "import torch; print(torch.__version__); print('CUDA:', torch.cuda.is_available())"
```

CUDA must print `True`. If it prints `False`, stop. Fix the local NVIDIA/PyTorch setup
before continuing. CPU-only builds are too slow for production work on this pipeline.

CUDA version target: `cu124` (CUDA 12.4 — matches current Studio Driver series).
If the user's driver is older, use `cu121` instead.

### Step 4 — Install pipeline requirements

```powershell
pip install -r requirements.txt
pip install git+https://github.com/xinntao/Real-ESRGAN.git
```

### Step 5 — Apply the basicsr compatibility patch

```powershell
$f = ".venv\Lib\site-packages\basicsr\data\degradations.py"
(Get-Content $f) -replace 'torchvision.transforms.functional_tensor', 'torchvision.transforms.functional' | Set-Content $f
```

This patch must be reapplied every time the virtual environment is rebuilt.

### Step 6 — Install commercial / CLI UV tools (if applicable)

**xatlas** is installed via pip (in requirements.txt). No extra step needed.

**Ministry of Flat (free CLI UV tool):**
- Download from: https://quelsolaar.com/ministry_of_flat/
- Place the binary at `tools\mof.exe` relative to the pipeline root
- No installation required — it is a standalone executable

**RizomUV (commercial, best UV quality):**
- Purchase at: https://www.rizomuv.com/ (~€149–€259 perpetual license)
- Install per their installer. The pipeline calls it via subprocess using its CLI mode.
- Only purchase when entering production phase. xatlas is sufficient for development.

### Step 7 — Verify all imports

```powershell
python -c "import torch, PIL, numpy, cv2, rembg, transformers, timm, einops, open3d; print('Core imports OK')"
python -c "import pymeshlab, xatlas, trimesh; print('Texture pipeline imports OK')"
python -c "import mediapipe, face_alignment; print('Reconstruction imports OK')"
python 01_upscale.py --help
python 02_remove_bg.py --help
python 03_depth_estimate.py --help
python 04_mesh_generate.py --help
python 04b_texture_bake.py --help
python 05_export.py --help
python 06_scale_crystal.py --help
```

All `--help` outputs must print without error before any pipeline run is attempted.

---

## 5. Requirements and Packages

### requirements.txt — Three Configurations

Choose the configuration that matches the pipeline's purpose. Each configuration
is a complete standalone `requirements.txt`. Do not mix configs without checking
compatibility. The configurations are ordered from minimal to full.

---

#### CONFIG A — Research / Depth Testing (minimal)

Use when: creating a new pipeline to test a depth model only (stages 01–04, no texture baking).
No texture pipeline packages. No reconstruction packages. Fastest setup.

```text
# requirements.txt — CONFIG A: Research / Depth Testing
# Stages covered: 01, 02, 03, 04 (geometry only)
# Not included: texture baking (04b), facial reconstruction (phase 3)

# ── Core scientific stack ─────────────────────────────────────────────────────
numpy
scipy
Pillow
opencv-python
tqdm
python-dotenv

# ── Image upscaling ───────────────────────────────────────────────────────────
basicsr
facexlib
gfpgan
# After pip install, also run:
#   pip install git+https://github.com/xinntao/Real-ESRGAN.git

# ── Background removal ────────────────────────────────────────────────────────
rembg[gpu]

# ── Depth estimation ──────────────────────────────────────────────────────────
transformers
timm
einops
huggingface_hub

# ── 3D geometry (geometry-only path) ─────────────────────────────────────────
open3d

# ── Visualization ─────────────────────────────────────────────────────────────
matplotlib
```

**Install sequence for Config A:**
```powershell
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
pip install -r requirements.txt
pip install git+https://github.com/xinntao/Real-ESRGAN.git
# Apply basicsr patch (see Step 5 above)
```

---

#### CONFIG B — Full Professional Pipeline (recommended for new production pipelines)

Use when: building a complete pipeline with texture baking and reconstruction stubs
(all stages 01–06 + 04b, Phase 3 stubbed and ready to activate).
This is the standard config for any pipeline created from this guide.

```text
# requirements.txt — CONFIG B: Full Professional Pipeline
# Stages covered: 01, 02, 03, 04, 04b, 05, 06
# Phase 3 (reconstruction): STUBBED — packages installed, logic not active by default

# ── Core scientific stack ─────────────────────────────────────────────────────
numpy
scipy
Pillow
opencv-python
tqdm
python-dotenv

# ── Image upscaling ───────────────────────────────────────────────────────────
basicsr
facexlib
gfpgan
# After pip install, also run:
#   pip install git+https://github.com/xinntao/Real-ESRGAN.git

# ── Background removal ────────────────────────────────────────────────────────
rembg[gpu]

# ── Depth estimation ──────────────────────────────────────────────────────────
transformers
timm
einops
huggingface_hub

# ── 3D geometry and mesh ──────────────────────────────────────────────────────
open3d
trimesh
fast-simplification

# ── Texture pipeline ──────────────────────────────────────────────────────────
pymeshlab
xatlas

# ── Human / facial reconstruction (Phase 3 — stubbed by default) ─────────────
mediapipe
face-alignment

# ── Visualization and reporting ───────────────────────────────────────────────
matplotlib
plotly
```

**Install sequence for Config B:**
```powershell
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
pip install -r requirements.txt
pip install git+https://github.com/xinntao/Real-ESRGAN.git
# Apply basicsr patch (see Step 5 above)
```

---

#### CONFIG C — ZoeDepth Isolated Pipeline

Use when: the pipeline's purpose is specifically to test ZoeDepth metric depth.
ZoeDepth requires `timm==0.9.16` which conflicts with current timm versions used
by Depth Anything V2 and other models. This config must never be mixed with Config A or B.
Create a completely separate pipeline folder and virtual environment for this config.

```text
# requirements.txt — CONFIG C: ZoeDepth Isolated Pipeline
# IMPORTANT: Do NOT install in the same venv as Config A or B.
# This pin (timm==0.9.16) will break Depth Anything V2 and other models.

# ── Core scientific stack ─────────────────────────────────────────────────────
numpy
scipy
Pillow
opencv-python
tqdm
python-dotenv

# ── Image upscaling ───────────────────────────────────────────────────────────
basicsr
facexlib
gfpgan
# After pip install, also run:
#   pip install git+https://github.com/xinntao/Real-ESRGAN.git

# ── Background removal ────────────────────────────────────────────────────────
rembg[gpu]

# ── Depth estimation — ZoeDepth requires pinned timm ─────────────────────────
transformers
timm==0.9.16          # PINNED — DO NOT UPGRADE — ZoeDepth fails with timm >= 1.0
einops
huggingface_hub

# ── 3D geometry (geometry-only — texture pipeline excluded for conflict safety) ─
open3d

# ── Visualization ─────────────────────────────────────────────────────────────
matplotlib
```

**Install sequence for Config C:**
```powershell
# Create a separate venv for this pipeline — do not reuse an existing one
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
pip install -r requirements.txt
pip install git+https://github.com/xinntao/Real-ESRGAN.git
# Apply basicsr patch (see Step 5 above)
# Verify timm version: pip show timm | findstr Version
# Must print: Version: 0.9.16
```

---

### Config Comparison Summary

| Feature | Config A | Config B | Config C |
| ------- | :------: | :------: | :------: |
| Stages 01–04 (geometry) | ✓ | ✓ | ✓ |
| Stage 04b (texture baking) | — | ✓ | — |
| Stage 05–06 (export + scale) | partial | ✓ | partial |
| Phase 3 reconstruction (stub) | — | ✓ | — |
| Depth Anything V2 | ✓ | ✓ | — |
| ZoeDepth | — | — | ✓ |
| PyMeshLab + xatlas | — | ✓ | — |
| mediapipe + face-alignment | — | ✓ | — |
| Setup complexity | Low | Medium | Low |
| Recommended for | Quick depth experiments | New production pipelines | ZoeDepth testing only |

### Package Role Reference

| Package | Phase | Purpose |
| ------- | ----- | ------- |
| `realesrgan` (git) | 1a | AI upscaling 2x/4x |
| `rembg[gpu]` | 1b | Automatic background removal |
| `gfpgan` | 1a/3 | Face restoration — improves facial detail before depth |
| `transformers` | 2 | Depth Anything V2, MiDaS via HuggingFace |
| `open3d` | 4 | Vertex-colored point cloud, normals, Poisson mesh (Path A) |
| `pymeshlab` | 4b | UV parameterization, photo texture projection, atlas baking |
| `xatlas` | 4b | UV atlas generation — free Python-native default |
| `trimesh` | 4b/5 | Mesh I/O, GLB export with embedded textures |
| `fast-simplification` | 4b/5 | Mesh decimation while preserving vertex color data |
| `mediapipe` | 3 | Face mesh (468 landmarks) — lightweight, no CUDA required |
| `face_alignment` | 3 | 3D facial landmark detection (68/98 points) |
| `matplotlib` | all | Preview image generation |

### ZoeDepth-specific pins (isolated pipeline only)

If this pipeline uses ZoeDepth, pin these in requirements.txt:

```text
timm==0.9.16
# Do NOT mix this pipeline with Depth Anything V2
```

Do not use this pin in any non-ZoeDepth pipeline. It will break other models.

---

## 6. Script Architecture Standards

Every script in this pipeline must follow these rules without exception.

### Structure of every script

```python
"""
File: [script_name].py
Stage: [Stage number and name]
Phase coverage: [Phase(s) this script implements]
Input:  [what it reads and from which output folder]
Output: [what it writes and to which output folder]
"""

# ── Standard imports ──────────────────────────────────────────────────────────
import argparse
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# ── Load environment config ───────────────────────────────────────────────────
load_dotenv()

# ── Constants from .env with defaults ────────────────────────────────────────
DEVICE = os.getenv("DEVICE", "cuda")
# [other constants as needed]

# ── Utility imports ───────────────────────────────────────────────────────────
from utils.file_utils import get_input_dir, get_output_dir, build_output_path, list_input_images
from utils.image_utils import load_image, save_image

# ── Argument parsing ──────────────────────────────────────────────────────────
def parse_args():
    parser = argparse.ArgumentParser(description="[Stage description]")
    # arguments here
    return parser.parse_args()

# ── Main processing function ──────────────────────────────────────────────────
def process_[stage_name](args):
    # main logic
    pass

# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    args = parse_args()
    # print active settings summary
    print(f"[Stage name] | device={args.device} | ...")
    process_[stage_name](args)
```

### Rules — apply to every script

- **One script, one stage.** Do not implement two stages in one file.
- **argparse for every option.** Use `.env` as default fallback, CLI argument wins.
- **Print active settings** at the top of every run before processing begins.
- **Run folder system.** Every stage output goes into `output/{stage_folder}/{run}/`.
  Auto-increment: `try_01`, `try_02`, etc. Never overwrite an existing run.
  Use `--run NAME` to override the auto-increment with a custom name.
- **`--from-run NAME`** on every stage that reads from a previous stage's output.
  It must read from the specified run, not just the latest.
- **16-bit PNG** for all depth maps. Never save depth as JPEG or 8-bit PNG.
- **RGBA PNG** for all background-removed output. Never flatten to RGB before Stage 04.
- **Lossless PNG** for all intermediate images (upscaled, bg_removed). Never JPEG.
- **Never overwrite source images.** Always write to output folders.
- **`try/except` around** all model loading, file I/O, and inference calls.
  Print a clear error message and `sys.exit(1)` on failure.
- **`snake_case`** for all functions and variables.
- **`UPPER_SNAKE_CASE`** for all module-level constants.
- **No emojis in Python comments.** Comments should be short, clear, professional.
  Write comments as if explaining to yourself what the code does and why.
- **Shared logic belongs in `utils/`**, not copied between scripts.

### Run folder auto-increment example

```python
from utils.file_utils import build_output_path

# auto-increment: finds next available try_XX
out_dir = build_output_path("upscaled", run_name=args.run)

# if args.run is None → auto-increment (try_01, try_02, ...)
# if args.run is "my_test" → use "my_test" exactly
```

---

## 7. Stage-by-Stage Build Specification

Build stages in order. Each stage must pass its quality checkpoint before the next
stage is started. Do not build Stage 04 until Stage 03 has produced a verified
depth map on a real image.

---

### Stage 01 — Image Preparation (`01_upscale.py`)

**Phase coverage:** Phase 1a — AI Upscaling, Image Enhancement
**Input:** `input/` (original photos)
**Output:** `output/upscaled/{run}/`

**What it must do:**
- Load JPEG/PNG from `input/` (all files, or one file via `--file`)
- Run Real-ESRGAN upscaling at the configured factor (2x or 4x)
- Save as lossless PNG with `_upscaled` suffix
- Support `--factor 2|4`, `--model MODEL`, `--tile PIXELS`, `--device cuda|cpu`
- Print model name, factor, device, and file count before processing
- Use tqdm progress bar for multi-file runs

**What it must NOT do:**
- Save as JPEG at any point
- Modify the source file in `input/`
- Skip writing a run folder — even single-file runs must use the run folder system

**CLI reference:**
```powershell
python 01_upscale.py
python 01_upscale.py --file image_01.jpg
python 01_upscale.py --factor 2
python 01_upscale.py --tile 256
python 01_upscale.py --run baseline_test
```

**Models:**
| Model | Scale | Use |
| ----- | ----- | --- |
| `RealESRGAN_x4plus` | 4x | Default — real photos and portraits |
| `RealESRGAN_x2plus` | 2x | Already high-resolution source (≥2000px) |
| `RealESRGAN_x4plus_anime_6B` | 4x | Illustrations only — not for photos |

**Quality checkpoint:**
- Output must be exactly 2× or 4× the input resolution
- No tiling artifacts (visible grid lines at tile boundaries)
- Facial detail must be sharper than input — verify nose, eye, hair
- File must be PNG with alpha channel preserved if input had alpha

---

### Stage 02 — Background Removal (`02_remove_bg.py`)

**Phase coverage:** Phase 1b — Automatic Background Removal
**Input:** `output/upscaled/{run}/`
**Output:** `output/bg_removed/{run}/`

**What it must do:**
- Load PNG from the specified or latest upscaled run
- Run REMBG with the configured model
- Save `{stem}_nobg.png` as RGBA PNG (4 channels — required by Stage 03 and 04)
- Save `{stem}_mask.png` as grayscale PNG (alpha channel extracted separately)
- Support `--model MODEL`, `--fg-threshold N`, `--bg-threshold N`, `--erode-size N`
- Support `--no-mask` to skip mask export
- Support `--from-run NAME` and `--run NAME`

**What it must NOT do:**
- Flatten RGBA to RGB — the alpha channel is the subject mask used by all downstream stages
- Discard the mask PNG — it is required for Stage 03 quality inspection

**Models:**
| Model | Quality | Use |
| ----- | ------- | --- |
| `isnet-general-use` | ★★★★★ | Default — best for portraits and hair |
| `u2net` | ★★★★ | Faster fallback |
| `u2netp` | ★★★ | Lightweight — batch testing only |
| `sam` | ★★★★★ | Highest precision — requires CUDA |

**Quality checkpoint (manual — operator must perform this):**
- Open `_mask.png` in any image viewer
- Confirm the mask has soft semi-transparent transitions at hair boundaries
- Binary (pure black/white) masks will create geometric cliff artifacts in Stage 03
- If the mask is binary: re-run with different alpha matting settings, or manually
  soften edges in Photoshop before proceeding
- This is a human decision — do not automate past it

---

### Stage 03 — Depth Estimation and Initial Geometry (`03_depth_estimate.py`)

**Phase coverage:** Phase 2 — Depth Estimation, Initial Point Cloud preparation
**Input:** `output/bg_removed/{run}/` (`_nobg.png` files)
**Output:** `output/depth_maps/{run}/`

**What it must do:**
- Load `_nobg.png` (RGBA) from the specified or latest bg_removed run
- Run the configured depth model
- Apply the configured edge masking profile
- Save `{stem}_{model}_{profile}[_fSIGMA]_depth.png` as **16-bit PNG** — always
- Save a companion `_preview_depth.png` as 8-bit inferno colormap for human inspection
- Support `--model MODEL`, `--size Small|Base|Large` (depth_anything_v2 only)
- Support `--profile PROFILE`, `--feather SIGMA`
- Support `--from-run NAME` and `--run NAME`

**Depth models to support:**
| Model | Type | Notes |
| ----- | ---- | ----- |
| `depth_anything_v2` | Relative | Default. Best portraits. ~3–6s on RTX 3060. |
| `midas` | Relative | Reliable fallback — DPT-Large via HuggingFace |
| `depth_pro` | Metric | Apple Depth Pro — sharp edges. Registry entry, untested. |
| `marigold` | Diffusion | Highest detail. Slow. Registry entry, untested. |
| `patchfusion` | Tile fusion | High-res. Registry entry — custom loader required. |

Use a model registry dict in the script to make adding new models clean:
```python
MODEL_REGISTRY = {
    "depth_anything_v2": load_depth_anything_v2,
    "midas":             load_midas,
    "depth_pro":         load_depth_pro,    # stub until tested
    "marigold":          load_marigold,     # stub until tested
    "patchfusion":       load_patchfusion,  # stub until tested
}
```

**Edge masking profiles:**
| Profile | Mask mode | Feather | Use when |
| ------- | --------- | ------- | -------- |
| `standard` | Binary cut at alpha=0 | none | Baseline comparison only |
| `soft_edges_v1` | Alpha as linear weight | none | Soft mask from Stage 02 |
| `soft_edges_feathered` | Alpha weight + Gaussian blur | `10px` default | Any mask |

**Quality checkpoint (manual — operator must perform this):**
- Open `_preview_depth.png` in any image viewer
- The **nose tip must be the brightest (white/yellow) point** in the image
- Eye sockets must be darker than the nose
- Forehead must dome naturally (brightest at center, dimmer at edges)
- If depth is inverted (background brighter than face): the model inverted it — fix in script
- Do not proceed to Stage 04 with an incorrect depth map

---

### Stage 04 — Reconstruction and 3D Asset Creation (`04_mesh_generate.py`)

**Phase coverage:** Phase 3 (Human Reconstruction stub) + Phase 4 Path A (Textured Point Cloud → Mesh)
**Input:** `output/depth_maps/{run}/` (16-bit depth PNG) + corresponding `_nobg.png` from bg_removed
**Output:** `output/point_clouds/{run}/` + `output/meshes/{run}/geometry/`

#### Sub-stage A — Human Reconstruction (Phase 3)

This sub-stage runs BEFORE mesh generation. It reads the source RGBA image and the
depth map. It does NOT read the mesh (the mesh does not exist yet at this point).

**When STUB (default in new pipelines):**
- Skip all reconstruction logic
- Log: `"Phase 3 (Human Reconstruction): STUBBED — using depth geometry only"`
- Proceed directly to Sub-stage B

**When ACTIVE (activated via `--reconstruction mediapipe` or similar):**
- Detect facial landmarks using MediaPipe Face Mesh (468 landmarks)
- Optionally run face-alignment for 3D landmark positions (68/98 point model)
- Generate refined face geometry from landmarks
- Merge refined face geometry with the coarse point cloud from depth
- Log: `"Phase 3: reconstruction complete — X landmarks detected, geometry merged"`

The `--reconstruction` argument controls this:
```
--reconstruction none         # default — stub
--reconstruction mediapipe    # MediaPipe Face Mesh 468 landmarks
--reconstruction face_align   # face-alignment 3D landmarks
```

**Reconstruction sub-stage implementation:**

```python
def run_reconstruction_stub(rgba_image, depth_map):
    # Phase 3 is stubbed — geometry comes from depth only
    print("Phase 3 (Human Reconstruction): STUBBED")
    return None  # returning None signals to Sub-stage B to use depth geometry

def run_reconstruction_mediapipe(rgba_image, depth_map):
    import mediapipe as mp
    # detect 468 face landmarks from rgba_image
    # project landmarks onto depth surface using depth values
    # return refined face point cloud as numpy array (N, 3) with RGB colors
    pass

def run_reconstruction_face_align(rgba_image, depth_map):
    import face_alignment
    # detect 3D face landmarks (68 or 98 points)
    # return landmark geometry as numpy array
    pass

RECONSTRUCTION_REGISTRY = {
    "none":         run_reconstruction_stub,
    "mediapipe":    run_reconstruction_mediapipe,
    "face_align":   run_reconstruction_face_align,
}
```

#### Sub-stage B — 3D Asset Creation (Phase 4 Path A)

**What it must do:**
1. Load 16-bit depth PNG from Stage 03
2. Load corresponding `_nobg.png` (RGBA) — needed for color projection
3. If reconstruction returned geometry: merge it with the depth-derived point cloud
4. Project RGB from the RGBA source image onto XYZ point positions
   — result is a vertex-colored point cloud: every point has (X, Y, Z, R, G, B)
5. Estimate surface normals using Open3D
6. Run Poisson surface reconstruction to produce a closed mesh
7. Transfer vertex colors to mesh vertices
8. Save vertex-colored PLY to `output/point_clouds/{run}/`
9. Save vertex-colored OBJ (or PLY) to `output/meshes/{run}/geometry/`

**Color projection rule:**
The `_nobg.png` file has semi-transparent pixels at hair boundaries. Do NOT composite
these onto black — composite onto a neutral grey (128, 128, 128) or white background
before projecting. Otherwise hair boundaries will appear dark/black on the mesh.

```python
# Composite RGBA onto neutral grey before color sampling
bg = np.full((*rgba.shape[:2], 3), 128, dtype=np.uint8)
alpha = rgba[:, :, 3:4] / 255.0
rgb_composited = (rgba[:, :, :3] * alpha + bg * (1 - alpha)).astype(np.uint8)
```

**CLI reference:**
```powershell
python 04_mesh_generate.py
python 04_mesh_generate.py --z-scale 0.3
python 04_mesh_generate.py --poisson-depth 10
python 04_mesh_generate.py --reconstruction none
python 04_mesh_generate.py --reconstruction mediapipe
python 04_mesh_generate.py --no-color          # skip color projection
python 04_mesh_generate.py --from-run try_03 --run try_04
```

**Key parameters:**
| Argument | Default | Description |
| -------- | ------- | ----------- |
| `--z-scale N` | `0.3` (from `.env`) | Depth exaggeration factor. Too high = poor crystal. |
| `--poisson-depth N` | `10` | Poisson reconstruction depth. Higher = finer detail, slower. |
| `--reconstruction TYPE` | `none` | Phase 3 reconstruction mode (see above) |
| `--no-color` | off | Skip color projection — geometry-only output |
| `--from-run NAME` | latest depth_maps | Which depth_maps run to read from |
| `--run NAME` | auto try_XX | Output subfolder name |

**Quality checkpoint:**
- Open the PLY point cloud in MeshLab: `File > Import Mesh`
- Verify points have color (face should show skin tone gradients, not uniform grey)
- Verify nose tip protrudes — Z depth should be visible as relief
- Open the OBJ mesh in Blender or MeshLab: check for catastrophic holes or inversions
- If mesh has inverted normals (faces appear invisible from outside): fix normals in script

---

### Stage 04b — Texture Baking (`04b_texture_bake.py`)

**Phase coverage:** Phase 4 Path B — UV Unwrap + Photo Texture Projection + Production Export
**Input:** `output/meshes/{run}/geometry/` + `output/bg_removed/{run}/` (source RGBA)
**Output:** `output/meshes/{run}/textured/`

This script takes the geometry mesh from Stage 04 and produces the SSLE-ready
textured mesh. This is the production path. It runs AFTER manual mesh inspection
and editing in Blender/MeshLab (or it can run directly for automated testing).

**What it must do:**

1. **Load the geometry mesh** from Stage 04 geometry output (OBJ or PLY)
2. **UV Unwrap** — generate UV coordinates for the mesh surface
   - Default UV tool: `xatlas` (pip-installed, Python-native, zero setup)
   - Optional: `rizomuv` (subprocess call to RizomUV CLI — highest quality)
   - Optional: `mof` (subprocess call to Ministry of Flat binary — fast, free)
3. **Project source photo onto UV-mapped mesh**
   - Load `_nobg.png` composited onto neutral grey background
   - Use PyMeshLab `project_active_rasters_color_to_current_mesh()` with the source
     image as a raster and the camera matrix derived from the image dimensions
4. **Export textured mesh in two formats:**
   - `OBJ + MTL` with companion texture atlas PNG (`{stem}_textured.obj` + `.mtl` + `_atlas.png`)
   - `GLB` binary GLTF with embedded texture (`{stem}_textured.glb`)
5. **Print a quality report:** atlas resolution, texture coverage %, estimated poly count

**UV tool selection logic:**
```python
UV_TOOLS = {
    "xatlas":   uv_with_xatlas,   # default — always available via pip
    "rizomuv":  uv_with_rizomuv,  # subprocess to RizomUV CLI — requires purchase
    "mof":      uv_with_mof,      # subprocess to Ministry of Flat binary
}
```

**xatlas implementation:**
```python
import xatlas

def uv_with_xatlas(vertices, faces):
    # returns uv_coords (N, 2), vertex_mapping, face_indices
    atlas = xatlas.Atlas()
    atlas.add_mesh(vertices, faces)
    atlas.generate(xatlas.PackOptions(), xatlas.ChartOptions())
    vmapping, indices, uvs = atlas[0]
    return uvs, vmapping, indices
```

**PyMeshLab photo projection:**
```python
import pymeshlab

def project_photo_to_uv_mesh(mesh_path, photo_path, output_path, atlas_size=4096):
    ms = pymeshlab.MeshSet()
    ms.load_new_mesh(str(mesh_path))
    # load the source photo as a raster
    ms.load_new_raster(str(photo_path))
    # project raster color onto mesh surface
    ms.apply_filter("project_active_rasters_color_to_current_mesh",
                    texturesize=atlas_size,
                    pushpull=True)
    ms.save_current_mesh(str(output_path))
```

**texture atlas resolution guidance:**
- 3840×3840 source → use `4096` atlas (safe, fast)
- For maximum portrait fidelity: `8192` (slower, larger file)
- Test `4096` first. Only increase if facial detail is lost in the atlas.

**GLB export via trimesh:**
```python
import trimesh

def export_glb(mesh_path, texture_path, output_path):
    mesh = trimesh.load(str(mesh_path))
    # attach texture to mesh material
    # export as binary GLTF with embedded texture
    mesh.export(str(output_path))
```

**CLI reference:**
```powershell
python 04b_texture_bake.py
python 04b_texture_bake.py --uv-tool xatlas
python 04b_texture_bake.py --uv-tool rizomuv
python 04b_texture_bake.py --atlas-size 8192
python 04b_texture_bake.py --no-glb           # skip GLB export
python 04b_texture_bake.py --from-run try_04 --from-bg-run try_02 --run bake_01
```

**Quality checkpoint:**
- Open the OBJ in Blender: `File > Import > Wavefront OBJ`
- Switch to Material Preview mode (keyboard: `Z`, then `Material Preview`)
- The face texture must be visible and correctly projected — not stretched, not mirrored
- Skin tone gradients from the original photo must be visible on the mesh
- Hair boundary must not show black fringing (check the composite-to-grey step)
- Open the GLB in Windows 3D Viewer or online at: https://3dviewer.net/
- This is the file that goes to Cockpit3D — if it looks wrong here, it will look wrong in the crystal

---

### Stage 05 — Artist Stage and Export (`05_export.py`)

**Phase coverage:** Phase 5 — Artist Correction, Topology Cleanup, Mesh Validation, Export
**Input:** `output/meshes/{run}/geometry/` (Path A) and/or `output/meshes/{run}/textured/` (Path B)
**Output:** `output/exports/{run}/full_size/`

**What it must do:**
- Detect whether a textured subfolder exists in the mesh run
- If textured mesh exists: export both geometry-only and textured versions
- Validate the mesh: check for non-manifold edges, degenerate faces, isolated vertices
- Apply light automated cleanup: remove isolated components below threshold, basic hole fill
- Generate a mesh quality report: face count, vertex count, surface area, bounding box, issues found
- Save a preview render PNG of the mesh (use matplotlib or Open3D offscreen renderer)
- Export full-size files in configured formats: OBJ, STL, PLY
- For the textured version: export as OBJ+MTL and GLB
- Apply `--smooth N` passes of Laplacian smoothing if requested (default: 0 — do not smooth unless asked)
- Support `--export-format obj|stl|ply|all`

**Smoothing rule:** Do NOT apply smoothing by default. Smoothing is a destructive operation
that loses facial detail. Only apply when the user explicitly requests it via `--smooth N`.

**Decimation (via fast-simplification):**
- Support `--decimate N` to reduce face count to N faces while preserving vertex colors
- Default: no decimation (preserve full resolution for Cockpit3D import)
- Typical useful target: 500k–1M faces for manual editing, 2M–4M for production

**CLI reference:**
```powershell
python 05_export.py
python 05_export.py --smooth 2
python 05_export.py --decimate 1000000
python 05_export.py --export-format obj,stl,ply
python 05_export.py --from-run try_04 --run export_01
```

**Quality checkpoint:**
- Read the mesh report file — check face count is reasonable (500k–6M for portrait)
- Open the exported OBJ in Blender and verify no catastrophic geometry artifacts
- Inspect the preview PNG — portrait features should be recognizable
- Only proceed to Stage 06 if this checkpoint passes

---

### Stage 06 — Crystal Size Scaling (`06_scale_crystal.py`)

**Phase coverage:** Phase 6 (partial) — Crystal Scaling
**Input:** `output/exports/{run}/full_size/`
**Output:** `output/exports/{run}/crystal_size/`

**What it must do:**
- Apply a uniform scale and translation to fit the mesh inside the chosen crystal blank dimensions
- Preserve vertex colors, UV coordinates, and texture references — none of these are affected by scaling
- Support crystal presets by name (`--crystal m_cube`) and custom dimensions (`--crystal-size W H D`)
- Never modify the full-size export — always write a new copy to the crystal_size subfolder
- Support `--list-crystals` to print all available presets

**Crystal presets (W × H × D in mm):**

| Preset | W | H | D | Notes |
| ------ | - | - | - | ----- |
| `xs_cube` | 40 | 40 | 30 | Keychain / pendant |
| `s_cube` | 60 | 60 | 40 | Small desk — common starter |
| `m_cube` | 80 | 80 | 50 | Medium desk — most popular |
| `l_cube` | 100 | 100 | 60 | Large desk — portrait quality |
| `xl_cube` | 120 | 120 | 80 | Extra large, premium gift |
| `s_rect` | 80 | 60 | 40 | Small landscape rectangle |
| `m_rect` | 100 | 80 | 50 | Medium landscape rectangle |
| `l_rect` | 120 | 80 | 60 | Large landscape rectangle |
| `s_heart` | 80 | 80 | 40 | Heart shape (bounding box) |
| `tower` | 60 | 60 | 100 | Tall pillar / standing portrait |

**Margin:** Apply `CRYSTAL_MARGIN_MM` (default 5.0mm) of clearance on all sides so the
mesh does not intersect the crystal surface.

**CLI reference:**
```powershell
python 06_scale_crystal.py --crystal m_cube
python 06_scale_crystal.py --crystal-size 100 80 50
python 06_scale_crystal.py --list-crystals
python 06_scale_crystal.py --from-run export_01
```

---

## 8. Utils Module Specification

### `utils/__init__.py`

Empty file. Required for Python to treat `utils/` as a package.

### `utils/file_utils.py`

Must implement:

```python
# STAGE_OUTPUT_DIRS maps stage key names to output folder names
STAGE_OUTPUT_DIRS = {
    "upscaled":     "upscaled",
    "bg_removed":   "bg_removed",
    "depth_maps":   "depth_maps",
    "point_clouds": "point_clouds",
    "meshes":       "meshes",
    "exports":      "exports",
}

def get_input_dir() -> Path:
    # Returns Path("input") relative to script cwd

def get_output_dir(stage_key: str) -> Path:
    # Returns output/{STAGE_OUTPUT_DIRS[stage_key]}

def build_output_path(stage_key: str, run_name: str | None = None) -> Path:
    # If run_name is None: auto-increment (try_01, try_02, ...)
    # If run_name is a string: use it exactly
    # Creates the directory if it does not exist
    # Returns the full Path object

def get_latest_run(stage_key: str) -> Path | None:
    # Returns the most recently modified run subfolder under the stage output dir
    # Returns None if no runs exist yet

def get_run(stage_key: str, run_name: str) -> Path:
    # Returns the exact run path, raises FileNotFoundError if it does not exist

def list_input_images(directory: Path) -> list[Path]:
    # Returns sorted list of JPEG and PNG files in directory
    # Raises FileNotFoundError if directory does not exist or is empty
```

### `utils/image_utils.py`

Must implement:

```python
def load_image(path: Path) -> PIL.Image.Image:
    # Load any image format, return PIL Image

def load_rgba(path: Path) -> PIL.Image.Image:
    # Load as RGBA — convert if needed. Required for _nobg.png inputs.

def save_image(image: PIL.Image.Image, path: Path) -> None:
    # Save lossless PNG always (ignore extension if saving intermediate)

def save_depth_map(depth: np.ndarray, path: Path) -> None:
    # Save as 16-bit PNG. Normalize to 0–65535 range.
    # Accepts float32 or uint16 input.

def load_depth_map(path: Path) -> np.ndarray:
    # Load 16-bit PNG, return float32 array normalized to 0.0–1.0

def save_preview_depth(depth: np.ndarray, path: Path) -> None:
    # Save 8-bit inferno colormap preview

def composite_rgba_on_grey(rgba: np.ndarray, grey: int = 128) -> np.ndarray:
    # Composite RGBA onto a flat grey background
    # Returns uint8 RGB array (H, W, 3)
    # Used before color projection to avoid black-fringing at alpha boundaries

def pil_to_numpy(image: PIL.Image.Image) -> np.ndarray:
    # PIL Image → uint8 numpy array (H, W, C)

def numpy_to_pil(array: np.ndarray) -> PIL.Image.Image:
    # uint8 numpy array → PIL Image

def get_image_info(path: Path) -> dict:
    # Returns {width, height, mode, file_size_mb}

def bgr_to_rgb(array: np.ndarray) -> np.ndarray:
    # Convert OpenCV BGR array to RGB

def rgb_to_bgr(array: np.ndarray) -> np.ndarray:
    # Convert RGB array to OpenCV BGR
```

---

## 9. Configuration Files

### `.env` — Active configuration

```dotenv
# Device
DEVICE=cuda

# Stage 01 — Upscaling
UPSCALE_FACTOR=4
UPSCALE_MODEL=RealESRGAN_x4plus
UPSCALE_TILE=400

# Stage 02 — Background removal
REMBG_MODEL=isnet-general-use
REMBG_FG_THRESHOLD=240
REMBG_BG_THRESHOLD=10
REMBG_ERODE_SIZE=10

# Stage 03 — Depth estimation
DEPTH_MODEL=depth_anything_v2
DEPTH_ANYTHING_MODEL_SIZE=Large
DEPTH_PROFILE=standard

# Stage 04 — Mesh generation
Z_SCALE=0.3
POISSON_DEPTH=10
RECONSTRUCTION_MODE=none

# Stage 04b — Texture baking
UV_TOOL=xatlas
TEXTURE_ATLAS_SIZE=4096

# Stage 05 — Export
MESH_EXPORT_FORMAT=all
MESH_SMOOTH_PASSES=0

# Stage 06 — Crystal scaling
CRYSTAL_PRESET=m_cube
CRYSTAL_MARGIN_MM=5.0
```

### `.env.example`

Same as `.env` but with all secret or local-only values replaced by placeholders.
For this pipeline there are no secrets, so `.env.example` is identical to `.env`.
Commit `.env.example`. Never commit `.env`.

### `CLAUDE.md` — AI session memory

The `CLAUDE.md` inside each pipeline is the AI's working memory for that pipeline.
It should always contain:

```markdown
# [pipeline-name] — Memory

## Pipeline File Status

| File | Status | Notes |
| ---- | ------ | ----- |
| utils/file_utils.py  | [done/pending] | [summary] |
| utils/image_utils.py | [done/pending] | [summary] |
| 01_upscale.py        | [done/pending] | [summary] |
| 02_remove_bg.py      | [done/pending] | [summary] |
| 03_depth_estimate.py | [done/pending] | [summary] |
| 04_mesh_generate.py  | [done/pending] | [summary] |
| 04b_texture_bake.py  | [done/pending] | [summary] |
| 05_export.py         | [done/pending] | [summary] |
| 06_scale_crystal.py  | [done/pending] | [summary] |

## Pipeline Purpose

[One paragraph: what this pipeline is testing, what makes it different]

## Reconstruction Status

Phase 3 Human Reconstruction: [STUBBED / mediapipe / face_align]

## Known Issues

[Any active issues, blockers, or quality concerns]

## Last Run Results

| Date | Stage | Input | Result | Notes |
| ---- | ----- | ----- | ------ | ----- |
```

---

## 10. Quality Checkpoints

Every checkpoint marked **[MANUAL]** requires a human to look at the output.
Do not automate past a manual checkpoint. Log the result in `CLAUDE.md`.

| After Stage | Checkpoint | Type | Pass condition |
| ----------- | ---------- | ---- | -------------- |
| 01 | Upscaled image resolution = N× source | Automated | `output_width == input_width * factor` |
| 01 | No tiling grid artifacts | **[MANUAL]** | Open image, zoom on hair/face — no grid lines |
| 02 | RGBA channel preserved (4 channels) | Automated | `PIL.Image.open().mode == "RGBA"` |
| 02 | Mask has soft transitions | **[MANUAL]** | Open `_mask.png` — no hard black/white binary edges at hair |
| 03 | Depth is 16-bit PNG | Automated | `PIL.Image.open().mode == "I;16"` |
| 03 | Nose tip is brightest point | **[MANUAL]** | Open `_preview_depth.png` — white/yellow at nose |
| 04 | Point cloud has vertex colors | Automated | Open3D `has_colors()` returns True |
| 04 | Mesh has no inverted normals | **[MANUAL]** | Open PLY in MeshLab — face should be visible from front |
| 04b | Texture atlas correctly projected | **[MANUAL]** | Open OBJ in Blender, switch to Material Preview |
| 04b | No black fringing at hair | **[MANUAL]** | Check hair/subject boundary in material preview |
| 05 | Mesh report generated | Automated | Report TXT file exists and has non-zero face count |
| 05 | No catastrophic geometry | **[MANUAL]** | Open OBJ in Blender — face is recognizable |
| 06 | Output fits within crystal preset dimensions | Automated | Bounding box ≤ (W-margin) × (H-margin) × (D-margin) mm |

---

## 11. Pipeline Guide and Documentation

### Creating the pipeline-guide.md

1. Copy `Markdown_Helpers/pipeline-guide.template.md` into the new pipeline root as `pipeline-guide.md`
2. Fill in every `[bracketed placeholder]` — do not leave any unfilled
3. Update the Stage Status table to reflect actual implementation status
4. Add the new pipeline to the `Current Pipeline Chapters` section of root `INSTRUCTIONS.md`

### Creating the depth guide

Create `md_helpers/03-depth-guide.md` with:
- The depth model chosen and why
- The profile chosen and why
- Any tuning notes from early runs (feather sigma adjustments, Z scale decisions)
- A comparison table if multiple depth models were tested

### Required documentation entries in INSTRUCTIONS.md

After the pipeline is created, add an entry in section 19 (Current Pipeline Chapters):

```markdown
## [pipeline-name] — [Pipeline Description]

`[pipeline-name]` is [purpose and testing hypothesis].

Important notes:
- Default depth model: [model-name]
- Phase 3 Human Reconstruction: [STUBBED / active with mediapipe / active with face_align]
- UV tool: [xatlas / rizomuv / mof]
- [any compatibility pins or special notes]
```

---

## 12. Known Compatibility Issues

Resolve these before running, not during debugging.

| Area | Issue | Fix |
| ---- | ----- | --- |
| Python version | 3.12+ breaks older ML packages | Use `py -3.11 -m venv .venv` always |
| PyTorch | Default pip install is CPU-only | Install from CUDA wheel URL first (Step 3) |
| `basicsr` | Imports `functional_tensor` removed in newer torchvision | Apply degradations.py patch (Step 5) |
| ZoeDepth | Fails with `timm >= 1.0` | Isolated pipeline only with `timm==0.9.16` pin |
| `rembg[gpu]` | Requires CUDA for alpha matting | CUDA must be working before Stage 02 runs well |
| `mediapipe` | May conflict with older numpy | Install after numpy; test with `import mediapipe` |
| `pymeshlab` | GPL license | Acceptable for internal research and production use |
| `xatlas` | Poor UV packing for organic shapes | Sufficient for development; upgrade to RizomUV for production |
| Open3D | `write_triangle_mesh` PLY does not always preserve UV | Export to OBJ for textured meshes, PLY for geometry-only |
| PyTorch3D | Not in requirements.txt by default | Heavy install — add only if differentiable rendering is needed |

---

## 13. Final Verification Checklist

Before marking the pipeline as ready for first test run, confirm every item:

**Environment:**
- [ ] Python version is 3.11.x (`python --version`)
- [ ] CUDA is available (`torch.cuda.is_available()` returns `True`)
- [ ] basicsr patch applied
- [ ] All imports pass (Step 7 verification commands)
- [ ] All `--help` outputs print without error

**Files:**
- [ ] All 9 script files exist (01 through 06, plus 04b, utils/file_utils.py, utils/image_utils.py)
- [ ] `utils/__init__.py` exists (empty)
- [ ] `.env` and `.env.example` exist and are filled in
- [ ] `CLAUDE.md` exists and has all sections populated
- [ ] `pipeline-guide.md` exists with all placeholders filled
- [ ] `md_helpers/03-depth-guide.md` exists

**Folder structure:**
- [ ] All output subfolders exist
- [ ] `input/` contains at least one test image (copied from `input_image_samples/`)
- [ ] `models/realesrgan/` exists (weights will auto-download on first run)

**Documentation:**
- [ ] New pipeline added to `INSTRUCTIONS.md` section 19
- [ ] Stage Status table in `pipeline-guide.md` is accurate

**First run protocol:**
Run Stage 01 on a single test image first. Verify the output. Then run Stage 02 on that
output. Do not run a full pipeline pass until each individual stage has been verified.

```powershell
python 01_upscale.py --file your_test_image.jpg --run test_01
# → verify output manually, then:
python 02_remove_bg.py --from-run test_01 --run test_01
# → inspect mask manually, then:
python 03_depth_estimate.py --profile soft_edges_feathered --from-run test_01 --run test_01
# → inspect depth preview manually, then:
python 04_mesh_generate.py --from-run test_01 --run test_01
# → inspect PLY in MeshLab, then:
python 04b_texture_bake.py --from-run test_01 --run test_01
# → inspect textured OBJ in Blender, then:
python 05_export.py --from-run test_01 --run test_01
python 06_scale_crystal.py --crystal m_cube --from-run test_01
```

Only after all stages produce verified output on the test image should batch runs begin.

---

## Reference — Output File Naming Convention

All output files follow a consistent naming pattern so any stage can find the output
of a previous stage without hardcoded paths.

```
Stage 01: {stem}_upscaled.png
Stage 02: {stem}_upscaled_nobg.png
          {stem}_upscaled_mask.png
Stage 03: {stem}_upscaled_nobg_{model}_{profile}[_f{sigma}]_depth.png
          {stem}_upscaled_nobg_{model}_{profile}_preview_depth.png
Stage 04: {stem}_pointcloud.ply
          output/meshes/{run}/geometry/{stem}_mesh.obj (or .ply)
Stage 04b: output/meshes/{run}/textured/{stem}_textured.obj
           output/meshes/{run}/textured/{stem}_textured.mtl
           output/meshes/{run}/textured/{stem}_atlas.png
           output/meshes/{run}/textured/{stem}_textured.glb
Stage 05: output/exports/{run}/full_size/{stem}_export.obj (+ .stl, .ply as configured)
          output/exports/{run}/full_size/{stem}_report.txt
          output/exports/{run}/full_size/{stem}_preview.png
Stage 06: output/exports/{run}/crystal_size/{stem}_{crystal_preset}.obj (+ other formats)
```

The `{stem}` is the original source filename without extension, carried through all stages.
This makes it possible to trace any output file back to its original source image.
