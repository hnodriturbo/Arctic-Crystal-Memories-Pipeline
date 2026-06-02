<!--
File: Markdown_Helpers/pipeline-setup.md
Purpose:
 - Canonical setup guide for creating new K9 Crystal Pipeline instances.
 - Shared by all pipelines; do not copy this file into individual pipeline folders.
-->

# Pipeline Setup Guide

This is the canonical setup guide for creating a new local K9 Crystal Pipeline.
Keep this file in `Markdown_Helpers/` at the repository root. Individual pipelines should
have their own root-level `pipeline-guide.md`, but they should not keep a copied
`pipeline-setup.md`.

---

## What a Pipeline Instance Is

Each pipeline is an isolated experiment or production workflow under the repo root:

```text
K9-Crystal-Pipeline/
├── Markdown_Helpers/
│   ├── pipeline-setup.md
│   ├── pipeline-guide.template.md
│   └── NOTES.md
├── py_step_files/
│   ├── 01_upscale.py
│   ├── 02_remove_bg.py
│   ├── 03_depth_estimate.py
│   ├── 04_mesh_generate.py
│   ├── 05_export.py
│   └── 06_scale_crystal.py
├── pipeline-01/
├── pipeline-02-zoedepth/
├── `NEW PIPELINE NAME`
└── web/
```

Each pipeline owns its own:

- Python virtual environment
- dependency pins
- `.env` and `.env.example`
- input images
- generated output
- pipeline-specific `pipeline-guide.md` (At first we use the original pipeline-guide.md and modify it as needed)
- depth decision log, when depth behavior differs or evolves

This isolation is intentional. A new depth model, package pin, export method, or
mesh strategy should not destabilize another working pipeline.

The root `py_step_files/` folder is the universal source template library for
pipeline step scripts. Do not keep a `py_step_files/` folder inside individual
pipeline folders. When creating a new pipeline, copy the root step files into
the new pipeline root, then adapt them for that pipeline's purpose.

---

## AI / Agent Checklist Before Creating a Pipeline

Before creating a new pipeline, ask or confirm these decisions:

| Question                                  | Why it matters                                                                                         |
| ----------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| What should the pipeline folder be named? | Use a clear name such as `pipeline-03-depthpro` or `pipeline-04-marigold`.                             |
| What is the pipeline's purpose?           | Benchmark, production workflow, depth-model test, mesh/export experiment, web-connected workflow, etc. |
| Which depth model is the default?         | Examples: `depth_anything_v2`, `zoedepth`, `midas`, `depth_pro`, `marigold`, `patchfusion`.            |
| Does it need isolated dependency pins?    | ZoeDepth needs `timm==0.9.16`; other models may need separate Torch, Transformers, or custom packages. |
| Which pipeline should it copy from?       | Usually copy from the most similar current pipeline, then adjust.                                      |
| Which stages should be included?          | Current full shape is stages 01 through 06, but research pipelines may stop earlier.                   |

Do not guess high-impact model or dependency decisions. If the answer is unknown,
ask the user before building the new pipeline.

---

## Standard Pipeline Folder Structure

```text
pipeline-XX-name/
├── input/                          # Always copy all images from `input_image_samples/` to each pipeline's input/ folder
├── output/
│   ├── upscaled/                   # Stage 01 png files output
│   ├── bg_removed/                 # Stage 02 png files output
│   ├── depth_maps/                 # Stage 03 png files output
│   ├── point_clouds/               # Stage 04 point cloud output
│   ├── meshes/                     # Stage 04 mesh output
│   ├── exports/                    # Stage 05 output
│   └── scaled_exports/             # Stage 06 output
├── models/
│   └── realesrgan/                 # Auto-downloaded model weights
├── utils/
│   ├── __init__.py
│   ├── file_utils.py
│   └── image_utils.py
├── .env                            # Local config, do not commit
├── .env.example                    # Safe config template
├── requirements.txt                # Accordingly to new specifications
├── CLAUDE.md                       # Optional local session memory
├── pipeline-guide.md               # Official guide for this pipeline
├── 01_upscale.py                   # Stage 01
├── 02_remove_bg.py                 # Stage 02
├── 03_depth_estimate.py            # Stage 03
├── 04_mesh_generate.py             # Stage 04
├── 05_export.py                    # Stage 05
└── 06_scale_crystal.py             # Stage 06
```

Each output copies files into their respective output folder inside this processes names output as folder.
  - `output/upscaled/try_01/` or `output/bg_removed/special_try_01/`
Each pipeline has it's own `pipeline-guide.md`
  - At first it is a copied file
  - Modified to specifications and updated

