# Texture Mesh Guide — K9 Crystal Pipeline

**Date:** 2026-05-30  
**Scope:** UV unwrapping, texture projection, and photo baking for SSLE-quality portrait meshes.  
**Budget:** Open to paid/commercial solutions where quality justifies cost.

---

## Why Texture Meshes Are the Core of SSLE Portrait Quality

The SSLE machine engraves by firing a laser at precise XYZ coordinates inside a K9 crystal block. Each pulse creates a micro-fracture — a tiny bubble of light. The visual result the viewer sees through the crystal depends entirely on two things per point:

**1. Position (XYZ)** — where in space the bubble sits. This creates the 3D relief — the nose protrudes, the eyes recede, the face has volume. This comes from the depth map and mesh geometry.

**2. Laser power** — how large and bright the bubble is. This is what encodes facial likeness into the crystal — the shadow under the cheekbone, the highlight on the forehead, the gradient across the skin, the individual hair strands. Without this, two different portraits engraved at the same depth profile would look nearly identical.

The only way to correctly assign laser power per point is to have the **original photograph's luminance and color mapped onto the 3D mesh surface**. When the mesh carries that photo as a texture, every exported point knows not just where it is in 3D space but what shade it carries from the source image. Cockpit3D and equivalent SSLE software sample that texture when generating the laser point cloud.

**This pipeline's responsibility is everything upstream of Cockpit3D.** Cockpit3D is the final production step — it takes our textured mesh and fine-tunes the engraving parameters for the specific machine, crystal blank, and job settings. The geometry quality, the texture projection accuracy, and the mesh preparation are entirely owned by this pipeline. Portrait likeness is won or lost here, before Cockpit3D ever opens the file.

**Conclusion: texture meshes are not optional. They are the mechanism by which a photograph becomes a recognizable person inside a crystal.**

---

## Foundational Concepts

### What UV Coordinates Are

A 3D mesh is a surface in space. A texture is a flat image. UV coordinates are the bridge — a 2D mapping that says "this point on the 3D surface corresponds to this pixel in the texture image." Every vertex on the mesh gets a U (horizontal) and V (vertical) coordinate in the range 0–1, pointing to a location in the texture atlas.

For portrait meshes from depth maps, getting UV coordinates right is critical:
- The mesh surface is curved and organically shaped — face, hair, shoulders, neck
- UV seams (where the flat unwrap is cut) must be placed where they are least visible
- Distortion must be minimized so photo pixels project cleanly without stretching
- Atlas packing must be efficient so no texture resolution is wasted on empty space

A poorly generated UV map means the photo projection stretches across the face incorrectly — noses become wide, eyes get skewed, skin gradients smear. Bad UVs cannot be fixed by a better texture. UV quality is foundational.

### What Texture Projection Is

Once a mesh has UV coordinates, the source photograph is projected onto the surface — every UV-mapped face of the mesh is "painted" with the corresponding pixel from the photo. The result is stored as a texture atlas image (typically 4096×4096 or 8192×8192 pixels) paired with the mesh via a material file.

For portrait work from a single camera image (which is what this pipeline uses — one depth-estimated photo), projection is straightforward: the camera is effectively at a known position relative to the face, and the photo is the texture. The challenge is handling the edges — semi-transparent hair pixels, the transition from subject to background, and the areas of the mesh not visible in the original photo (back of the head, sides).

### Vertex Colors vs. UV Texture Atlas

There are two ways to carry color on a mesh:

**Vertex colors** — each vertex stores an RGB value. Simple, no UV needed, loads in any 3D viewer. Limitations: color resolution is limited by vertex density, no proper UV channel for material export, not the format SSLE software expects for laser power mapping.

**UV texture atlas** — the mesh has UV coordinates and a separate texture image file. Higher resolution, proper material definition, supported by Cockpit3D and all SSLE production software. More complex to generate but the correct production format.

This pipeline uses vertex colors as the fast path for Blender editing (cheap, built into Open3D) and a UV texture atlas as the production path for Cockpit3D export.

---

## Package Research — Full Evaluation

### Tier 1 — Core pipeline packages

---

#### Open3D

| | |
|---|---|
| **Cost** | Free — MIT license |
| **Install** | Already in `.venv` |
| **Maintenance** | Actively maintained — large community, regular releases |

**What it does for texture:**

