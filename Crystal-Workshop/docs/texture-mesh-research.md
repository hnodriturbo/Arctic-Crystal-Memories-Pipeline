# Texture Mesh Research — K9 Crystal Pipeline

**Date:** 2026-05-30  
**Scope:** All packages — free, open source, and commercial. Cost is not a filter.  
**Status:** Research complete. Implementation decisions recorded at the bottom.

---

## Why Texture Meshes Are Central to SSLE Quality

The SSLE machine engraves by firing laser pulses at XYZ coordinates inside a crystal block. Each pulse creates a micro-fracture (bubble). The visual result depends on two things:

1. **Position (XYZ)** — drives the 3D relief shape. This comes from the depth map and mesh geometry.
2. **Laser power per point** — drives perceived brightness and portrait likeness. This is what makes a crystal look like a specific person — the shadows under the eyes, the highlight on the nose, the skin tone gradients, the hair detail.

Without a texture-mapped mesh, laser power can only be estimated from geometry alone (surface normals, Z depth). With a texture-mapped mesh, every surface point carries its actual photo color from the source portrait. The engraving software (Cockpit3D) then samples that texture to assign precise laser power values per point — encoding the portrait's photographic shading directly into the crystal.

**This pipeline's job is to produce the best possible textured mesh as input to Cockpit3D.** Cockpit3D takes that mesh and fine-tunes the point cloud generation for the specific machine, crystal blank, and engraving parameters. We own everything upstream of Cockpit3D — the geometry quality, the texture projection quality, and the mesh preparation. That is where portrait quality is won or lost.

**Texture meshes are not a visual bonus. They are the mechanism by which photo likeness survives into the crystal.**

---

## UV Unwrapping — What It Is and Why It Matters

Before a photo can be projected onto a 3D mesh as a texture, the mesh needs **UV coordinates** — a 2D mapping of every 3D surface point onto a flat texture image. This is called UV parameterization or UV unwrapping.

For portrait meshes from depth maps:
- The mesh surface is curved and complex (face, hair, shoulders)
- UV seams must be placed where they are least visible
- Distortion must be minimized so the photo projects cleanly without stretching
- Atlas packing must be efficient so texture resolution is not wasted on empty space

UV unwrapping quality directly affects texture projection quality. A bad UV map = stretched or distorted texture = wrong shading encoded into the crystal.

---

## Package Research — Full List Including Commercial

---

### TIER 1 — Primary candidates for this pipeline

---

#### Open3D — already installed

**Cost:** Free (MIT license)  
**Install:** already in `.venv`

**Texture capability:**
- `RGBDImage.create_from_color_and_depth()` + Poisson reconstruction → generates mesh with **vertex colors** sampled from the source photo at each 3D point
- No UV atlas, no MTL file — vertex colors only
- `TriangleMesh` supports `triangle_uvs` and `textures` attributes but Poisson does not populate them

**Verdict:** The fast path for Stage 04. Zero extra cost. Vertex colors are sufficient for Blender editing and provide enough texture information for Cockpit3D import. Not sufficient for a clean exportable UV-mapped texture atlas.

---

#### PyMeshLab — best full-pipeline texture tool

**Cost:** Free (GPL license)  
**Install:** `pip install pymeshlab`  
**Maintenance:** Actively maintained — highest-rated mesh processing Python library (95/100). Python bindings for MeshLab, which is the industry standard for large mesh processing.

**Texture capability:**
- `project_active_rasters_color_to_current_mesh()` — projects a raster image (the source portrait) onto the mesh surface using camera projection matrices. Proper photo-to-surface texture projection.
- `iso_parametrization_build_atlased_mesh()` — automatic UV parameterization and atlas generation
- `transfer_vertex_attributes_to_texture_1_or_2_meshes()` — bakes vertex colors (from Open3D) into a UV-mapped texture atlas
- Handles 4M+ triangle meshes (MeshLab is designed for large-scale mesh processing)
- Exports textured OBJ+MTL, GLB, PLY with embedded textures

**Verdict:** The correct tool for full UV-mapped textured mesh generation in this pipeline. Bridges the gap between Open3D geometry output and a production-ready textured mesh. Primary choice for Stage 04b.

---

#### RizomUV — best-in-class commercial UV unwrapper

**Cost:** Commercial — perpetual license ~€149 (Virtual Spaces) or ~€259 (Real + Virtual Spaces). Subscription also available. Free trial available.  
**Platform:** Windows, Mac, Linux  
**Python API:** Yes — Python 3 integrated into RizomUV since version 2022.1. Full scripting API. Also has a C++ library for pipeline integration.  
**Automation:** Command-line automatable. Supports batch processing of large datasets.