---

## Stage Overview

| Stage | Script                 | Purpose                                                    |
| ----- | ---------------------- | ---------------------------------------------------------- |
| 01    | `01_upscale.py`        | Upscale source images with Real-ESRGAN.                    |
| 02    | `02_remove_bg.py`      | Remove background and save RGBA subject plus mask.         |
| 03    | `03_depth_estimate.py` | Generate 16-bit depth maps and preview images.             |
| 04    | `04_mesh_generate.py`  | Convert depth into point cloud / mesh geometry.            |
| 05    | `05_export.py`         | Validate and export full-size OBJ/STL/PLY assets.          |
| 06    | `06_scale_crystal.py`  | Scale full-size exports to exact crystal blank dimensions. |

Not every experimental pipeline has to implement every stage immediately, but the
pipeline guide must clearly mark incomplete or stub stages. Each pipeline will always have
these 6 main python step files. They will expand and be modified and copied into each new
pipeline that is created. Sometimes pipeline will be created just for enhancing one step into
different parts if needed. That's experimental pipeline.

---

## Manual Setup — PowerShell

Run these commands from inside the new pipeline folder.


### 1. Create folders

```powershell
New-Item -ItemType Directory -Force input
New-Item -ItemType Directory -Force output\upscaled
New-Item -ItemType Directory -Force output\bg_removed
New-Item -ItemType Directory -Force output\depth_maps
New-Item -ItemType Directory -Force output\point_clouds
New-Item -ItemType Directory -Force output\meshes
New-Item -ItemType Directory -Force output\exports
New-Item -ItemType Directory -Force output\scaled_exports
New-Item -ItemType Directory -Force models\realesrgan
New-Item -ItemType Directory -Force utils
```


### 2. Create and activate the Python environment

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Python 3.11 is the default for this repo. Python 3.12+ can break ML packages used
by the pipelines.


### 3. Configure VS Code

```powershell
mkdir .vscode -Force; Set-Content .vscode\settings.json '{ "python.defaultInterpreterPath": ".venv\\Scripts\\python.exe", "python.terminal.activateEnvironment": true }'
```


### 4. Install PyTorch with CUDA support

```powershell
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
python -c "import torch; print(torch.__version__); print(torch.cuda.is_available())"
```

If CUDA prints `False`, stop and fix the local NVIDIA / PyTorch setup before judging pipeline speed or quality.


### 5. Install pipeline requirements

```powershell
pip install -r requirements.txt
pip install git+https://github.com/xinntao/Real-ESRGAN.git
```


### 6. Apply the basicsr compatibility patch

```powershell
$f = ".venv\Lib\site-packages\basicsr\data\degradations.py"
(Get-Content $f) -replace 'torchvision.transforms.functional_tensor', 'torchvision.transforms.functional' | Set-Content $f
```

Reapply this patch whenever the virtual environment is rebuilt.


### 7. Verify imports and CLI entrypoints

```powershell
python -c "import torch, PIL, numpy, cv2, rembg, transformers, timm, einops, open3d; print('All imports OK')"
python 01_upscale.py --help
python 02_remove_bg.py --help
python 03_depth_estimate.py --help
python 04_mesh_generate.py --help
python 05_export.py --help
python 06_scale_crystal.py --help
```

---

## Reusable Coding Standards

- Each stage is a standalone script and importable as a module.
- Shared logic belongs in `utils/`; do not copy helper logic between step files.
- Use `argparse` for CLI options and `.env` fallbacks for defaults.
- Print active settings at the start of each run.
- Use `snake_case` for functions and variables.
- Use `UPPER_SNAKE_CASE` for constants.
- Use clear try/except handling around file I/O and model inference.
- Save depth maps as 16-bit PNG.
- Save background removal output as RGBA PNG.
- Preserve originals and avoid overwriting previous runs.
- Keep comments professional and useful; no emojis in Python comments.

---

## Known Compatibility Notes

| Area      | Issue                                                        | Current handling                                 |
| --------- | ------------------------------------------------------------ | ------------------------------------------------ |
| Python    | Python 3.12+ can break older ML packages.                    | Use Python 3.11 for pipeline environments.       |
| PyTorch   | Default pip install may be CPU-only.                         | Install from the CUDA wheel URL first.           |
| `basicsr` | Imports `functional_tensor`, removed from newer torchvision. | Patch `degradations.py` after environment setup. |
| ZoeDepth  | Fails with `timm >= 1.0` in current testing.                 | Use an isolated pipeline with `timm==0.9.16`.    |