Open3D's `RGBDImage.create_from_color_and_depth()` combines the source photo (`_nobg.png`) and the 16-bit depth map into a paired RGBD object. When a point cloud is integrated from this RGBD image and then reconstructed into a mesh via Poisson surface reconstruction, each vertex automatically carries an RGB value sampled from the photo at that 3D position. The result is a vertex-colored mesh.

`TriangleMesh` in Open3D has `triangle_uvs` and `textures` attributes, but Poisson reconstruction does not populate them. Vertex colors only — no UV atlas, no MTL file.

**Strengths:**
- Zero extra setup — already installed, already used for mesh generation
- Vertex-colored mesh generated as a natural byproduct of RGBD integration
- Loads in Blender with visible portrait colors — accurate enough for editing sessions
- Handles 4M–6M triangle meshes efficiently

**Limitations:**
- No UV coordinates → cannot export a proper textured OBJ+MTL or GLB
- Vertex color resolution is limited by triangle density — fine detail between vertices is lost
- Not what Cockpit3D expects for texture-driven laser power assignment

**Role in pipeline:** Fast path. Stage 04 generates vertex-colored meshes automatically. Used for all Blender editing work. Not used for final SSLE production export.

---

#### PyMeshLab

| | |
|---|---|
| **Cost** | Free — GPL license |
| **Install** | `pip install pymeshlab` |
| **Maintenance** | Actively maintained — Python bindings for MeshLab, rated highest among mesh processing Python libraries. MeshLab itself is a 20-year industry standard. |
| **Large mesh support** | Designed for millions of polygons — no practical limit for this pipeline's mesh sizes |

**What it does for texture:**

PyMeshLab exposes MeshLab's full filter pipeline via Python. For texture baking, the key functions are:

- `project_active_rasters_color_to_current_mesh()` — takes a raster image (the source photo) and a camera matrix and projects the image color onto the mesh surface. This is proper photo-to-surface texture projection. The mesh must have UV coordinates before this step.

- `iso_parametrization_build_atlased_mesh()` — automatic UV parameterization using isochart or harmonic methods. Generates UV coordinates and packs them into an atlas layout.

- `transfer_vertex_attributes_to_texture_1_or_2_meshes()` — bakes vertex color data (from Open3D) into a UV-mapped texture atlas image. This is the bridge between the vertex-color fast path and the UV-texture production path: generate vertex colors in Open3D, then use this to produce a proper atlas.

- Export: OBJ+MTL with texture image, PLY with embedded texture, GLB via trimesh.

**Strengths:**
- The most complete texture baking pipeline available in pure Python
- UV parameterization + projection + atlas generation all in one library
- Handles 4M+ triangle meshes
- Well-documented filter list with hundreds of mesh processing operations

**Limitations:**
- UV quality from `iso_parametrization_build_atlased_mesh` is good but not as precise as dedicated UV tools like RizomUV for organic surfaces
- Requires per-wedge UV coordinates before texture transfer — must run UV parameterization first, cannot skip
- Some edge cases with flat-plane UVs (not relevant for portrait meshes which have organic curvature)

**Role in pipeline:** Primary texture baking tool for Stage 04b. Takes the geometry mesh from Stage 04, UV-parameterizes it, projects the source photo onto the surface, and exports the textured mesh for Cockpit3D.

---

#### xatlas

| | |
|---|---|
| **Cost** | Free — MIT license |
| **Install** | `pip install xatlas` |
| **Maintenance** | Actively maintained — Python bindings for xatlas C++ library. Updated July 2025. |

**What it does:**

xatlas is a UV parameterization library. It takes vertex positions and face indices and returns UV coordinates plus an atlas chart layout. Specifically:

```python
import xatlas
vmapping, indices, uvs = xatlas.parametrize(vertices, faces)
```

The mesh is segmented into charts (regions of the surface that can be flattened with minimal distortion), each chart is parameterized independently, and all charts are packed into the atlas space.

**Strengths:**
- Pure Python API — no subprocess, no external executables, no extra tools
- Lightweight and fast
- Good atlas packing for hard-surface meshes and moderately organic shapes
- Straightforward integration — call from any Python script

**Limitations:**
- Atlas quality for highly organic surfaces (face, hair) can be fragmented — more seam lines visible than RizomUV or Ministry of Flat
- Packing efficiency is lower than commercial tools — some wasted atlas space
- UV generation only — no texture projection, no baking. xatlas generates coordinates; PyMeshLab does the actual texture work.

