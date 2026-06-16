# pipeline-01 — Memory
<!-- Living memory for pipeline-01.
     For operating instructions, read pipeline-guide.md.
     For project context, read the root INSTRUCTIONS.md. -->

---

## Pipeline File Status

| File                   | Status  | Notes                                                                                                             |
| ---------------------- | ------- | ----------------------------------------------------------------------------------------------------------------- |
| `utils/file_utils.py`  | done    | get_input_dir, get_output_dir, build_output_path, list_input_images, STAGE_OUTPUT_DIRS                            |
| `utils/image_utils.py` | done    | load_image, save_image, save_depth_map, pil_to_numpy, get_image_info, bgr/rgb helpers                             |
| `01_upscale.py`        | done    | Real-ESRGAN 4x, argparse CLI, tqdm, model auto-download, CUDA/CPU fallback                                        |
| `02_remove_bg.py`      | done    | REMBG isnet-general-use, alpha_matting, mask export, argparse CLI, tqdm                                           |
| `03_depth_estimate.py` | done    | Depth Anything V2 / MiDaS, 16-bit PNG + inferno preview, 3 edge profiles, `--feather` sigma override, run folders |
| `04_mesh_generate.py`  | done    | Open3D point cloud and mesh generation from depth maps                                                            |
| `05_export.py`         | done    | Validate mesh, clean, export full-size OBJ/STL/PLY, preview PNG, report TXT                                      |
| `06_scale_crystal.py`  | done    | Scale to physical crystal mm, 10 presets, --crystal / --crystal-size / --list-crystals CLI. Step 6 (final).       |

---

## Last Worked On

**2026-05-30** — Root `py_step_files/` created as the universal template source from the live `pipeline-01` scripts. Stage 05 was synced from the implemented template into the live pipeline. Pipeline-local `py_step_files/` folders should not be kept.

---

## Pipeline Run Results

| Date       | Step | Input                    | Result              | Output Quality                                                                                                                                                                                                        |
| ---------- | ---- | ------------------------ | ------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2026-05-28 | 01   | `image_01.jpg` (960×960) | Success             | `image_01_upscaled.png` 3840×3840, 4x, ~4.5 min on CPU                                                                                                                                                                |
| 2026-05-28 | 02   | `image_01_upscaled.png`  | Success with issues | `_nobg.png` saved. Mask is binary black/white — alpha matting Cholesky step failed silently. Hair boundary has no soft transitions. **Not acceptable for Step 03.** User is manually reworking the mask in Photoshop. |

---

## Known Issues & Blockers

**BLOCKER — CUDA not available:**
PyTorch installed in `.venv` is CPU-only build. User is installing NVIDIA Studio Driver 610.47 and rebooting on 2026-05-28. After reboot, run:
```
.\.venv\Scripts\pip.exe install torch torchvision --index-url https://download.pytorch.org/whl/cu121
```
Verify with: `.\.venv\Scripts\python.exe -c "import torch; print(torch.cuda.is_available())"`

**QUALITY RISK — Stage 02 mask quality:**
`image_01_upscaled_mask.png` was binary black/white with no soft transitions at hair boundaries during the first test. This can create hard geometric cliffs unless depth profiles such as `soft_edges_feathered` are used or the mask is manually corrected.

**FIXED — basicsr torchvision compatibility:**
`basicsr/data/degradations.py` line 8: patched `functional_tensor` → `functional`. Applied directly to `.venv` site-packages. This fix must be reapplied if the venv is rebuilt.

---

## Key Decisions Made

- **Output always PNG (lossless)** between stages — no JPEG at any intermediate step
- **CUDA is required** — CPU fallback exists in code but is not acceptable for production. RTX 3060 Laptop GPU.
- **Alpha matting enabled** in Stage 02 (`alpha_matting=True`) for soft hair edges — but failed on first run; needs CUDA or a different approach
- **isnet-general-use** chosen as default REMBG model over u2net — better hair/edge quality for portrait use case
- **Mask must have soft semi-transparent transitions** at subject boundary before Stage 03 can produce a usable depth map. Hard binary mask = hard geometric cliffs = bad crystal.
- **Template source rule:** root `py_step_files/` is the universal source for future pipeline step scripts. Pipeline folders should not keep their own `py_step_files/` copies.

---

## Web Frontend

The `web/` sibling folder contains a Next.js 16 / React 19 / Tailwind 4 local operator UI.

**How it connects to Python:**
- Next.js Route Handlers use `child_process.spawn()` to call Python scripts directly
- Python venv path used: `pipeline-01/.venv/Scripts/python.exe`
- stdout streamed back to browser via Server-Sent Events

**Changes made to Python code for web support:**
- `utils/file_utils.py` → `build_output_path()` accepts optional `run_name` string override (avoids auto-increment when web passes a custom name)
- `01_upscale.py`, `02_remove_bg.py`, `03_depth_estimate.py` → `--run` now accepts any user-supplied string, not just auto-increment
- `03_depth_estimate.py` → MODEL_REGISTRY extended with `depth_pro`, `marigold`, `patchfusion`

**Depth models available in the web UI (Stage 03 dropdown):**

| Key                 | Model                   | Notes                                 |
| ------------------- | ----------------------- | ------------------------------------- |
| `depth_anything_v2` | Depth Anything V2 Large | Default                               |
| `depth_pro`         | Apple Depth Pro         | Sharp edges, metric depth             |
| `marigold`          | Marigold LCM            | Diffusion-based, slow, highest detail |
| `patchfusion`       | PatchFusion             | High-res tile fusion, custom loader   |

See `web/INSTRUCTIONS.md` for full frontend spec.

---

## Tech Stack in Use

| Component          | Library / Model           | Version / Notes                                            |
| ------------------ | ------------------------- | ---------------------------------------------------------- |
| Upscaling          | Real-ESRGAN               | `RealESRGAN_x4plus` — model cached at `models/realesrgan/` |
| Background removal | rembg + isnet-general-use | model cached at `~/.u2net/`                                |
| Depth estimation   | Depth Anything V2         | Implemented with profile support                          |
| Mesh generation    | Open3D (Poisson)          | Implemented                                                |
| Export             | OBJ + STL + PLY           | Stage 05 full-size export + Stage 06 crystal scaling        |
| Runtime            | Python 3.11               | `.venv` at `pipeline-01/.venv`                             |
| GPU                | NVIDIA RTX 3060 Laptop    | CUDA 12.x — PyTorch CUDA build pending reboot              |
| Env config         | python-dotenv             | `.env` at `pipeline-01/.env`                               |
