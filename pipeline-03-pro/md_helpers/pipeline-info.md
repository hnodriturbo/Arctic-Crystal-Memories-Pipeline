# PIPELINE-03-PRO - Pipeline Information File

---

## What sources does stage 04b use? (Definitive Answer — 2026-06-02)

Stage 04b reads from **two** sources:

**Source 1 — Geometry mesh** (`output/meshes/{run}/geometry/`)
The `_mesh.obj` (or `_mesh.ply`) produced by step 03. This is the 3D surface with vertices and triangles. Step 04b reads the vertex positions and face topology from this file. It does NOT use the vertex colors embedded in this mesh — those are ignored; the photo projection overwrites them.

**Source 2 — Prepared RGBA image** (`output/prepared/{run}/`)
The `_prepared.png` produced by step 01. This is the background-removed portrait at 1800px, stored as RGBA (background is transparent). Step 04b composites this onto neutral grey (128,128,128) using `composite_rgba_on_grey()`, then uses the resulting RGB image as the photo to project onto the UV atlas.

**How source 2 is matched to source 1:** `find_prepared_for_mesh()` strips depth/model suffix tokens from the mesh filename (`_mesh`, `_depth_anything_v2`, `_soft_edges_feathered`, etc.) backward until it recovers the base prepared stem, then looks for `{stem}.png` in `output/prepared/{prepared_run}/`. If no exact match, falls back to the first `*_prepared.png` in that run.

**What step 04b produces from these two sources:**
1. UV unwrap via xatlas — generates a UV coordinate set for every triangle
2. Barycentric photo projection — for each UV atlas pixel, traces back through 3D space to the corresponding photo pixel and samples color
3. Output: `_textured.obj` + `_textured.mtl` + `_atlas.png` + `_textured.glb` → all into `output/meshes/{run}/textured/`

**Key point:** Step 04b does NOT run depth estimation or mesh generation. It is purely a texture-baking step that needs geometry (step 03 output) and the source photo (step 01 output).

---

## Why does the OBJ from step 03 already have color?

The geometry mesh from step 03 uses vertex colors — every vertex in the mesh has an RGB value baked directly into the PLY/OBJ file itself. No texture file needed. MeshLab and Blender can display these per-vertex colors when you turn them on. Step 04b's job is different — it creates a proper UV-mapped texture atlas (a separate PNG image that maps onto the surface via UV coordinates). Vertex colors are fine for inspection but Cockpit3D works better with a real texture atlas because it samples color at sub-vertex precision.

So you have two color representations now:

Step 03 OBJ: vertex colors (color stored per point, no image file)
Step 04b OBJ: UV texture (color stored in a 4096×4096 PNG, referenced via MTL file)

## Can edges have a different Z-depth?

Yes, and it's actually a useful idea for crystal engraving — you could push the silhouette edge slightly inward in Z so the subject boundary doesn't just "cliff off" but has a defined gradual transition. The way to do it is in step 02: the soft_edges_feathered profile already does exactly this — it reduces the depth value for semi-transparent pixels near the edge using the alpha channel as a weight. Your feather=100 run is already applying this. A more aggressive approach would be to manually paint the 16-bit depth PNG in Photoshop — brush the edge region to a specific mid-grey value to force it to a chosen depth.

## The trimesh.visual change — is trimesh a stub?

No, trimesh is fully installed and used. The problem was Pylance (VS Code's Python type checker) — trimesh's official type stubs don't declare visual as a known attribute on the trimesh module, even though trimesh.visual is a real subpackage at runtime. Pylance was marking it as an error purely based on incomplete stub definitions.

By switching from trimesh.visual.material.PBRMaterial to from trimesh.visual.material import PBRMaterial, Pylance can now resolve the import directly from the file path instead of going through the module attribute, so it stops complaining. The actual behavior at runtime is identical either way — same function, same result.