**Role in pipeline:** Default UV generation in Stage 04b. Call xatlas first to generate UV coordinates, then pass the UV-mapped mesh to PyMeshLab for photo projection. Zero-cost path that produces acceptable results for testing and iteration.

---

### Tier 2 — Commercial tools for production quality

---

#### RizomUV

| | |
|---|---|
| **Cost** | ~€149 (Virtual Spaces) or ~€259 (Real + Virtual Spaces) — perpetual license. Subscription also available. Free trial. |
| **Platform** | Windows, Mac, Linux |
| **Python API** | Yes — Python 3 integrated into RizomUV since version 2022.1. Full scripting API and a C++ library for pipeline integration. |
| **Automation** | Command-line automatable. Batch processing of large datasets supported. |
| **Website** | rizomuv.com |

**What it does:**

RizomUV is the industry standard for professional UV unwrapping. It is used in game studios, VFX pipelines, and photogrammetry workflows worldwide. For portrait meshes specifically:

- **Superior packing algorithms** — maximizes the percentage of texture atlas space actually covered by mesh UVs. More coverage = more texture resolution assigned to portrait detail. A 10–20% improvement in packing efficiency over xatlas translates directly to sharper projected texture per triangle.
- **LSCM, angle-based, and pelt mapping** — multiple parameterization algorithms optimized for different surface types. Pelt mapping is particularly good for organic surfaces like faces.
- **Automatic seam detection and placement** — places UV cuts where they cause the least visual distortion on the surface. For a portrait, good seam placement means no visible texture discontinuities across the face.
- **Python scripting API** — full control over unwrapping parameters, seam placement, and packing from Python scripts. Call it as a library or drive the standalone executable via its scripting interface.
- **CLI integration** — can be called as a subprocess from `04b_texture_bake.py`, passing the input mesh and receiving a UV-mapped mesh.

**Strengths:**
- Genuinely best-in-class UV quality for organic shapes — consistently outperforms every open source tool
- Python API allows full pipeline automation without manual interaction
- Perpetual license — one-time cost, no recurring fees
- Trusted in professional production environments

**Limitations:**
- Cost (though reasonable for a professional tool)
- Runs as a separate application — subprocess or API call from the pipeline, not a pip install
- Setup is more involved than pure Python packages

**Role in pipeline:** Quality upgrade for Stage 04b UV generation. Replace xatlas with RizomUV when entering production phase. Recommended purchase when Stage 04b implementation begins. The UV quality improvement directly improves texture projection quality, which directly improves crystal engraving result.

**Integration path:**
```python
# Stage 04b calls RizomUV via its Python API
import subprocess
result = subprocess.run([
    'rizomuv', '--input', mesh_path,
    '--script', 'unwrap_portrait.lua',  # RizomUV script file
    '--output', uv_mesh_path
])
```

---

#### Ministry of Flat

| | |
|---|---|
| **Cost** | Free for most uses. Commercial source license available for redistribution or inclusion in other software — contact for pricing. |
| **Platform** | Windows, Mac, Linux — standalone executable + CLI |
| **Python integration** | CLI subprocess call. No native Python API. Blender bridge addon exists (mofbridge on GitHub). |
| **Website** | quelsolaar.com/ministry_of_flat |

**What it does:**

Ministry of Flat is a fully automatic UV unwrapper built for pipeline automation. It operates as a command-line tool — pass it a mesh, it returns a UV-mapped mesh. No interaction required. It is designed specifically for batch processing large datasets.

The algorithm groups faces by normal proximity to create patches that can be projected without significant distortion, then splits groups by spatial proximity to ensure consistent patches. Fast and reliable for automated runs.

**Strengths:**
- Free for this use case
- Fully CLI-automatable — one subprocess call, no interaction
- Fast — designed for batch production
- Produces clean, usable UVs with no manual configuration

**Limitations:**
- No Python API — subprocess only
- Packing quality below RizomUV for fine portrait work
- Less control over seam placement than RizomUV

**Role in pipeline:** Default free automatic UV path. Use as the Stage 04b default when RizomUV is not available, or when automated batch processing is needed without quality as the primary concern.

**Integration path:**
```python
import subprocess
subprocess.run(['mof', input_mesh_path, output_uv_mesh_path])
```

---

### Tier 3 — Supporting tools

