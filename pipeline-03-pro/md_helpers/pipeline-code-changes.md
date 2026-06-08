# Pipeline Python Code Changes & Utils Files Changes

## Table of Contents
`dateOfChange & timeOfChange` - `file_utils` <!-- each table of contents should be clickable like a chapter -->
[2026-06-02] - `04b_texture_bake.py` — planar UV projection, fast atlas bake, OBJ-only mesh scan
[2026-06-05] - `00_upscale.py` — new script: Real-ESRGAN AI upscale for input images below 1800px

### What Was Done

#### **file_utils.py**
```python
""" 
Here will be explanation of the change and the full function 
(if part of function was changed, copy it all here explaining the change 
in the commenting top block here above the new version of the function) 
"""

def get_input_dir() -> Path:
    """Return the pipeline input directory, creating it if needed."""
    raw = os.getenv("INPUT_DIR", "./input")
    path = (PIPELINE_DIR / raw).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path
```
- This specific function was changed to use the environmental `INPUT_DIR` and fall back to the relative ./input folder

---

## 2026-06-02 — `04b_texture_bake.py`

### Three changes in one session

#### 1. Added `uv_with_planar()` — new default UV method

**OLD CODE (xatlas default):**
```python
DEFAULT_UV_TOOL = os.getenv("UV_TOOL", "xatlas")

def uv_with_xatlas(
    vertices: np.ndarray, faces: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    import xatlas
    atlas = xatlas.Atlas()
    atlas.add_mesh(vertices.astype(np.float32), faces.astype(np.uint32))
    atlas.generate(xatlas.ChartOptions(), xatlas.PackOptions())
    vmapping, indices, uvs = atlas[0]
    return uvs, vmapping, indices

UV_TOOLS = {
    "xatlas": uv_with_xatlas,
    "rizomuv": uv_with_rizomuv,
    "mof": uv_with_mof,
}
```

**NEW CODE (planar default):**
```python
DEFAULT_UV_TOOL = os.getenv("UV_TOOL", "planar")

def uv_with_planar(
    vertices: np.ndarray, faces: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    x = vertices[:, 0]
    y = vertices[:, 1]
    x_min, x_max = x.min(), x.max()
    y_min, y_max = y.min(), y.max()
    u = (x - x_min) / (x_max - x_min + 1e-8)
    v = 1.0 - (y - y_min) / (y_max - y_min + 1e-8)
    uvs = np.stack([u, v], axis=1).astype(np.float32)
    vmapping = np.arange(len(vertices), dtype=np.int32)
    return uvs, vmapping, faces.astype(np.int32)

UV_TOOLS = {
    "planar": uv_with_planar,
    "xatlas": uv_with_xatlas,
    "rizomuv": uv_with_rizomuv,
    "mof": uv_with_mof,
}
```

xatlas cuts the mesh into hundreds of disconnected UV islands optimised for geometry packing, not photo projection. When the photo was sampled onto those islands the result was a random patchwork of colour fragments — visually broken. Planar projection maps each vertex UV directly from its normalised XY screen position, so the atlas is a clean front-facing photo projection. For a portrait crystal viewed from the front this is the correct approach.

---

#### 2. Replaced slow barycentric rasterizer with fast planar path in `project_photo_to_atlas()`

**OLD CODE:**
```python
def project_photo_to_atlas(
    vertices, uvs, vmapping, faces_uv, photo_rgb, atlas_size
) -> np.ndarray:
    uv_vertices_3d = vertices[vmapping]
    H, W = photo_rgb.shape[:2]
    atlas = np.zeros((atlas_size, atlas_size, 3), dtype=np.uint8)
    uv_px = (uvs * (atlas_size - 1)).astype(np.float32)

    for face in faces_uv:
        i0, i1, i2 = face
        p0, p1, p2 = uv_vertices_3d[i0], uv_vertices_3d[i1], uv_vertices_3d[i2]
        u0, u1, u2 = uv_px[i0], uv_px[i1], uv_px[i2]
        # ... bounding box + per-pixel barycentric loop ...
        for ay in range(min_v, max_v + 1):
            for ax in range(min_u, max_u + 1):
                # ... barycentric test, 3D interpolation, photo sample ...
                atlas[ay, ax] = photo_rgb[py, px]
    return atlas
```

**NEW CODE:**
```python
def project_photo_to_atlas(
    vertices, uvs, vmapping, faces_uv, photo_rgb, atlas_size
) -> np.ndarray:
    from PIL import Image as PILImage

    is_planar = (
        len(vmapping) == len(vertices)
        and np.array_equal(vmapping, np.arange(len(vertices), dtype=vmapping.dtype))
    )
    if is_planar:
        # Fast path: atlas = photo resized. Completes in <1s.
        photo_pil = PILImage.fromarray(photo_rgb).resize(
            (atlas_size, atlas_size), PILImage.LANCZOS
        )
        return np.array(photo_pil)

    # Slow fallback for non-planar UV tools (xatlas/rizomuv/mof)
    # ... same per-triangle barycentric loop as before ...
```

The old pure-Python per-triangle loop took 1020 seconds for 633K triangles. With planar UVs the atlas is simply the photo resized to atlas_size — a single Lanczos resize. The slow fallback is preserved for xatlas/rizomuv/mof use cases.

---

#### 3. `list_geometry_meshes()` — OBJ only, skip PLY

**OLD CODE:**
```python
def list_geometry_meshes(run: str) -> list[Path]:
    """Find all _mesh.obj or _mesh.ply files in output/meshes/{run}/geometry/."""
    files = sorted(
        [
            p
            for p in geo_dir.iterdir()
            if p.suffix in (".obj", ".ply") and "_mesh" in p.name
        ],
        key=lambda p: p.name.lower(),
    )
```

**NEW CODE:**
```python
def list_geometry_meshes(run: str) -> list[Path]:
    """Find _mesh.obj files in output/meshes/{run}/geometry/. OBJ only — PLY is a duplicate."""
    files = sorted(
        [p for p in geo_dir.iterdir() if p.suffix == ".obj" and "_mesh" in p.name],
        key=lambda p: p.name.lower(),
    )
```

Step 03 writes both `.obj` and `.ply` for the same mesh. The previous scan picked up both, causing step 04b to bake the same mesh twice and overwrite its own output (wasting ~30 minutes per run). OBJ is the canonical format for texture baking; PLY is for MeshLab inspection only.

---

## 2026-06-05 — `00_upscale.py`

### New script: Real-ESRGAN AI upscale for input images

New file created from scratch. Upscales any PNG in `input/` whose long edge is below 1800px using Real-ESRGAN x4plus, then resizes the 4x result back down to exactly 1800px on the long edge. Alpha channel is handled by splitting RGB and alpha before inference and upscaling the alpha mask with Lanczos separately, then recombining. Output is saved as `<name>_upscaled.png` alongside the original.

Also applied the required basicsr compatibility patch in `.venv/Lib/site-packages/basicsr/data/degradations.py`: changed `from torchvision.transforms.functional_tensor import rgb_to_grayscale` to `from torchvision.transforms.functional import rgb_to_grayscale` — the `functional_tensor` submodule was removed in newer torchvision versions.

**Why:** `image_01.png` is 960×960px — below the 1800px working resolution. Simple bilinear/Lanczos upscaling adds no real detail. Real-ESRGAN recovers facial detail via a trained super-resolution model before depth estimation and mesh creation in external software. `image_02.png` is already 1800px and is skipped automatically.