**UV capability:**
- Industry-leading UV packing algorithms — maximizes texture space better than any open source tool
- LSCM, angle-based, and pelt mapping algorithms
- Automatic seam detection and placement
- Works as a standalone executable driven by Python scripts via its API
- Has bridge plugins for major 3D tools (Maya, Houdini SideFX Labs, Cinema 4D via third-party)

**Verdict:** The best UV unwrapper available. The Python API means it can be called from Stage 04b as a subprocess or via its scripting interface. If UV quality is critical (and for portrait crystal work it is), this is the right investment. The superior packing means more texture resolution per triangle = better photo projection quality.

**Pipeline integration path:** Call RizomUV via its Python API or as a CLI subprocess from `04b_texture_bake.py` — pass it the geometry mesh, get back a UV-mapped mesh, then use PyMeshLab to project the photo texture onto the UVs.

---

#### Ministry of Flat (MoF) — free automatic UV, CLI-automatable

**Cost:** Free for most uses. Commercial source license available (perpetual, for redistribution or inclusion in other software). Contact for pricing.  
**Platform:** Windows, Mac, Linux — standalone executable + CLI  
**Python integration:** Not native Python, but fully automatable via CLI subprocess call. Blender bridge addon exists (mofbridge on GitHub — exports mesh, runs MoF, reimports UVs).

**UV capability:**
- Fully automatic UV unwrapping — no manual seam placement needed
- Command-line mode: integrate directly into pipeline as a subprocess
- Fast — designed for batch processing large datasets
- Not as fine-tuned as RizomUV but significantly faster for automated runs

**Verdict:** Excellent free alternative to RizomUV for automated pipelines where speed matters more than perfect packing. Worth including as the default UV path in Stage 04b (free, CLI, fast), with RizomUV as the quality upgrade option.

**Pipeline integration path:** `subprocess.run(['mof', '--input', mesh_path, '--output', uv_mesh_path])` from `04b_texture_bake.py`.

---

#### xatlas — pure Python UV parameterization

**Cost:** Free (MIT license)  
**Install:** `pip install xatlas`  
**Maintenance:** Actively maintained — updated July 2025. Python bindings for the xatlas C++ library.

**UV capability:**
- `xatlas.parametrize(vertices, faces)` → returns UV coordinates, vertex mapping, and atlas indices
- Generates UV atlases by segmenting the mesh into charts, parameterizing each chart, and packing them
- Pure Python API — no subprocess, no external executables
- Handles large meshes but atlas quality is lower than RizomUV for organic shapes

**Verdict:** The easiest pure-Python UV path. Less quality than RizomUV or MoF for portrait meshes (more chart fragmentation, less optimal packing), but zero setup cost and zero subprocess complexity. Good for testing and iteration. Use as fallback when RizomUV/MoF is not available.

---

### TIER 2 — Specialized tools worth knowing

---

#### libUvula — Ultimaker's UV unwrapper with Python bindings

**Cost:** Free (LGPL-3.0 license)  
**Source:** github.com/Ultimaker/libUvula  
**Python bindings:** Yes — built via conan2. `pyUvula.unwrap(vertices, indices)` → returns UVs, texture_width, texture_height  
**Built for:** Large meshes (developed for 3D printing workflows)

**UV algorithm:** Groups faces by normal proximity to create patches that project without distortion. Inspired by Blender's Smart UV Project but as a standalone C++ library.

**Verdict:** Interesting option — designed specifically for large meshes (relevant for 4M triangle portrait meshes) and has proper Python bindings. Less battle-tested than xatlas but worth evaluating. Requires building from source via conan2, which adds setup friction.

---

#### PyTorch3D — Meta's differentiable rendering library

**Cost:** Free (BSD license)  
**Install:** `pip install pytorch3d` (requires PyTorch + CUDA)  
**Maintenance:** Actively maintained by Meta Research

**Texture capability:**
- Loads OBJ files with UV-mapped textures: `load_obj(path, create_texture_atlas=True)`
- `TexturesUV` and `TexturesVertex` classes for storing and sampling texture data on meshes
- Differentiable texture sampling — can optimize texture appearance
- GPU-accelerated rendering and texture interpolation
- Supports texture atlas creation, vertex UV coordinates, and texture face indices

**Verdict:** Not primarily a texture baking tool — it's a deep learning rendering library. But it is the best tool for GPU-accelerated texture sampling and rendering once a texture already exists on the mesh. Relevant if the pipeline evolves toward neural optimization of texture quality or depth estimation using differentiable rendering. Also useful for generating high-quality preview renders of textured meshes during Stage 04b/05 quality checks.

**Requires:** CUDA. Already planned for this pipeline.

---

#### InstaMAT — commercial material and mesh baking platform

**Cost:** Free for revenue under $100k/year. Commercial license for studios.  
**SDK:** C++ SDK released October 2025. InstaMAT Pipeline = command-line tool for scripted execution.  
**Automation:** `InstaMAT Pipeline` CLI can execute all graph types including mesh baking jobs.