---

#### trimesh

| | |
|---|---|
| **Cost** | Free — MIT license |
| **Install** | `pip install trimesh` |

**What it does for texture:**

trimesh can store and re-export vertex-colored meshes and UV-mapped meshes. Its primary value in this pipeline is **GLB export** — Binary GLTF format with texture image embedded in the file. GLB is a single-file format that carries geometry, UV coordinates, and texture together, supported by modern 3D viewers, web viewers, and SSLE software.

Does not generate UVs, project textures, or bake photos. It operates on texture data that already exists on the mesh.

**Role in pipeline:** Export step in Stage 05. After PyMeshLab bakes the texture, use trimesh to export the production GLB file alongside the OBJ+MTL.

---

#### fast-simplification

| | |
|---|---|
| **Cost** | Free — MIT license |
| **Install** | `pip install fast-simplification` |

**What it does:**

Wraps VTK's quadric decimation algorithm. Reduces triangle count from millions to hundreds of thousands while preserving vertex attributes including colors. Configurable target reduction ratio.

```python
import fast_simplification
mesh_out = fast_simplification.simplify(points, faces, target_reduction=0.75)
# 4M triangles → 1M triangles, vertex colors preserved
```

**Role in pipeline:** Post-edit decimation before crystal export. After manual editing in Blender and before running Stage 06, decimate from 4M–6M triangles to 500k–1M while preserving vertex color data. Texture baking should happen after decimation so the atlas covers the final mesh density.

---

#### PyTorch3D

| | |
|---|---|
| **Cost** | Free — BSD license |
| **Install** | `pip install pytorch3d` (requires CUDA PyTorch) |
| **Maintenance** | Actively maintained by Meta Research |

**What it does for texture:**

PyTorch3D is a differentiable 3D rendering library. It supports loading OBJ files with UV-mapped textures, `TexturesUV` and `TexturesVertex` classes for storing texture data on meshes, and GPU-accelerated texture sampling and rendering. The differentiable renderer means texture appearance can be optimized — adjusted so that the rendered view of the mesh matches the original photograph.

```python
from pytorch3d.io import load_obj
verts, faces, aux = load_obj(path, create_texture_atlas=True)
# aux.texture_atlas contains the baked texture atlas
```

**Strengths:**
- GPU-accelerated — extremely fast texture sampling on the RTX 3060
- Differentiable — enables neural optimization of texture quality if needed
- Can generate high-quality preview renders of textured meshes for quality checks

**Limitations:**
- Requires CUDA (available after CUDA fix)
- Primarily a deep learning tool — overkill as a static texture baking tool
- Complex API compared to PyMeshLab for straightforward photo projection

**Role in pipeline:** Quality preview renders and future neural texture optimization. Once the CUDA fix is confirmed working, use PyTorch3D to render the textured mesh from the original camera viewpoint and compare it pixel-by-pixel against the source photo — an automatic quality check for texture projection accuracy.

---

#### libUvula

| | |
|---|---|
| **Cost** | Free — LGPL-3.0 |
| **Source** | github.com/Ultimaker/libUvula |
| **Python bindings** | Yes — built via conan2. `pyUvula.unwrap(vertices, indices)` → UVs, texture_width, texture_height |

**What it does:**

C++ UV unwrapper developed by Ultimaker for 3D printing workflows. Groups faces by normal proximity to create flat-projectable patches — inspired by Blender's Smart UV Project but as a standalone library. Built specifically for large meshes.

**Role in pipeline:** Alternative UV generation path. Less tested than xatlas for portrait meshes. Requires building from C++ source via conan2 — higher setup friction than xatlas pip install. Evaluate if xatlas atlas fragmentation becomes a quality problem and RizomUV is not yet purchased.

---

#### InstaMAT

| | |
|---|---|
| **Cost** | Free for annual revenue under $100k. Commercial license for larger operations. |
| **CLI** | InstaMAT Pipeline — command-line execution of all graph types including mesh baking |
| **SDK** | C++ SDK released October 2025 for custom integration |
| **Website** | instamaterial.com |

**What it does:**

InstaMAT is a professional material design and texture baking platform. Its Element Graph supports Mesh Bake nodes for generating normal maps, curvature maps, ambient occlusion, and texture atlases from high-poly + low-poly mesh pairs. The Pipeline CLI can automate these baking jobs without the UI.

