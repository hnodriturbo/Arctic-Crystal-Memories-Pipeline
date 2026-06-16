# Pipeline-03-Pro — Operator and Developer Guide

**Purpose of this document:**
This is the single authoritative reference for running `pipeline-03-pro`, understanding every
decision the code makes, knowing exactly when to intervene manually, and — critically — how to
activate the professional stubs that are wired but dormant. Read it end to end once before
touching anything. Refer back to individual sections as you work.

---

## Table of Contents

1. [What This Pipeline Is](#1-what-this-pipeline-is)
2. [Data Flow — End to End](#2-data-flow--end-to-end)
3. [Environment Setup](#3-environment-setup)
4. [Stage 01 — Prepare](#4-stage-01--prepare)
5. [Stage 02 — Depth Estimation](#5-stage-02--depth-estimation)
6. [Stage 03 — Mesh Generation and Color Projection](#6-stage-03--mesh-generation-and-color-projection)
7. [Stage 04b — Texture Baking](#7-stage-04b--texture-baking)
8. [Stage 05 — Export and Validation](#8-stage-05--export-and-validation)
9. [Stage 06 — Crystal Scaling](#9-stage-06--crystal-scaling)
10. [The Stub System — What It Is and How to Activate It](#10-the-stub-system--what-it-is-and-how-to-activate-it)
11. [Implementing Phase 3 — Human Facial Reconstruction](#11-implementing-phase-3--human-facial-reconstruction)
12. [Upgrading UV Quality — From xatlas to RizomUV](#12-upgrading-uv-quality--from-xatlas-to-rizomuv)
13. [Upgrading Texture Projection — PyMeshLab Raster Method](#13-upgrading-texture-projection--pymeshlab-raster-method)
14. [Depth Model Selection and Profile Tuning](#14-depth-model-selection-and-profile-tuning)
15. [Quality Checkpoints — What to Look For](#15-quality-checkpoints--what-to-look-for)
16. [Tuning Reference — Every Knob Explained](#16-tuning-reference--every-knob-explained)
17. [Cockpit3D Handoff](#17-cockpit3d-handoff)
18. [The Professional Path — Stage-by-Stage Upgrade Plan](#18-the-professional-path--stage-by-stage-upgrade-plan)

---

## 1. What This Pipeline Is

`pipeline-03-pro` converts a portrait photograph into a production-ready 3D mesh for
K9 crystal laser sub-surface engraving (SSLE). The output is a crystal-scaled 3D file
that is imported into Cockpit3D, which assigns laser power per point and drives the
SSLE machine.

The pipeline has **6 active scripts** and **2 stub systems** that are wired but waiting
for implementation. The pipeline produces real, usable output at every stage right now.
The stubs are Phase 3 (human facial reconstruction) and two UV tool upgrades (RizomUV,
Ministry of Flat). Activating them improves output quality but is not required to produce
crystal-ready files today.

**The two output paths:**

- **Path A — Geometry only:** Vertex-colored OBJ/PLY from step 03. For Blender/MeshLab
  manual review and editing. Step 05 validates and exports this path.

- **Path B — Textured production:** UV-mapped mesh with photo texture atlas from step 04b.
  OBJ+MTL+atlas PNG and GLB. This is the path that goes to Cockpit3D. Texture encodes
  photo likeness into laser power — without it, the SSLE machine works from geometry alone.

---

## 2. Data Flow — End to End

```
input/portrait.jpg
        |
        v
[ 01_prepare.py ]
  - rembg at native resolution (e.g. 5121x7678)
  - resize RGBA to 1800px long edge (e.g. 1201x1800)
  - saves: output/prepared/{run}/portrait_prepared.png       (RGBA)
  - saves: output/prepared/{run}/portrait_prepared_mask.png  (grayscale)
        |
        v  [MANUAL: inspect mask — hair edges soft? background gone?]
        |
[ 02_depth_estimate.py ]
  - loads: portrait_prepared.png (RGBA)
  - runs: Depth Anything V2 Large on RGB channel
  - applies: alpha mask profile (standard / soft_edges_feathered)
  - saves: output/depth_maps/{run}/portrait_prepared_depth_anything_v2_standard_depth.png  (16-bit)
  - saves: ...preview.png  (8-bit inferno colormap)
        |
        v  [MANUAL: inspect preview — nose tip brightest? forehead domes naturally?]
        |
[ 03_mesh_generate.py ]
  - loads: 16-bit depth PNG + portrait_prepared.png (RGBA)
  - builds: XYZ point cloud with RGB sampled from RGBA composited on grey
  - [Phase 3 stub runs here — currently logs and passes through]
  - runs: Poisson surface reconstruction (depth=11)
  - saves: output/point_clouds/{run}/..._pointcloud.ply         (vertex-colored)
  - saves: output/meshes/{run}/geometry/..._mesh.obj             (Path A — geometry)
  - saves: output/meshes/{run}/geometry/..._mesh.ply
        |
        v  [MANUAL: open PLY in MeshLab — normals correct? vertex colors visible?]
        |
[ 04b_texture_bake.py ]                         <- Path B starts here
  - loads: geometry OBJ + portrait_prepared.png (RGBA)
  - runs: xatlas UV unwrap
  - projects: source photo onto UV atlas via barycentric sampling
  - saves: output/meshes/{run}/textured/..._textured.obj
  - saves: output/meshes/{run}/textured/..._textured.mtl
  - saves: output/meshes/{run}/textured/..._atlas.png
  - saves: output/meshes/{run}/textured/..._textured.glb
        |
        v  [MANUAL: open OBJ in Blender Material Preview — texture on face correct?]
        |
[ 05_export.py ]
  - loads: geometry OBJ from geometry/
  - validates: watertight, orientable, face count
  - cleans: removes isolated floaters, degenerate faces
  - saves: output/exports/{run}/full_size/..._export.obj (.stl, .ply)
  - saves: output/exports/{run}/full_size/..._report.txt
        |
        v  [MANUAL: read report — face count reasonable? watertight?]
        |
[ 06_scale_crystal.py ]
  - loads: full_size OBJ
  - scales: to fit chosen crystal preset (e.g. m_cube = 80x80x50mm) with 5mm margin
  - centers: at origin, lifts Z=0 to bottom
  - saves: output/exports/{run}/crystal_size/..._{preset}.obj
        |
        v
  COCKPIT3D IMPORT -> laser point cloud -> SSLE machine -> K9 crystal
```

---

## 3. Environment Setup

**Python 3.11 is mandatory.** Python 3.12+ breaks several ML packages.

```powershell
# Navigate to the pipeline folder
cd D:\Hnodri\Repos\K9-Crystal-Pipeline\pipeline-03-pro

# Create virtual environment
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1

# Verify Python version
python --version   # must print Python 3.11.x

# Install PyTorch with CUDA FIRST — always before requirements.txt
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124

# Verify CUDA is available — must print True before continuing
python -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0))"

# Install pipeline requirements
pip install -r requirements.txt

# Configure VS Code to use this venv
mkdir .vscode -Force
Set-Content .vscode\settings.json '{ "python.defaultInterpreterPath": ".venv\\Scripts\\python.exe" }'
```

**Verify all imports pass:**
```powershell
python -c "import torch, PIL, numpy, cv2, rembg, transformers, timm, einops, open3d; print('Core OK')"
python -c "import pymeshlab, xatlas, trimesh; print('Texture pipeline OK')"
python -c "import mediapipe, face_alignment; print('Reconstruction packages OK')"
```

**Verify all scripts respond to --help:**
```powershell
python 01_prepare.py --help
python 02_depth_estimate.py --help
python 03_mesh_generate.py --help
python 04b_texture_bake.py --help
python 05_export.py --help
python 06_scale_crystal.py --help
```

---

## 4. Stage 01 — Prepare

**Script:** `01_prepare.py`
**Input:** `input/` — raw JPEG or PNG photographs
**Output:** `output/prepared/{run}/`

### What it does

1. Loads the source image at **native resolution** — no resize before background removal.
   Native resolution matters here: rembg needs maximum pixels to trace hair, fur, and
   soft clothing edges accurately. A 5121×7678 image gives rembg ~39M pixels to work with.

2. Runs `rembg` with alpha matting to produce an RGBA PNG where transparent pixels are
   the removed background. Alpha matting (vs binary masking) creates a soft gradient at
   subject edges — this is critical for hair. Hard-edge masks create geometric cliff
   artifacts in the depth map and mesh.

3. Resizes the RGBA result to 1800px on the long edge using Lanczos resampling. This is
   the working resolution for all downstream stages. The short side is calculated from the
   exact input ratio — no cropping, no padding.

4. Saves the alpha channel separately as a grayscale mask PNG for visual inspection.

### Running it

```powershell
# All images in input/
python 01_prepare.py

# Single file
python 01_prepare.py --file human_one_person.jpg

# Explicit run name
python 01_prepare.py --file human_one_person.jpg --run one_person_v1

# Larger working resolution (costs more RAM in mesh step)
python 01_prepare.py --target-long-edge 2400

# Different rembg model
python 01_prepare.py --model u2net
```

### Rembg model selection

| Model               | Quality           | Speed            | Use when             |
| ------------------- | ----------------- | ---------------- | -------------------- |
| `isnet-general-use` | Best — hair/fur   | Slow             | Default — portraits  |
| `u2net`             | Good              | Medium           | General subjects     |
| `u2netp`            | Lower             | Fast             | Batch testing only   |
| `sam`               | Highest precision | Slow, needs CUDA | Fine-detail subjects |

### What to inspect

Open `_prepared_mask.png` in any image viewer. This is the single most important
quality gate in the pipeline. Everything downstream inherits mask errors.

**Pass:** Soft semi-transparent transitions at hair. Subject interior is pure white.
Background is pure black. Fine hair strands are individually preserved.

**Fail — re-run with adjustments:**
- Hard binary edges at hair: increase `--erode-size` to 15 or 20, or try `sam` model
- Holes inside subject (missed skin): lower `--bg-threshold` to 5
- Background bleeding into subject: raise `--fg-threshold` to 250
- Missing hair tips: `--fg-threshold 230 --bg-threshold 5 --erode-size 15`

**Manual fix option:** If rembg produces an imperfect mask, open the RGBA PNG in
Photoshop, use the Refine Edge tool on the mask, and save back as PNG with alpha.
The downstream stages will use whatever alpha channel is in the PNG — they do not
care how it was produced.

---

## 5. Stage 02 — Depth Estimation

**Script:** `02_depth_estimate.py`
**Input:** `output/prepared/{run}/` — RGBA prepared PNGs
**Output:** `output/depth_maps/{run}/`

### What it does

1. Loads the RGBA prepared image. Separates RGB (for the depth model) and alpha (for masking).
2. Runs the depth model. Depth Anything V2 Large internally resizes to ~518px before inference.
   The raw output is an inverse disparity map — values are higher where objects are closer.
3. Bilinear upsamples the model output back to the original image resolution.
4. Normalizes to 0.0–1.0 where 1.0 = closest to camera.
5. Applies the selected edge masking profile.
6. Saves as **16-bit PNG** (65536 depth levels). Never 8-bit — 8-bit creates Z-staircase
   artifacts in the mesh that are visible in the crystal.
7. Saves an 8-bit inferno colormap preview for human inspection.

### Running it

```powershell
# Default — Depth Anything V2 Large, standard profile
python 02_depth_estimate.py

# Feathered edges — recommended for portraits with hair
python 02_depth_estimate.py --profile soft_edges_feathered

# Wider feather zone
python 02_depth_estimate.py --profile soft_edges_feathered --feather 20

# Read from a specific prepared run
python 02_depth_estimate.py --from-run one_person_v1 --run one_person_v1

# MiDaS fallback (if DAv2 gives bad results on a specific image)
python 02_depth_estimate.py --model midas
```

### Edge masking profiles

The alpha mask from step 01 is applied to the depth map after inference. How it is applied
controls the quality of the boundary between subject and background in the final mesh.

**`standard`** — Binary cut. Every pixel where alpha=0 is set to depth=0. Creates a hard
geometric wall at the subject boundary. Use only for baseline comparison. Not recommended
for portraits — the hard cut creates a ledge artifact around the silhouette.

**`soft_edges_v1`** — The alpha channel value (0–255) is used as a linear weight on the
depth. Pixels that are 50% transparent get 50% of their depth value. The boundary fades
gradually. Better for hair but still limited to the actual alpha gradient width.

**`soft_edges_feathered`** — Like `soft_edges_v1` but with a Gaussian blur applied to
the alpha weight before multiplication. Sigma=10 is the default; use 15–25 for portraits
with complex hair or flyaways. This is the recommended profile for production.

### What to inspect

Open the `_preview.png` in any viewer. The colormap is inferno: white/yellow = close,
dark purple/black = far.

**Pass conditions:**
- Nose tip is the single brightest (white) point on the face
- Eye sockets are slightly darker than the nose
- Forehead domes — bright at center, dimmer at edges
- Ears are darker than the face (they are further from the camera on a portrait)
- Background is pure black (zeroed out by the alpha mask)
- No sudden depth discontinuities inside the face (these create ridges in the mesh)

**Fail conditions and fixes:**
- Depth is inverted (background bright, face dark): the model output has the wrong polarity.
  This occasionally happens with MiDaS. The script handles DAv2 correctly; if using MiDaS
  and it inverts, edit `estimate_depth()` and add `depth_norm = 1.0 - depth_norm` before
  the mask step.
- Forehead is flat or sunken: the depth model failed to capture facial relief. Try
  `--profile soft_edges_feathered` and inspect again. If still flat, the source image
  lighting may not provide enough depth cues — try a different image or manual correction.
- Ears are same depth as face: normal for front-facing portraits. Not an error.

**Manual correction:** Open the 16-bit `_depth.png` in Photoshop as a 16-bit greyscale
document. Paint corrections with a white brush (value 65535) to bring areas forward, or
black (value 0) to push back. Use a soft round brush. Save as 16-bit PNG. The mesh step
will use whatever is in the depth file — manual corrections are normal and expected.

---

## 6. Stage 03 — Mesh Generation and Color Projection

**Script:** `03_mesh_generate.py`
**Input:** `output/depth_maps/{run}/` + `output/prepared/{run}/`
**Output:** `output/point_clouds/{run}/` + `output/meshes/{run}/geometry/`

### What it does

**Stage A — Depth to point cloud with vertex colors:**

Each pixel in the depth map becomes one XYZ point. The coordinate system is:
- X: normalized to [-1, +1] left to right
- Y: normalized to [-1, +1] bottom to top (flipped from image convention)
- Z: depth_value × Z_SCALE (controlled by `--z-scale`)

Background pixels (alpha < 128) are excluded. The remaining foreground pixels each get
an RGB color sampled from the prepared RGBA image. But before sampling, the RGBA is
composited onto neutral grey (128, 128, 128) background using the alpha channel as weight:

```
rgb_out = rgb_src * (alpha/255) + 128 * (1 - alpha/255)
```

This composite step is critical. Without it, semi-transparent pixels at hair edges
would sample into transparent (black) regions, creating a dark fringe around the
subject in the vertex colors and texture atlas. Grey is used instead of white or
black because it is the least visually disruptive neutral tone.

**Phase 3 reconstruction hook** (currently stubbed — see section 10):
After building the point cloud, the reconstruction function is called with the RGBA
image and depth map. Currently it logs "STUBBED" and returns None. When implemented,
it injects refined facial geometry (from MediaPipe or face-alignment landmarks) into
the point cloud before normal estimation.

**Stage B — Poisson surface reconstruction:**

Open3D estimates surface normals for each point (KNN=30 search), orients them
consistently toward a virtual camera at (0, 0, 2), then runs Poisson reconstruction.

Poisson reconstruction fills the continuous surface that best fits the oriented point
cloud. The `depth` parameter controls the octree resolution — each increment roughly
doubles the triangle count. After reconstruction, the lowest-density boundary triangles
(Poisson fringe at convex hull) are trimmed with a 1% quantile threshold.

Two Laplacian smoothing passes reduce Poisson surface noise without erasing facial features.

### Running it

```powershell
# Default — production settings (Poisson depth=11, voxel=0.001)
python 03_mesh_generate.py

# Draft run — fast, lower quality
python 03_mesh_generate.py --poisson-depth 9

# Maximum quality (slow, ~12GB RAM)
python 03_mesh_generate.py --poisson-depth 12

# Specify which runs to read from
python 03_mesh_generate.py --from-run one_person_v1 --prepared-run one_person_v1 --run one_person_v1

# Geometry only — skip color projection
python 03_mesh_generate.py --no-color

# Export OBJ only (faster than all)
python 03_mesh_generate.py --export-format obj
```

### Poisson depth and voxel size guide

The voxel downsample step reduces the point cloud before reconstruction to save memory
and speed up Poisson. Smaller voxels = more points retained = denser mesh.

| POISSON_DEPTH | MESH_VOXEL_SIZE | Approx triangles | Time on RTX 3060 | RAM   |
| ------------- | --------------- | ---------------- | ---------------- | ----- |
| 9             | 0.002           | ~100K–300K       | ~30s             | Low   |
| 10            | 0.002           | ~300K–800K       | ~90s             | OK    |
| 11            | 0.001           | ~1M–3M           | ~4–8 min         | OK    |
| 12            | 0.001           | ~3M–8M           | ~20–40 min       | ~12GB |

Z_SCALE controls the depth exaggeration — how pronounced the 3D relief is relative to
the XY dimensions. Start at 0.3. For taller, more dramatic engraving: 0.5–0.7. For
shallower, wider crystals: 0.15–0.25. This must be tested against the actual crystal
size in Cockpit3D — what looks right in 3D may be too deep or too shallow for the
laser's Z range.

### What to inspect

**Point cloud (PLY):** Open in MeshLab (`File > Import Mesh`). Switch to `Render > Color > Per Vertex`.
- Face should show natural skin tone gradients — not uniform grey
- Nose should visibly protrude in Z when you rotate the view
- Hair region should show dark-to-grey gradation (not pure black — that would mean the
  composite-on-grey step failed or the alpha was binary)

**Mesh (OBJ/PLY):** Open in MeshLab or Blender.
- Front-facing: normals point toward you. If faces are invisible from the front
  (inside-out mesh), the normal orientation failed. Fix: in the script, change the
  camera location in `orient_normals_towards_camera_location([0.0, 0.0, 2.0])` — try
  negative Z or a different position depending on your coordinate system.
- Mesh should be a continuous surface with no major holes inside the face region.
  Holes at the edges/silhouette are normal and expected from Poisson on an open surface.

---

## 7. Stage 04b — Texture Baking

**Script:** `04b_texture_bake.py`
**Input:** `output/meshes/{run}/geometry/` + `output/prepared/{run}/`
**Output:** `output/meshes/{run}/textured/`

### What it does

This is Path B — the production path. It takes the geometry mesh from step 03 and
produces an SSLE-ready textured mesh that encodes the actual photo colors onto every
surface point.

**Step 1 — UV unwrap:**
Generates a UV atlas for the mesh — a flat 2D layout of the 3D surface. The default
tool is xatlas, which is fast, free, and Python-native. It produces a reasonable UV
layout automatically but is not optimal for organic portrait shapes. See section 12 for
upgrading to RizomUV.

**Step 2 — Photo projection:**
For each pixel in the UV atlas, the script traces back to the 3D position, maps that
position to the original photo, and samples the color. The mapping uses barycentric
coordinates within each UV triangle.

The source photo is the `_prepared.png` composited on grey (same grey composite as
step 03 — consistent color handling throughout).

**Step 3 — Export:**
- `_textured.obj` + `_textured.mtl`: OBJ with material referencing the atlas texture
- `_atlas.png`: the 4096×4096 (or configured size) texture atlas
- `_textured.glb`: binary GLTF with embedded texture, for Cockpit3D and web viewers

### Running it

```powershell
# Default — xatlas UV, 4096 atlas
python 04b_texture_bake.py

# Larger atlas for more detail
python 04b_texture_bake.py --atlas-size 8192

# Skip GLB if trimesh has issues
python 04b_texture_bake.py --no-glb

# Specify runs
python 04b_texture_bake.py --from-run one_person_v1 --from-prepared-run one_person_v1 --run one_person_v1
```

### Atlas size guidance

| Atlas size | File size | Detail level | Use when             |
| ---------- | --------- | ------------ | -------------------- |
| 2048       | ~3–8MB    | Low          | Quick test only      |
| 4096       | ~12–30MB  | Good         | Default production   |
| 8192       | ~50–120MB | Maximum      | High-detail portrait |

For a portrait crystal, 4096 is sufficient. The crystal engraving process itself is the
resolution bottleneck — the SSLE machine's point spacing is the limit, not the atlas.
Use 8192 only if you see blurring of fine facial features (eyelashes, pores) in the
crystal output and confirm the atlas is the bottleneck, not the mesh or depth map.

### What to inspect

Open the `_textured.obj` in Blender:
1. `File > Import > Wavefront OBJ`
2. Press `Z` then select `Material Preview`
3. The portrait photo should be mapped to the face surface

**Pass:**
- Skin tone gradients from the original photo are visible on the mesh
- Eyes, nose, mouth position correctly
- Hair shows natural color, not black fringing
- No obvious UV seams visible across the face (seams on the back/sides are acceptable)

**Fail — black fringing at hair:** The grey composite step did not run or the alpha mask
is binary with hard edges. Go back to step 01 and re-run with better alpha matting
settings, or manually soften the mask in Photoshop.

**Fail — stretched or distorted texture:** xatlas produced poor UV charts for this mesh
topology. See section 12 — upgrade to RizomUV for this subject.

**Fail — overall texture looks dark or desaturated:** The photo may have been loaded
incorrectly (BGR vs RGB channel order). Check `composite_rgba_on_grey()` in `image_utils.py`
and verify it reads channels in RGB order.

---

## 8. Stage 05 — Export and Validation

**Script:** `05_export.py`
**Input:** `output/meshes/{run}/geometry/`
**Output:** `output/exports/{run}/full_size/`

### What it does

1. Loads the geometry mesh
2. Validates: checks `is_watertight()`, `is_orientable()`, counts vertices and triangles
3. Removes isolated floating components below a size threshold
4. Removes degenerate triangles, duplicated geometry, non-manifold edges
5. Optionally applies Laplacian smoothing (`--smooth N` passes, default 0)
6. Optionally decimates face count (`--decimate N`, default disabled)
7. Writes a plain-text validation report
8. Exports in the configured formats (OBJ, STL, PLY, or all)

### Smoothing and decimation

**Do not smooth by default.** Laplacian smoothing is a destructive, irreversible
operation. It rounds sharp features — which in a portrait means softening the nose tip,
eye socket edges, and lip definition. These are exactly the features that matter for
crystal quality. Only apply smoothing if the mesh has visible Poisson ripple artifacts
that do not go away with a higher Poisson depth setting.

If you must smooth: 1–2 passes maximum. Each pass moves every vertex toward the
average of its neighbours. After 5+ passes a portrait looks like it is made of clay.

**Decimation** is useful when the mesh needs to be sent to Blender or MeshLab for
manual editing — a 5M-triangle mesh is slow to manipulate in 3D software. Decimate
to 500K–1M for editing, then export at full resolution for Cockpit3D.

```powershell
# Default — no smoothing, no decimation, all formats
python 05_export.py

# Decimate to 1M triangles for Blender editing
python 05_export.py --decimate 1000000

# 1 smooth pass only (use sparingly)
python 05_export.py --smooth 1

# OBJ only
python 05_export.py --export-format obj
```

### Reading the report

The `_report.txt` contains:
```
Vertex count:    2,341,809
Triangle count:  4,683,618
Watertight:      NO — has open edges
Orientable:      YES
Bounding box:    2.0234 x 3.0112 x 0.4231  (unit scale)
```

**Watertight: NO** is normal and expected for a portrait mesh generated from a single
depth view. Watertight means the mesh is a completely closed surface with no boundary
edges. A portrait mesh always has an open boundary at the edges and back — it is
literally an open shell. This does not affect Cockpit3D import or crystal quality.

**Orientable: NO** is a problem. Non-orientable means there are faces with inconsistent
winding (some pointing inward, some outward). Open the mesh in MeshLab: `Filters >
Normals, Curvatures and Orientation > Re-Orient all faces coherently`. Then re-run step 05.

---

## 9. Stage 06 — Crystal Scaling

**Script:** `06_scale_crystal.py`
**Input:** `output/exports/{run}/full_size/`
**Output:** `output/exports/{run}/crystal_size/`

### What it does

Applies a uniform scale to fit the mesh inside the chosen crystal blank with a margin
clearance on all sides. Centers the mesh horizontally, then lifts it so Z=0 is the bottom
face of the crystal. The mesh is positioned exactly where it will appear inside the crystal.

### Crystal presets

```powershell
# List all presets
python 06_scale_crystal.py --list-crystals
```

| Preset    | W×H×D (mm) | Best for                          |
| --------- | ---------- | --------------------------------- |
| `xs_cube` | 40×40×30   | Keychain, pendant                 |
| `s_cube`  | 60×60×40   | Small desk display                |
| `m_cube`  | 80×80×50   | Medium desk — most popular        |
| `l_cube`  | 100×100×60 | Large desk, best portrait quality |
| `xl_cube` | 120×120×80 | Premium gift                      |
| `s_rect`  | 80×60×40   | Landscape format                  |
| `m_rect`  | 100×80×50  | Landscape, medium                 |
| `l_rect`  | 120×80×60  | Landscape, large                  |
| `s_heart` | 80×80×40   | Heart shape (bounding box)        |
| `tower`   | 60×60×100  | Tall portrait pillar              |

```powershell
# Use a preset
python 06_scale_crystal.py --crystal m_cube

# Custom dimensions
python 06_scale_crystal.py --crystal-size 90 70 45

# Tighter margin (default is 5mm per side)
python 06_scale_crystal.py --crystal m_cube --margin 3.0
```

The margin prevents the mesh from intersecting the crystal surface. The SSLE machine
cannot engrave too close to the surface — laser refraction near the glass boundary causes
distortion. 5mm is the minimum safe margin for most machines. Check your specific
machine's specifications.

---

## 10. The Stub System — What It Is and How to Activate It

### What a stub is

A stub is a function that is wired into the pipeline's execution path but does nothing
useful yet. The stub exists so that:
1. The pipeline runs successfully today without the feature
2. The interface contract (inputs, outputs, return values) is defined before implementation
3. You can activate and test a feature incrementally without restructuring the code

In `03_mesh_generate.py`, three reconstruction functions are defined:

```python
RECONSTRUCTION_REGISTRY = {
    "none":         run_reconstruction_stub,     # <-- active default
    "mediapipe":    run_reconstruction_mediapipe, # <-- raises NotImplementedError
    "face_align":   run_reconstruction_face_align, # <-- raises NotImplementedError
}
```

The active function is selected by the `--reconstruction` argument. Calling
`python 03_mesh_generate.py --reconstruction mediapipe` currently raises a
`NotImplementedError`. Implementing the feature means replacing that error with
working code.

In `04b_texture_bake.py`, two UV tool functions are stubs:

```python
UV_TOOLS = {
    "xatlas":  uv_with_xatlas,   # <-- active default, fully implemented
    "rizomuv": uv_with_rizomuv,  # <-- raises NotImplementedError
    "mof":     uv_with_mof,      # <-- raises NotImplementedError
}
```

### The contract each stub must honour

**Reconstruction functions** receive:
- `rgba_image`: `np.ndarray` shape (H, W, 4) uint8 — the full prepared RGBA image
- `depth_map`: `np.ndarray` shape (H, W) float32, values 0.0–1.0 — the normalized depth

They must return one of:
- `None` — no reconstruction geometry; pipeline uses depth-only point cloud
- `np.ndarray` shape (N, 6) float64 — array of (X, Y, Z, R, G, B) points to merge with
  the depth-derived point cloud before normal estimation. XYZ must be in the same
  coordinate space as the depth point cloud (unit-scale, [-1,+1]).

**UV tool functions** receive:
- `vertices`: `np.ndarray` shape (V, 3) float32 — 3D vertex positions
- `faces`: `np.ndarray` shape (F, 3) int32 — face indices

They must return:
- `uvs`: `np.ndarray` shape (N, 2) float32 — UV coordinates (N can differ from V)
- `vmapping`: `np.ndarray` shape (N,) — original vertex indices for each UV vertex
- `indices`: `np.ndarray` shape (F, 3) — face indices into the UV vertex set

---

## 11. Implementing Phase 3 — Human Facial Reconstruction

Phase 3 is the most impactful professional upgrade. The current pipeline builds 3D
geometry entirely from a single-view depth estimate. Depth Anything V2 is excellent
but it has no knowledge of human anatomy — it produces a smooth generic face shape.
Facial reconstruction injects anatomically-accurate landmark positions derived from
a human face model, correcting the nose bridge, eye socket depth, and lip curvature
that a depth model approximates loosely.

### Approach A — MediaPipe Face Mesh (468 landmarks)

MediaPipe detects 468 facial landmarks in 2D, then maps each to a 3D position using
the depth map. This does not require a 3D face model — it works entirely from the
single image and depth.

**Implementation in `03_mesh_generate.py`:**

Replace the `run_reconstruction_mediapipe` function body:

```python
def run_reconstruction_mediapipe(rgba_image, depth_map):
    import mediapipe as mp
    import numpy as np

    H, W = depth_map.shape
    rgb_image = rgba_image[:, :, :3]

    mp_face_mesh = mp.solutions.face_mesh
    with mp_face_mesh.FaceMesh(
        static_image_mode=True,
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
    ) as face_mesh:
        results = face_mesh.process(rgb_image)

    if not results.multi_face_landmarks:
        print("  Phase 3: no face detected — using depth geometry only")
        return None

    landmarks = results.multi_face_landmarks[0].landmark
    print(f"  Phase 3: {len(landmarks)} landmarks detected")

    points = []
    for lm in landmarks:
        # MediaPipe landmark coords are 0.0-1.0 normalized to image size
        px = int(lm.x * W)
        py = int(lm.y * H)

        # Clamp to image bounds
        px = max(0, min(W - 1, px))
        py = max(0, min(H - 1, py))

        # Map pixel to the same unit-scale coord space as the depth point cloud
        # X: 0..W -> -1..+1,  Y: 0..H -> +1..-1 (flipped),  Z: from depth map
        x = (px / (W - 1)) * 2.0 - 1.0
        y = -((py / (H - 1)) * 2.0 - 1.0)

        # Use the depth map Z for this pixel (same Z_SCALE applied in depth_to_pointcloud)
        z_depth = float(depth_map[py, px])

        # Skip background points (depth=0 means background after masking)
        if z_depth < 0.01:
            continue

        # Sample color from the source RGBA (same grey composite as depth_to_pointcloud)
        alpha = rgba_image[py, px, 3] / 255.0
        r = rgba_image[py, px, 0] * alpha + 128 * (1 - alpha)
        g = rgba_image[py, px, 1] * alpha + 128 * (1 - alpha)
        b = rgba_image[py, px, 2] * alpha + 128 * (1 - alpha)

        # Note: z_scale is applied in depth_to_pointcloud, not here.
        # Store raw depth — the merge happens before z_scale is applied.
        # Actually z_scale is already baked into z in depth_to_pointcloud,
        # so we apply it here too for consistency.
        z = z_depth * DEFAULT_Z_SCALE

        points.append([x, y, z, r/255.0, g/255.0, b/255.0])

    if not points:
        return None

    landmark_array = np.array(points, dtype=np.float64)
    print(f"  Phase 3: {len(landmark_array)} landmark points added to point cloud")
    return landmark_array
```

Then in `depth_to_pointcloud()`, merge the reconstruction result after building the
base point cloud. Find the section after the point cloud is built and add:

```python
# Inside depth_to_pointcloud(), after pcd is created from xyz array:
# (The reconstruction_result parameter needs to be threaded through — see below)

if reconstruction_result is not None:
    # Add landmark points to the point cloud
    extra_xyz = reconstruction_result[:, :3]
    extra_rgb = reconstruction_result[:, 3:]

    all_xyz = np.vstack([np.asarray(pcd.points), extra_xyz])
    pcd.points = o3d.utility.Vector3dVector(all_xyz)

    if pcd.has_colors():
        all_rgb = np.vstack([np.asarray(pcd.colors), extra_rgb])
        pcd.colors = o3d.utility.Vector3dVector(all_rgb)
```

**To wire this in, `depth_to_pointcloud` needs a `reconstruction_result` parameter.**
Update its signature and call site in `main()`.

**Activate:**
```powershell
python 03_mesh_generate.py --reconstruction mediapipe
```

### Approach B — face-alignment 3D landmarks (68/98 points)

`face_alignment` detects 68 or 98 facial landmarks with 3D positions (X, Y, Z in
image space). This is more geometrically accurate than MediaPipe's depth-sampled
positions because face-alignment predicts Z from a trained model.

```python
def run_reconstruction_face_align(rgba_image, depth_map):
    import face_alignment
    import numpy as np

    H, W = depth_map.shape
    rgb_image = rgba_image[:, :, :3]

    fa = face_alignment.FaceAlignment(
        face_alignment.LandmarksType.THREE_D,
        device='cuda',
        flip_input=False,
    )

    # face_alignment expects uint8 RGB HWC array
    preds = fa.get_landmarks(rgb_image)

    if preds is None or len(preds) == 0:
        print("  Phase 3: face_alignment found no faces — using depth geometry only")
        return None

    # Take the first detected face
    landmarks_3d = preds[0]  # shape (68, 3) — x, y, z_in_image_space

    print(f"  Phase 3: {len(landmarks_3d)} 3D landmarks detected")

    points = []
    for lm in landmarks_3d:
        px, py = int(lm[0]), int(lm[1])
        # lm[2] is the model's predicted Z — scale it to match depth units
        # The sign/scale of lm[2] varies by model; normalize against the depth map.
        px = max(0, min(W - 1, px))
        py = max(0, min(H - 1, py))

        x = (px / (W - 1)) * 2.0 - 1.0
        y = -((py / (H - 1)) * 2.0 - 1.0)
        z = float(depth_map[py, px]) * DEFAULT_Z_SCALE

        alpha = rgba_image[py, px, 3] / 255.0
        r = (rgba_image[py, px, 0] * alpha + 128 * (1 - alpha)) / 255.0
        g = (rgba_image[py, px, 1] * alpha + 128 * (1 - alpha)) / 255.0
        b = (rgba_image[py, px, 2] * alpha + 128 * (1 - alpha)) / 255.0

        points.append([x, y, z, r, g, b])

    return np.array(points, dtype=np.float64) if points else None
```

**Activate:**
```powershell
python 03_mesh_generate.py --reconstruction face_align
```

### When to use each

- **MediaPipe** is the first thing to activate. It is fast, runs on CPU, and the 468
  landmarks densely cover the face. Excellent for straightforward portrait poses.

- **face-alignment** is slower but its 3D landmark predictions are geometrically
  more accurate. Use it when MediaPipe's depth sampling gives incorrect Z positions
  (which happens when the depth map has artifacts in specific facial regions).

- **Combine both:** There is nothing stopping you from running both and merging their
  landmark sets into a single extra point array. The merge logic in `depth_to_pointcloud`
  does not care about the source of the extra points.

---

## 12. Upgrading UV Quality — From xatlas to RizomUV

xatlas is an automatic UV packer. It works well for hard-surface models but produces
suboptimal UV charts for organic shapes like faces — it tends to create many small
charts with wasted atlas space and visible seams in unexpected places.

RizomUV is a professional UV unwrapping tool (€149–€259 perpetual). It understands
organic surfaces and places seams where they are least visible (behind ears, under
chin). For portrait crystals, better UV packing means better texture resolution on
the face and fewer artifacts where seams cross facial features.

### Implementing the RizomUV subprocess call

RizomUV has a Lua scripting API and can be called headlessly via subprocess. The general
pattern is: export the mesh as OBJ, write a Lua script that loads it and runs the
unwrapper, call `rizomuv.exe --headless script.lua`, read back the UV-mapped OBJ.

**Implementation in `04b_texture_bake.py`:**

```python
import subprocess
import tempfile
import trimesh

def uv_with_rizomuv(vertices: np.ndarray, faces: np.ndarray):
    # Path to RizomUV executable — update for your install location
    RIZOMUV_EXE = Path(r"C:\Program Files\Rizom Lab\RizomUV 2024\rizomuv.exe")
    if not RIZOMUV_EXE.exists():
        raise FileNotFoundError(
            f"RizomUV not found at {RIZOMUV_EXE}. "
            "Install RizomUV or use xatlas."
        )

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        input_obj  = tmpdir / "input.obj"
        output_obj = tmpdir / "output.obj"

        # Write mesh as OBJ for RizomUV
        _write_simple_obj(vertices, faces, input_obj)

        # Write RizomUV Lua script
        lua_script = tmpdir / "unwrap.lua"
        lua_script.write_text(f"""
ZomLoad({{File={{Path="{str(input_obj).replace(chr(92), '/')}"}} }})
ZomIslandGroups({{Mode="Auto", MergingPolicy=8322}})
ZomUnwrap({{Options={{Iterations=1}}}})
ZomPack({{Options={{Rotate=true, Translate=true}}}})
ZomSave({{File={{Path="{str(output_obj).replace(chr(92), '/')}", UVWProps=true}} }})
""")

        # Run RizomUV headless
        result = subprocess.run(
            [str(RIZOMUV_EXE), "-cfi", str(lua_script)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            raise RuntimeError(f"RizomUV failed: {result.stderr}")

        # Load the UV-mapped mesh back
        mesh = trimesh.load(str(output_obj), process=False)
        uvs      = np.array(mesh.visual.uv, dtype=np.float32)
        vmapping = np.arange(len(uvs), dtype=np.int32)
        indices  = np.array(mesh.faces, dtype=np.int32)
        return uvs, vmapping, indices


def _write_simple_obj(vertices, faces, path):
    with open(str(path), "w") as f:
        for v in vertices:
            f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
        for face in faces:
            f.write(f"f {face[0]+1} {face[1]+1} {face[2]+1}\n")
```

**Activate:**
```powershell
python 04b_texture_bake.py --uv-tool rizomuv
```

### Ministry of Flat (free alternative)

Ministry of Flat is a free standalone UV unwrapper. Place `mof.exe` in `tools\` at the
pipeline root. The interface is a command-line OBJ in / OBJ out tool.

```python
def uv_with_mof(vertices: np.ndarray, faces: np.ndarray):
    MOF_EXE = PIPELINE_DIR / "tools" / "mof.exe"
    if not MOF_EXE.exists():
        raise FileNotFoundError("mof.exe not found in tools/. Download from quelsolaar.com")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        input_obj  = tmpdir / "input.obj"
        output_obj = tmpdir / "output.obj"

        _write_simple_obj(vertices, faces, input_obj)

        subprocess.run(
            [str(MOF_EXE), str(input_obj), str(output_obj)],
            check=True, capture_output=True, timeout=60,
        )

        mesh = trimesh.load(str(output_obj), process=False)
        uvs      = np.array(mesh.visual.uv, dtype=np.float32)
        vmapping = np.arange(len(uvs), dtype=np.int32)
        indices  = np.array(mesh.faces, dtype=np.int32)
        return uvs, vmapping, indices
```

---

## 13. Upgrading Texture Projection — PyMeshLab Raster Method

The current texture projection in `04b_texture_bake.py` uses a pure Python barycentric
rasterizer. It is correct but slow on large atlases. PyMeshLab has a built-in photo
projection filter that uses hardware-accelerated rasterization.

**Replacement projection function in `04b_texture_bake.py`:**

```python
def project_photo_pymeshlab(
    mesh_path: Path,
    photo_path: Path,
    output_obj_path: Path,
    atlas_size: int = 4096,
) -> None:
    import pymeshlab

    ms = pymeshlab.MeshSet()
    ms.load_new_mesh(str(mesh_path))

    # Load the source photo as a raster (camera image)
    ms.load_new_raster(str(photo_path))

    # Build a camera matrix from the image dimensions (orthographic front projection)
    # For a portrait photo taken roughly face-on, this is a good approximation.
    ms.apply_filter(
        "set_raster_camera_per_raster",
        camtype=0,   # 0 = orthographic
    )

    # Project raster color onto mesh UV
    ms.apply_filter(
        "transfer_texture_to_color_per_vertex",
        textsize=atlas_size,
        pushpull=True,  # fill holes in atlas using surrounding color
    )

    ms.save_current_mesh(str(output_obj_path))
```

This replaces the barycentric loop entirely and is significantly faster for atlases
over 2048. The output is an OBJ with texture coordinates baked by PyMeshLab's internal
rasterizer, which handles edge padding (pushpull) automatically.

---

## 14. Depth Model Selection and Profile Tuning

### Choosing the right depth model

**Depth Anything V2 Large** (`depth_anything_v2`) is the default and correct choice for
portraits. It produces smooth, anatomically plausible depth fields with strong facial
feature awareness. The Large variant downloads ~1.3GB on first run.

**MiDaS DPT-Large** (`midas`) is the reliable fallback. Use it if DAv2 produces unusual
results on a specific image (e.g. very unusual lighting, non-standard pose, or a
profile view where the face is partially occluded). MiDaS is generally less accurate on
faces but more robust to unusual inputs.

**Depth Pro** (`depth_pro`) is an Apple model that produces metric depth (in real-world
scale) with sharp edge boundaries. It is wired in the registry but not implemented. When
implemented, it is particularly useful for subjects at unusual distances or when the
absolute depth values matter (vs. relative depth).

**Marigold** (`marigold`) is a diffusion-based depth model that produces extraordinarily
fine surface detail. It is the highest-quality option for hair and skin texture. It is
significantly slower than transformer models (~5–10 minutes per image vs. ~30 seconds).
Wired in the registry, not implemented.

### Profile combinations and when to use them

```
Standard profile, DAv2 Large:
  python 02_depth_estimate.py --model depth_anything_v2 --profile standard
  Use for: initial test run to verify the depth model is working correctly.
  Not recommended for production — hard mask edges create geometric ledges.

Feathered edges, DAv2 Large:
  python 02_depth_estimate.py --profile soft_edges_feathered
  Use for: all portrait production runs. Default recommendation.

Feathered edges, wide sigma, DAv2 Large:
  python 02_depth_estimate.py --profile soft_edges_feathered --feather 25
  Use for: subjects with complex hair, flyaways, or very fine edge detail.

Standard profile, MiDaS:
  python 02_depth_estimate.py --model midas --profile soft_edges_feathered
  Use for: fallback when DAv2 produces artifacts on a specific image.
```

---

## 15. Quality Checkpoints — What to Look For

Every stage has a manual inspection step. Do not skip these. Automated tests verify that
the code ran without crashing. Only a human can verify that the output is correct for
crystal engraving quality.

| After stage | What to open         | What to verify                                              | Tool                            |
| ----------- | -------------------- | ----------------------------------------------------------- | ------------------------------- |
| 01          | `_prepared_mask.png` | Hair edges soft, background pure black                      | Any image viewer                |
| 01          | `_prepared.png`      | Subject on transparent background, correct crop             | Photoshop / GIMP                |
| 02          | `_preview.png`       | Nose tip brightest; forehead domes; background black        | Any image viewer                |
| 02          | `_depth.png`         | No flat regions in face; nose protrudes clearly             | Photoshop 16-bit view           |
| 03          | `_pointcloud.ply`    | Vertex colors visible; nose protrudes in Z                  | MeshLab                         |
| 03          | `_mesh.ply`          | Normals correct (visible from front); no catastrophic holes | MeshLab or Blender              |
| 04b         | `_textured.obj`      | Photo correctly mapped; no seams on face; no dark fringing  | Blender Material Preview        |
| 04b         | `_atlas.png`         | Face covers majority of atlas; no large blank regions       | Any image viewer                |
| 04b         | `_textured.glb`      | Correct in browser viewer or Windows 3D Viewer              | windows.3dviewer / 3dviewer.net |
| 05          | `_report.txt`        | Triangle count reasonable; orientable = YES                 | Text editor                     |
| 05          | `_export.obj`        | Recognizable portrait; no floating geometry                 | Blender                         |
| 06          | `_{preset}.obj`      | Fits within crystal dimensions; bottom at Z=0               | Cockpit3D                       |

---

## 16. Tuning Reference — Every Knob Explained

All parameters can be set in `.env` (persistent) or overridden per-run with CLI flags
(one-off). CLI always wins over `.env`.

### Stage 01 parameters

| Parameter                                  | Default             | Effect                                                                               |
| ------------------------------------------ | ------------------- | ------------------------------------------------------------------------------------ |
| `REMBG_MODEL` / `--model`                  | `isnet-general-use` | Which background removal model to use                                                |
| `PREPARE_LONG_EDGE` / `--target-long-edge` | `1800`              | Working resolution. Do not increase beyond 2400 without testing memory.              |
| `REMBG_FG_THRESHOLD` / `--fg-threshold`    | `240`               | Higher = more pixels classified as foreground. Raise if subject has missing areas.   |
| `REMBG_BG_THRESHOLD` / `--bg-threshold`    | `10`                | Lower = more aggressive background removal. Lower if background bleeds into subject. |
| `REMBG_ERODE_SIZE` / `--erode-size`        | `10`                | Shrinks the subject silhouette. Higher = tighter mask, loses some edge pixels.       |

### Stage 02 parameters

| Parameter                              | Default             | Effect                                                        |
| -------------------------------------- | ------------------- | ------------------------------------------------------------- |
| `DEPTH_MODEL` / `--model`              | `depth_anything_v2` | Depth model to use                                            |
| `DEPTH_ANYTHING_MODEL_SIZE` / `--size` | `Large`             | DAv2 model size. Large = best. Small = fast draft.            |
| `DEPTH_PROFILE` / `--profile`          | `standard`          | Edge masking mode. Use `soft_edges_feathered` for production. |
| `--feather`                            | profile default     | Gaussian sigma for feathered profile. 10 = subtle, 25 = wide. |

### Stage 03 parameters

| Parameter                           | Default | Effect                                                                                 |
| ----------------------------------- | ------- | -------------------------------------------------------------------------------------- |
| `Z_SCALE` / `--z-scale`             | `0.3`   | Depth exaggeration. Higher = more dramatic relief. Start at 0.3 and tune with crystal. |
| `POISSON_DEPTH` / `--poisson-depth` | `11`    | Triangle count and detail level. See table in section 6.                               |
| `MESH_VOXEL_SIZE`                   | `0.001` | Point cloud density. Smaller = more points = denser mesh. 0.0 = no downsample.         |
| `--no-color`                        | off     | Skip vertex color projection. Use for geometry-only debugging.                         |
| `--reconstruction`                  | `none`  | Phase 3 mode. `none` = stub. `mediapipe` or `face_align` once implemented.             |

### Stage 04b parameters

| Parameter                             | Default  | Effect                                                                  |
| ------------------------------------- | -------- | ----------------------------------------------------------------------- |
| `UV_TOOL` / `--uv-tool`               | `xatlas` | UV unwrapper. `xatlas` = free default. `rizomuv` = best quality (paid). |
| `TEXTURE_ATLAS_SIZE` / `--atlas-size` | `4096`   | Atlas resolution. 4096 = production. 8192 = maximum detail.             |
| `--no-glb`                            | off      | Skip GLB export. Use if trimesh is not installed.                       |

### Stage 05 parameters

| Parameter                                | Default  | Effect                                                                         |
| ---------------------------------------- | -------- | ------------------------------------------------------------------------------ |
| `MESH_EXPORT_FORMAT` / `--export-format` | `all`    | Formats to export. `obj,stl` for specific selection.                           |
| `MESH_SMOOTH_PASSES` / `--smooth`        | `0`      | Laplacian passes. Keep at 0. Only increase to reduce Poisson ripple artifacts. |
| `--decimate`                             | disabled | Target triangle count. Use for editing copies, not production.                 |

### Stage 06 parameters

| Parameter                        | Default  | Effect                                           |
| -------------------------------- | -------- | ------------------------------------------------ |
| `CRYSTAL_PRESET` / `--crystal`   | `m_cube` | Crystal blank preset.                            |
| `CRYSTAL_MARGIN_MM` / `--margin` | `5.0`    | Clearance on all sides. Do not reduce below 3mm. |

---

## 17. Cockpit3D Handoff

After step 06 produces the crystal-sized OBJ:

1. Open Cockpit3D
2. `File > Import Mesh` — select the `_{preset}.obj` from `output/exports/{run}/crystal_size/`
3. Verify the mesh appears within the crystal blank boundary in the Cockpit3D viewport
4. If the textured GLB was produced (step 04b): import the `_textured.glb` instead for
   texture-mapped laser power assignment
5. Configure laser point spacing (typically 0.1–0.3mm depending on crystal size)
6. Run the point cloud generation — Cockpit3D converts the mesh to laser points
7. Preview the point cloud in Cockpit3D before sending to the machine
8. Send to the SSLE machine

**The Z_SCALE setting directly affects the depth of engraving inside the crystal.**
After your first crystal, measure the actual engraved depth and compare to what Cockpit3D
predicted. Calibrate Z_SCALE accordingly. The relationship is linear — if the engraving
is 70% of the intended depth, multiply Z_SCALE by 1.43.

---

## 18. The Professional Path — Stage-by-Stage Upgrade Plan

This section describes the specific ordered steps to go from the current working
pipeline to full production quality. Each step builds on the previous.

### Step 1 — Verify the geometry pipeline (immediate, no code changes)

Run all 6 stages on `human_one_person.jpg`. Inspect every output manually. Confirm you
can produce a Cockpit3D-ready file. This is the baseline you are improving from.

```powershell
python 01_prepare.py --file human_one_person.jpg --run v1
python 02_depth_estimate.py --profile soft_edges_feathered --from-run v1 --run v1
python 03_mesh_generate.py --from-run v1 --prepared-run v1 --run v1
python 04b_texture_bake.py --from-run v1 --from-prepared-run v1 --run v1
python 05_export.py --from-run v1 --run v1
python 06_scale_crystal.py --crystal m_cube --from-run v1
```

Import the result into Cockpit3D. Note the quality issues — these are your upgrade targets.

### Step 2 — Activate MediaPipe reconstruction (Phase 3)

Implement `run_reconstruction_mediapipe()` as described in section 11. Test on
`human_one_person.jpg` with `--reconstruction mediapipe`. Open the resulting PLY in
MeshLab and compare nose tip depth, eye socket depth, and forehead curvature against the
non-reconstruction result. The landmark-supplemented point cloud should show crisper
facial feature geometry.

Expected improvement: 10–25% better facial feature definition in the mesh.

### Step 3 — Upgrade texture projection to PyMeshLab

Replace the barycentric rasterizer in `04b_texture_bake.py` with the PyMeshLab raster
projection as described in section 13. Test with `--atlas-size 4096` then `--atlas-size 8192`.
Compare the texture atlas quality on fine features (eyelashes, lip texture, hair detail).

Expected improvement: significantly faster baking time + better atlas hole filling.

### Step 4 — Purchase and integrate RizomUV

Once the pipeline produces crystals you are satisfied with from a geometry standpoint,
invest in RizomUV. Implement `uv_with_rizomuv()` as described in section 12. Run both
`--uv-tool xatlas` and `--uv-tool rizomuv` on the same mesh and compare the atlas layout
in Blender. RizomUV will show more face coverage in the atlas and fewer seams crossing
facial features.

Expected improvement: 20–40% more texture resolution on the face within the same atlas size.

### Step 5 — Test Marigold depth model

When the rest of the pipeline is stable, implement the Marigold depth model stub in
`02_depth_estimate.py`. Marigold uses diffusion to produce depth with extraordinary
surface micro-detail — skin pores, fabric texture, hair strands. This turns a smooth
depth surface into a high-frequency detailed surface.

```python
# In MODEL_REGISTRY, marigold is already registered:
"marigold": {
    "type": "diffusers",
    "repo": "prs-eth/marigold-lcm-v1-0",
    ...
}

# Implementation in load_depth_model():
if model_name == "marigold":
    from diffusers import MarigoldDepthPipeline
    import torch
    pipe = MarigoldDepthPipeline.from_pretrained(
        "prs-eth/marigold-lcm-v1-0",
        torch_dtype=torch.float16,
    ).to(device)
    # Returns in estimate_depth():
    # depth_output = pipe(rgb, num_inference_steps=4, ensemble_size=5)
    # depth_np = depth_output.prediction[0, 0].numpy()
```

Marigold takes 4–10 minutes per image. Run it only for final production-quality jobs.

### Step 6 — Implement face-alignment reconstruction and merge with MediaPipe

Once MediaPipe reconstruction is stable, add `face_alignment` reconstruction and merge
both landmark sets. The combined point set gives dense coverage (468 MediaPipe + 68
face-alignment) across the face, each providing different geometric information.

### Step 7 — Multi-view depth fusion (advanced)

The current pipeline uses a single front-facing photo. Professional quality for complex
subjects (3/4 views, profile shots) requires multiple views. This is an architectural
extension — the `depth_to_pointcloud` function would be called once per view angle and
the resulting point clouds merged before Poisson reconstruction. Each view adds geometry
that is hidden in other views.

This is the final professional upgrade and requires multi-view photography of the subject.
It is not implemented anywhere in the codebase and requires architectural changes to step
01 and step 02 to handle multiple images per run.

---

*End of pipeline-03-pro guide.*
*For CLAUDE.md session memory, see pipeline-03-pro/CLAUDE.md.*
*For architecture decisions from pipeline-02, see pipeline-02-zoedepth-changes.md.*
