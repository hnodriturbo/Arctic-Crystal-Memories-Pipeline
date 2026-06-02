# pipeline-03-pro — Memory
<!-- Updated: 2026-05-31 -->

---

## Pipeline File Status

| File                    | Status   | Notes |
| ----------------------- | -------- | ----- |
| `utils/__init__.py`     | done     | Empty package init |
| `utils/file_utils.py`   | done     | Same stage keys as pipeline-02; meshes/{run}/geometry/ handled in scripts |
| `utils/image_utils.py`  | done     | Added composite_rgba_on_grey, load_depth_map, save_preview_depth, load_rgba |
| `01_prepare.py`         | done     | BG removal at native res + resize to 1800px. No upscaling. |
| `02_depth_estimate.py`  | done     | Depth Anything V2 default. No ZoeDepth, no timm pin. MiDaS as fallback. |
| `03_mesh_generate.py`   | done     | Vertex color projection (composite-on-grey). Phase 3 stubbed. Outputs to geometry/ |
| `04b_texture_bake.py`   | done     | xatlas UV unwrap + barycentric photo projection. OBJ+MTL+atlas. GLB via trimesh. |
| `05_export.py`          | done     | Full implementation: validate, cleanup, decimate option, report, export |
| `06_scale_crystal.py`   | done     | 10 crystal presets. Scale + center + lift to Z=0. |

---

## Pipeline Purpose

`pipeline-03-pro` is the production-quality portrait-to-crystal pipeline built on the
architecture validated in `pipeline-02-zoedepth`. Key differences from pipeline-02:

- **No upscaling.** Upscaling produces 157M+ vertices (OOM on 16GB RAM). Depth models
  resize input internally to ~384-518px regardless of input size. 1800px is the correct
  working resolution.
- **Vertex color projection** in step 03 (new). Every point carries (X, Y, Z, R, G, B)
  sampled from the source RGBA composited on neutral grey.
- **Texture baking** in step 04b (new). UV unwrap + photo projection + OBJ+MTL+GLB export.
- **Full export step** in step 05 (not a stub). Validation, cleanup, decimation, report.
- **Crystal scaling** in step 06. 10 presets, mm-accurate output for Cockpit3D import.
- **Depth Anything V2 Large** as the primary depth model. No ZoeDepth, no timm pin.
- **Phase 3 Human Reconstruction**: STUBBED. Wired with reconstruction registry, raises
  NotImplementedError if activated. Packages installed (mediapipe, face-alignment).

---

## Reconstruction Status

Phase 3 Human Reconstruction: **STUBBED**
- `run_reconstruction_stub()` logs and returns None
- `run_reconstruction_mediapipe()` raises NotImplementedError
- `run_reconstruction_face_align()` raises NotImplementedError
- Activate via: `python 03_mesh_generate.py --reconstruction mediapipe`

---

## Resolution and Memory Constraints

1800px is NOT a quality limit — it is the highest-information resolution the depth model
can use. Depth Anything V2 internally resizes to ~384-518px before inference. Pixels beyond
that are never seen by the model; upscaling only adds interpolated vertices that carry no
additional depth information, causing OOM with zero quality gain.

Full production mesh quality is controlled by POISSON_DEPTH and MESH_VOXEL_SIZE:

| POISSON_DEPTH | MESH_VOXEL_SIZE | Approx triangles | RAM  | Use for        |
| ------------- | --------------- | ---------------- | ---- | -------------- |
| 9             | 0.002           | ~100K-300K       | Low  | Quick drafts   |
| 10            | 0.002           | ~300K-800K       | OK   | Review quality |
| 11            | 0.001           | ~1M-3M           | OK   | Production     |
| 12            | 0.001           | ~3M-8M           | ~12GB| Maximum        |

**Keep PREPARE_LONG_EDGE=1800. Do not increase without testing.**
**Default is POISSON_DEPTH=11, MESH_VOXEL_SIZE=0.001 for production quality.**

---

## Known Issues & Notes

- `04b_texture_bake.py` uses a pure Python barycentric rasterizer. For large meshes
  or atlas sizes > 4096, this will be slow. Consider PyMeshLab's built-in raster
  projection as an alternative (see pro-setup.md section on PyMeshLab).
- `fast-simplification` must be installed for decimation in step 05. It wraps VTK.
- GLB export in step 04b requires `trimesh`. If trimesh is not installed, GLB is skipped
  with a warning (non-fatal).
- `mediapipe` may conflict with older numpy. Install after numpy, verify with `import mediapipe`.
- basicsr patch must be applied if Real-ESRGAN is later added. This pipeline does not
  include Real-ESRGAN — no patch needed for the current scripts.
- ZoeDepth is deliberately excluded. If ZoeDepth is needed, use pipeline-02-zoedepth.

---

## Last Run Results

| Date | Stage | Input | Result | Notes |
| ---- | ----- | ----- | ------ | ----- |
| —    | —     | —     | Pipeline created, no runs yet | |

---

## First Run Protocol

```powershell
# Create and activate venv (Python 3.11 mandatory)
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install PyTorch with CUDA first
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124

# Install requirements
pip install -r requirements.txt

# Copy a test image to input/
# Then run each stage individually and inspect output before proceeding

python 01_prepare.py --file your_test_image.jpg --run test_01
# Inspect mask PNG in output/prepared/test_01/

python 02_depth_estimate.py --from-run test_01 --run test_01
# Inspect _preview.png — nose should be brightest

python 03_mesh_generate.py --from-run test_01 --prepared-run test_01 --run test_01
# Open PLY in MeshLab — check normals and vertex colors

python 04b_texture_bake.py --from-run test_01 --from-prepared-run test_01 --run test_01
# Open OBJ in Blender, switch to Material Preview

python 05_export.py --from-run test_01 --run test_01
# Read _report.txt

python 06_scale_crystal.py --crystal m_cube --from-run test_01
# Import crystal-sized OBJ into Cockpit3D
```

---

## Documentation Rules (for Claude)

### pipeline-info.md
Located at `md_helpers/pipeline-info.md`. When the user asks an informational question
about the pipeline (file sizes, model behavior, dependency behavior, stage I/O, design
decisions), write the answer into this file in a clear Q&A section with a date header.
Do this in addition to answering inline.

### pipeline-code-changes.md
Located at `md_helpers/pipeline-code-changes.md`. Every time code is changed in any
pipeline script or utils file, append an entry to this file following the existing format:
- Date + file name as section header (add to Table of Contents too)
- Full function if changed (or full block if not a function)
- One-paragraph explanation of WHY the change was made
Do this automatically — the user should never need to ask.

### .gitignore note
3D output files (.ply, .stl, .glb, .gltf, .fbx) are gitignored at the repo root.
`.obj` is already covered. Never commit generated mesh output to git.