**Texture capability:**
- Node-based Element Graph with Mesh Bake node — generates normal maps, curvature maps, ambient occlusion, and full texture atlases from high-poly + low-poly mesh pairs
- Automated mesh baking pipelines
- Procedural material generation and texturing

**Verdict:** Powerful but designed for game asset pipelines (high-poly → low-poly baking). For this project the workflow is different — single mesh, photo projection, not multi-mesh baking. Overkill for now. Revisit if the pipeline needs procedural material generation (e.g., skin shader synthesis, hair material reconstruction beyond photo projection).

---

#### Microsoft UVAtlas — isochart texture atlasing

**Cost:** Free (MIT license)  
**Source:** github.com/microsoft/UVAtlas  
**Python bindings:** None official. C++ library only. Could be wrapped via ctypes or pybind11 but significant effort.

**UV algorithm:** Isochart — spectral analysis-based stretch-minimizing parameterization. High quality, particularly for organic surfaces.

**Verdict:** High-quality algorithm but no Python integration path without custom binding work. Not worth pursuing when PyMeshLab, xatlas, and RizomUV all offer better accessibility. Noted for completeness.

---

#### Nuvo — neural UV mapping

**Cost:** Research paper (arxiv 2312.05283) — no production package yet  
**What it does:** Neural UV mapping designed for challenging geometry from NeRF models and text-to-3D outputs. Produces less fragmented atlases than xatlas for difficult topology.

**Verdict:** Research stage only. Worth watching — if it produces a stable Python package it could be relevant for the depth-map-to-mesh pipeline where geometry can be noisy or irregular.

---

#### fast-simplification — mesh decimation with texture preservation

**Cost:** Free (MIT license)  
**Install:** `pip install fast-simplification`  
**What it does:** Wraps VTK's quadric decimation. Reduces triangle count while preserving vertex colors and point data.

**Verdict:** Needed for the post-edit decimation step. After manual editing in Blender and before crystal export in Stage 06, decimate from 4M triangles to ~500k–1M while preserving the vertex color data. This is the last processing step before texture baking — or it can run after baking if vertex colors need to survive into the scaled crystal export.

---

#### trimesh — mesh I/O and GLB export

**Cost:** Free (MIT license)  
**Install:** `pip install trimesh`

**Texture capability:** Stores and re-exports vertex-colored meshes and UV-mapped meshes. Best GLB (binary GLTF) export with embedded textures — cleaner than OBJ+MTL for texture-embedded single-file export.

**Verdict:** Use at the export stage in Stage 05. After PyMeshLab bakes the texture, trimesh handles the GLB export. Not for texture generation.

---

## Recommended Workflow — Three Paths

### Path A: Fast (vertex colors, editing-ready)

For iteration, Blender editing sessions, and rapid quality checks.

```
_nobg.png + 16-bit depth map
    ↓  Open3D RGBDImage integration
vertex-colored point cloud
    ↓  Poisson reconstruction (Open3D)
vertex-colored TriangleMesh (4M–6M triangles)
    ↓  o3d.io.write_triangle_mesh → PLY
PLY with vertex colors → Blender / MeshLab for editing
    ↓  manual edit + decimate (Blender)
edited mesh (500k–1M triangles)
    ↓  05_export.py
OBJ + STL + PLY (full_size)
```

**Packages needed:** Open3D (already installed)

---

### Path B: Production (UV-mapped texture atlas, SSLE-ready)

For final export to Cockpit3D. Runs after Path A editing is complete.

```
edited mesh from Path A (geometry clean, right triangle count)
    ↓  RizomUV (via CLI/API) OR Ministry of Flat (CLI) OR xatlas (Python)
UV-parameterized mesh with atlas coordinates
    ↓  PyMeshLab: project_active_rasters_color_to_current_mesh
        (source: _nobg.png projected via camera matrix)
UV-mapped mesh with photo texture baked as atlas image
    ↓  PyMeshLab export OBJ+MTL  +  trimesh export GLB
textured OBJ+MTL / GLB
    ↓  06_scale_crystal.py
crystal-sized textured mesh → Cockpit3D
```

**Packages needed:** PyMeshLab + xatlas (free minimum), RizomUV (commercial upgrade for UV quality)

---

### Path C: Neural quality (future, when research matures)

PyTorch3D differentiable rendering used to optimize texture quality against the source photo — texture is adjusted so the rendered view of the mesh matches the original portrait as closely as possible. Then exported as in Path B.

**Not implemented.** Requires CUDA. Revisit when PyTorch3D integration is otherwise needed in the pipeline.

---

## Implementation Plan for Pipeline

### Stage 04 update

