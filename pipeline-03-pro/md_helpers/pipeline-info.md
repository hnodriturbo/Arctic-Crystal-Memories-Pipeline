# PIPELINE-03-PRO - Pipeline Information File

## Why does the OBJ from step 03 already have color?

The geometry mesh from step 03 uses vertex colors — every vertex in the mesh has an RGB value baked directly into the PLY/OBJ file itself. No texture file needed. MeshLab and Blender can display these per-vertex colors when you turn them on. Step 04b's job is different — it creates a proper UV-mapped texture atlas (a separate PNG image that maps onto the surface via UV coordinates). Vertex colors are fine for inspection but Cockpit3D works better with a real texture atlas because it samples color at sub-vertex precision.

So you have two color representations now:

Step 03 OBJ: vertex colors (color stored per point, no image file)
Step 04b OBJ: UV texture (color stored in a 4096×4096 PNG, referenced via MTL file)
Can edges have a different Z-depth?

Yes, and it's actually a useful idea for crystal engraving — you could push the silhouette edge slightly inward in Z so the subject boundary doesn't just "cliff off" but has a defined gradual transition. The way to do it is in step 02: the soft_edges_feathered profile already does exactly this — it reduces the depth value for semi-transparent pixels near the edge using the alpha channel as a weight. Your feather=100 run is already applying this. A more aggressive approach would be to manually paint the 16-bit depth PNG in Photoshop — brush the edge region to a specific mid-grey value to force it to a chosen depth.

The trimesh.visual change — is trimesh a stub?

No, trimesh is fully installed and used. The problem was Pylance (VS Code's Python type checker) — trimesh's official type stubs don't declare visual as a known attribute on the trimesh module, even though trimesh.visual is a real subpackage at runtime. Pylance was marking it as an error purely based on incomplete stub definitions.

By switching from trimesh.visual.material.PBRMaterial to from trimesh.visual.material import PBRMaterial, Pylance can now resolve the import directly from the file path instead of going through the module attribute, so it stops complaining. The actual behavior at runtime is identical either way — same function, same result.