**Role in pipeline:** Not the right fit for the primary texture projection task (single mesh, photo projection). Becomes relevant if the pipeline grows to include procedural material generation — synthesizing skin shaders, hair material overlays, or ambient occlusion baked from the depth map. Worth revisiting at that point.

---

## Recommended Workflow Architecture

### Path A — Fast path: vertex colors for editing

Used for Blender editing sessions, mesh inspection, and rapid iteration. Zero extra packages needed.

```
_nobg.png  +  16-bit depth map
        ↓  Open3D: RGBDImage integration
  vertex-colored point cloud (~14M points from 3840×3840)
        ↓  Open3D: Poisson surface reconstruction (octree depth 10–11)
  vertex-colored TriangleMesh (4M–6M triangles)
        ↓  o3d.io.write_triangle_mesh → PLY with vertex colors
  Load into Blender → edit geometry, sculpt, correct artifacts
        ↓  Blender: decimate to 500k–1M triangles (keep vertex colors)
  edited geometry mesh → Stage 05 → OBJ + STL + PLY (full_size)
```

Vertex colors make every feature visible in Blender. You can see exactly where the eyes sit, where the hairline falls, where skin meets background. Editing without this is working blind on a grey surface.

---

### Path B — Production path: UV-mapped texture atlas for Cockpit3D

Used for final export. Run after Path A editing is complete and the mesh geometry is approved.

```
edited + decimated mesh (500k–1M triangles, with vertex colors)
        ↓  xatlas (default) OR RizomUV (quality) OR Ministry of Flat (batch)
  UV-parameterized mesh with atlas coordinates
        ↓  PyMeshLab: project_active_rasters_color_to_current_mesh
             input raster: _nobg.png composited onto neutral background
             camera matrix: identity / frontal projection from depth pipeline
  UV-mapped mesh with photo texture baked as atlas image (4096×4096 or 8192×8192)
        ↓  PyMeshLab: export OBJ + MTL + texture PNG
           trimesh: export GLB (texture embedded)
  textured OBJ+MTL  /  textured GLB
        ↓  Stage 06: 06_scale_crystal.py
             UV coordinates and texture are unaffected by uniform scaling
  crystal-sized textured mesh → Cockpit3D
```

---

### Path C — Future: neural texture optimization

After Path B texture is generated, use PyTorch3D's differentiable renderer to compare the rendered textured mesh against the source photo from the original camera viewpoint. Optimize texture values to minimize the pixel-level difference. This adjusts for projection errors, mesh inaccuracies, and depth estimation artifacts — bringing the engraved result closer to the source photograph.

Requires CUDA (confirmed working after CUDA fix) and PyTorch3D. Not implemented. Design when Stage 04b is stable.

---

## Expected File Sizes at Each Stage

| Stage | File type | 2x upscale (1920×1920) | 4x upscale (3840×3840) |
|-------|-----------|------------------------|------------------------|
| 04 — full-res mesh | PLY (vertex colors) | 80–150 MB | 300–600 MB |
| 04 — after Blender decimate | PLY (500k–1M tri) | 20–40 MB | 50–100 MB |
| 04b — texture atlas | PNG image | 48 MB (4096²) | 192 MB (8192²) |
| 04b — textured export | OBJ + MTL | 30–70 MB | 80–150 MB |
| 04b — textured export | GLB | 25–60 MB | 70–130 MB |
| 06 — crystal-sized | OBJ + MTL | same as 04b | same as 04b |

The texture atlas image dominates file size after texture baking. A 4096×4096 PNG is ~48 MB uncompressed; GLB compresses it to ~30–40 MB. For production, 4096×4096 is the minimum — use 8192×8192 when maximum portrait detail is required.

---

## Known Challenges and How to Handle Them

### Hair and alpha transparency

The `_nobg.png` source has semi-transparent pixels at hair boundaries. PyMeshLab's raster projection may treat transparent pixels as black or skip them entirely, leaving dark halos along the hair edge.