`04_mesh_generate.py` — add RGBD integration to generate vertex-colored mesh by default. Requires passing `_nobg.png` alongside the depth map (already in the same run folder). Add `--no-color` flag to skip color sampling.

### New Stage 04b

`04b_texture_bake.py` — takes the vertex-colored mesh from Stage 04. Steps:
1. UV parameterize (xatlas default, RizomUV optional via `--uv-tool rizomuv`)
2. Project source photo onto UV-mapped surface (PyMeshLab)
3. Export textured OBJ+MTL and GLB to `output/meshes/{run}/textured/`
4. Print texture atlas resolution, coverage %, and projection quality report

### Stage 05 update

`05_export.py` — detect if `textured/` subfolder exists in the mesh run and export both geometry-only and textured versions. The textured version is the SSLE production export.

### Stage 06 — no changes needed

UV coordinates and vertex colors are unaffected by uniform scaling and translation. Texture survives `06_scale_crystal.py` as-is.

---

## Packages to Install

```powershell
# Core texture pipeline — install before Stage 04 work begins
.\.venv\Scripts\pip.exe install pymeshlab
.\.venv\Scripts\pip.exe install xatlas
.\.venv\Scripts\pip.exe install trimesh
.\.venv\Scripts\pip.exe install fast-simplification

# GPU rendering / quality preview (requires CUDA PyTorch — install after CUDA fix)
.\.venv\Scripts\pip.exe install pytorch3d
```

**Commercial tools (download separately, not pip):**
- **RizomUV** — rizomuv.com — ~€149–€259 perpetual. Recommended purchase when entering production phase.
- **Ministry of Flat** — quelsolaar.com/ministry_of_flat — free CLI, no installation required beyond downloading the binary.

---

## Open Questions

1. **Texture atlas resolution:** What atlas image size does PyMeshLab generate from a 3840×3840 source projected onto a 4M-triangle mesh? Need to test whether a 4096×4096 atlas captures sufficient portrait detail or if 8192×8192 is needed.
2. **Hair + alpha transparency:** The `_nobg.png` has semi-transparent pixels at hair boundaries. PyMeshLab's raster projection may treat transparent pixels as black or skip them. Need to test: project onto neutral grey background composite vs. raw RGBA. Likely need to pre-composite onto white or neutral tone before projecting.
3. **Decimation order:** Bake at full resolution (4M–6M tri) then decimate → preserves texture fidelity, slower. Or decimate first then bake → faster, coarser atlas coverage. Recommendation: bake at full resolution, decimate with vertex color preservation (fast-simplification), then export. The texture atlas follows vertex data through decimation.
4. **RizomUV purchase timing:** Buy when Stage 04b implementation begins. The free path (xatlas + MoF) is sufficient for development and testing.
5. **Cockpit3D input format:** Confirmed that Cockpit3D takes the mesh as input and fine-tunes it for SSLE production. Need to confirm whether it prefers OBJ+MTL, GLB, or STL+separate texture file as input format for its own pipeline.

---

## Sources

- [Automated UV Unwrapping Tools 2025 — Medium](https://medium.com/@Jamesroha/automated-uv-unwrapping-tools-for-complex-3d-geometry-2025-3f12ef3d697c)
- [xatlas Python bindings — GitHub](https://github.com/mworchel/xatlas-python)
- [xatlas C++ library — GitHub](https://github.com/jpcy/xatlas)
- [RizomUV — rizomuv.com](https://www.rizomuv.com/)
- [Ministry of Flat — quelsolaar.com](https://www.quelsolaar.com/ministry_of_flat/)
- [mofbridge Blender addon — GitHub](https://github.com/garanovich/mofbridge)
- [libUvula — Ultimaker GitHub](https://github.com/Ultimaker/libUvula)
- [PyMeshLab filter list — readthedocs](https://pymeshlab.readthedocs.io/en/latest/filter_list.html)
- [PyTorch3D textured mesh tutorial](https://pytorch3d.org/tutorials/fit_textured_mesh)
- [Microsoft UVAtlas — GitHub](https://github.com/microsoft/UVAtlas)
- [InstaMAT C++ SDK release — instamaterial.com](https://instamaterial.com/2025/10/09/unlock-your-creativity-instamat-c-sdk-now-live-for-custom-integrations/)
- [InstaMAT Pipeline docs](https://docs.instamat.io/en/Products/InstaMAT_Pipeline)
- [Nuvo: Neural UV Mapping — arxiv](https://arxiv.org/html/2312.05283v1)
- [Quad Remesher / Remeshy](https://quadremesher.com/)
- [Beyond the Surface: 3D Mesh from 2D Images in Python — Medium](https://medium.com/red-buffer/beyond-the-surface-advanced-3d-mesh-generation-from-2d-images-in-python-0de6dd3944ac)