**Solution:** Before projecting, composite `_nobg.png` onto a neutral mid-grey background (`(128, 128, 128)` or the dominant background tone). This eliminates transparent pixels while preserving all visible subject pixels. The neutral background areas are on mesh geometry that will not appear in the final crystal (they're at the edge or back of the mesh) so the fill color does not affect the engraving result.

### Areas of the mesh not visible in the source photo

For a portrait mesh from a single frontal photo, the sides of the head and the back of the neck have no photo coverage. PyMeshLab's projection leaves these areas with a fallback color (typically grey or whatever the background composite color is).

**Solution:** This is acceptable for crystal engraving — the laser only engraves the visible portrait area. The non-photo-covered parts of the mesh are not in the final crystal face. No action needed unless full 360° texture is required.

### Decimation before or after texture baking

Baking at full resolution (4M–6M triangles) and then decimating produces the most accurate atlas — more vertices means higher projection sampling density means less texture interpolation error. But it is slower.

Decimating first and then baking is faster and the atlas coverage is sparser.

**Recommendation:** Decimate the geometry mesh in Blender after editing, then bake the texture atlas on the decimated mesh (500k–1M triangles). The vertex color data from Open3D guides decimation in Blender and is not needed after the texture atlas is baked. The atlas at 500k triangles projected from a 3840×3840 photo is still far higher quality than the laser resolution of the engraving machine — there is no quality loss.

### UV seams at high magnification in Blender

UV seam edges can appear as faint lines on the mesh surface in certain lighting. This is a visual artifact of the UV cut placement, not a geometry or texture quality issue. It does not appear in the crystal.

**Solution:** Use RizomUV's seam placement algorithm which minimizes visible seam edges on organic surfaces. xatlas can produce more fragmented atlases with more seam lines. For production runs, the RizomUV investment directly reduces this.

---

## Installation Order

```powershell
# Install all texture pipeline packages
.\.venv\Scripts\pip.exe install pymeshlab
.\.venv\Scripts\pip.exe install xatlas
.\.venv\Scripts\pip.exe install trimesh
.\.venv\Scripts\pip.exe install fast-simplification

# After CUDA PyTorch is confirmed working
.\.venv\Scripts\pip.exe install pytorch3d
```

**Commercial tools — download and install separately:**

| Tool | Source | When to buy |
|------|--------|-------------|
| RizomUV | rizomuv.com | When Stage 04b implementation begins |
| Ministry of Flat | quelsolaar.com/ministry_of_flat | Free — download now, use immediately |
| InstaMAT | instamaterial.com | When procedural material generation is needed |

---

## Stage Implementation Plan

### Stage 04 — update

Add RGBD integration to `04_mesh_generate.py` so vertex colors are generated by default. The `_nobg.png` is already in the same run folder as the depth map. Vertex-colored PLY is the primary output. Add `--no-color` flag for geometry-only runs.

### Stage 04b — new script

`04b_texture_bake.py` — full texture baking pipeline:

1. Load vertex-colored mesh from Stage 04
2. UV parameterize via xatlas (default) or RizomUV (via `--uv-tool rizomuv`)
3. Composite `_nobg.png` onto neutral background (handle transparency)
4. Project composited photo onto UV-mapped mesh via PyMeshLab
5. Export: OBJ+MTL to `output/meshes/{run}/textured/` + GLB via trimesh
6. Print: atlas resolution, UV coverage %, projection quality report

CLI flags:
- `--uv-tool xatlas|rizomuv|mof` — UV generation method
- `--atlas-size 4096|8192` — texture atlas resolution
- `--from-run NAME` — which mesh run to read from
- `--run NAME` — output run name

### Stage 05 — detect textured mesh

`05_export.py` should check if `textured/` exists in the mesh run and export both geometry-only and textured versions. The textured version is the primary SSLE production export.

### Stage 06 — no changes needed

UV coordinates and vertex colors survive `06_scale_crystal.py` unchanged. Uniform scaling and translation do not affect texture data.

---

## Open Questions

| Question | Priority | Notes |
|----------|----------|-------|
| Texture atlas resolution — does 4096² hold enough portrait detail at 4M triangles? | High | Test when 04b is implemented |
| Cockpit3D preferred input format — OBJ+MTL, GLB, or other? | High | Confirm before Stage 05 design is finalized |
| PyMeshLab projection quality on hair boundary after neutral background composite | High | Test with actual `_nobg.png` when mask quality is resolved |
| RizomUV vs xatlas atlas quality difference on portrait mesh | Medium | Test both side by side when 04b is running |
| Decimation level for optimal texture:resolution ratio | Medium | 500k triangles is the current plan — validate against machine laser resolution |
| PyTorch3D texture quality comparison render | Low | Implement after Path B is stable |
