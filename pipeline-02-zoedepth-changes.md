# Pipeline-02 Architecture Changes — Handoff for Pipeline-03
<!-- Written 2026-05-31. Read this before setting up pipeline-03. -->

---

## Why This Document Exists

Pipeline-02 (`pipeline-02-zoedepth`) was restructured significantly during the ZoeDepth testing
session. Pipeline-03 should be built from the **new architecture**, not the original copied files.
This document captures every change made, the reasoning, and what to carry forward.

---

## New Pipeline Structure (4 steps, not 5)

| # | File | Reads from | Writes to | Notes |
|---|------|-----------|-----------|-------|
| 01 | `01_prepare.py` | `input/` | `output/prepared/{run}/` | Merged bg removal + resize |
| 02 | `02_depth_estimate.py` | `output/prepared/{run}/` | `output/depth_maps/{run}/` | Was `03_depth_estimate.py` |
| 03 | `03_mesh_generate.py` | `output/depth_maps/{run}/` | `output/meshes/{run}/` | Was `04_mesh_generate.py` |
| 04 | `04_export.py` | `output/meshes/{run}/` | `output/exports/{run}/` | Was `05_export.py`; stub only |

**Old `01_upscale.py` and `02_remove_bg.py` are deleted.** Do not recreate them.
The upscaling step was removed entirely from the pipeline. `01_prepare.py` replaces both.

---

## Order of Operations (and why)

**Old order:** upscale → bg remove → depth → mesh  
**New order:** bg remove → resize → depth → mesh

**Reasoning:**
- rembg on a 10K×15K upscaled image attempts to allocate ~29 GB RAM → OOM crash.
- rembg on the original resolution works fine and produces better edge quality (more pixels → better segmentation on hair/fur).
- Depth models (ZoeDepth, Depth Anything V2) internally resize input to ~384–518px regardless of what you feed them. A 10K image gives zero depth quality benefit.
- Mesh vertex counts at 1800px long edge (~2.16M source pixels) → 100K–500K triangles after Poisson reconstruction. This is the production sweet spot for Cockpit3D. Going larger produces multi-million-triangle meshes that are slow to review and impractical to send to engravers.

---

## Aspect Ratio Rule — Non-Negotiable

**Always use `compute_target_size()` from `utils/image_utils.py`. Never compute target dimensions inline.**

```python
from utils.image_utils import compute_target_size
new_w, new_h = compute_target_size(orig_w, orig_h, target_long_edge=1800)
```

This function:
- Sets the longer dimension to `target_long_edge` exactly.
- Calculates the shorter dimension with `round()` from the true ratio.
- Clamps both to minimum 1px.
- Is the single source of truth for all resize operations in the pipeline.

The image `human_one_person.jpg` is **2:3 portrait** (5121×7678, ratio 0.6670).
At long edge 1800: output is **1201×1800** (ratio 0.6672 — 1-pixel rounding, unavoidable).
It is NOT 16:9. 16:9 would be landscape ~5121×2881.

---

## Changes to `utils/file_utils.py`

```python
# Old STAGE_OUTPUT_DIRS — remove upscaled and nobg:
STAGE_OUTPUT_DIRS = {
    "upscaled":   "upscaled",      # REMOVED
    "nobg":       "bg_removed",    # REMOVED
    "depth":      "depth_maps",
    "pointcloud": "point_clouds",
    "mesh":       "meshes",
    "export":     "exports",
}

# New STAGE_OUTPUT_DIRS — only what the new pipeline uses:
STAGE_OUTPUT_DIRS = {
    "prepared":   "prepared",      # NEW — replaces upscaled + nobg
    "depth":      "depth_maps",
    "pointcloud": "point_clouds",
    "mesh":       "meshes",
    "export":     "exports",
}
```

No other changes to `file_utils.py`.

---

## New Functions in `utils/image_utils.py`

Three functions were added. Copy them into pipeline-03's `image_utils.py`.

### `compute_target_size(orig_w, orig_h, target_long_edge) → (new_w, new_h)`

```python
def compute_target_size(orig_w: int, orig_h: int, target_long_edge: int) -> tuple[int, int]:
    if orig_h >= orig_w:  # portrait
        new_h = target_long_edge
        new_w = round(orig_w * target_long_edge / orig_h)
    else:  # landscape
        new_w = target_long_edge
        new_h = round(orig_h * target_long_edge / orig_w)
    return max(1, new_w), max(1, new_h)
```

### `resize_image(image, new_w, new_h) → Image.Image`

```python
def resize_image(image: Image.Image, new_w: int, new_h: int) -> Image.Image:
    return image.resize((new_w, new_h), Image.Resampling.LANCZOS)
```

Works for any PIL mode (RGB, RGBA, L). Always pair with `compute_target_size()`.

### `extract_alpha_mask(rgba_image) → Image.Image`

```python
def extract_alpha_mask(rgba_image: Image.Image) -> Image.Image:
    if rgba_image.mode != "RGBA":
        raise ValueError(f"Expected RGBA image, got mode '{rgba_image.mode}'")
    _, _, _, alpha = rgba_image.split()
    return alpha  # mode 'L', white=kept, black=removed
```

---

## New `01_prepare.py` — Key Design Points

- Reads from `input/`, writes to `output/prepared/{run}/`.
- Output filenames: `{stem}_prepared.png` (RGBA) and `{stem}_prepared_mask.png` (grayscale L).
- Steps inside one call: load bytes → rembg (native res) → resize RGBA → save.
- `Image.MAX_IMAGE_PIXELS = None` is set at import to allow large source images without Pillow's decompression bomb warning halting the run.
- Default long edge: `1800` (overridable via `--target-long-edge N` or `.env` `PREPARE_LONG_EDGE`).
- rembg model default: `isnet-general-use` (best portrait hair quality).
- Alpha matting is enabled by default (`alpha_matting=True`).

---

## Changes to `02_depth_estimate.py` (was `03_depth_estimate.py`)

1. Reads from `output/prepared/{run}/` instead of `output/bg_removed/{run}/`.
2. Lists `*_prepared.png` files instead of `*_nobg.png`.
3. Calls `latest_run_name("prepared", ...)` instead of `latest_run_name("nobg", ...)`.
4. Step number changed from 03 → 02 in all print statements and comments.
5. Next-step hint changed from `python 04_mesh_generate.py` → `python 03_mesh_generate.py`.
6. **Critical ZoeDepth fix** (see below).

---

## ZoeDepth `drop_path` Fix — Must Carry Into Pipeline-03 If Using ZoeDepth

timm 0.9.x BeiT `Block.__init__` stores the drop path layer as `self.drop_path1`,
but the MiDaS code cached by torch.hub calls `self.drop_path(x)` — the attribute
doesn't exist, causing `AttributeError: 'Block' object has no attribute 'drop_path'`.

**Fix:** patch `timm.models.beit.Block.__init__` before calling `torch.hub.load`:

```python
try:
    import timm.models.beit as _beit
    _orig_beit_init = _beit.Block.__init__
    def _patched_beit_init(self, *args, **kwargs):
        _orig_beit_init(self, *args, **kwargs)
        if not hasattr(self, "drop_path") and hasattr(self, "drop_path1"):
            self.drop_path = self.drop_path1
    _beit.Block.__init__ = _patched_beit_init
except Exception:
    pass
```

This patch is already in `pipeline-02`'s `02_depth_estimate.py` inside `load_depth_model()`.

**Pipeline-03 uses Depth Anything V2, not ZoeDepth — this patch is NOT needed there.**
Do not apply it in pipeline-03 unless you add ZoeDepth support back.

---

## Vertex / Resolution Sizing Argument

The choice of 1800px long edge is deliberate and justified:

| Source size | Pixels | Dense point cloud | After Poisson mesh | Cockpit3D |
|-------------|--------|------------------|--------------------|-----------|
| 640×960     | 614K   | ~614K vertices   | ~50K–150K tris     | Fast, low detail |
| 1201×1800   | 2.16M  | ~2.16M vertices  | ~150K–500K tris    | **Sweet spot** |
| 2400×3600   | 8.6M   | ~8.6M vertices   | ~500K–2M tris      | Slow to review |
| 5121×7678   | 39M    | ~39M vertices    | multi-million tris | Impractical |
| 10242×15356 | 157M   | ~157M vertices   | tens of millions   | OOM / unusable |

Depth models (ZoeDepth, Depth Anything V2) resize input internally to ~384–518px before
inference. Feeding a 10K image gives identical depth quality to a 1200px image — the model
never sees the extra pixels. The only thing a larger input adds is slower I/O and more
memory for the resize operation.

**Conclusion:** 1800px long edge (1201×1800 for 2:3 portrait) is the correct working
resolution. This is not a compromise — it's the technically correct choice.

---

## Pipeline-03 Setup Notes

- Pipeline-03 should use **Depth Anything V2** (`depth_anything_v2` model, `Large` size).
- Copy `01_prepare.py`, `02_depth_estimate.py`, `03_mesh_generate.py`, `04_export.py`
  from `pipeline-02-zoedepth/` as the starting point.
- Copy `utils/file_utils.py` and `utils/image_utils.py` — both have been updated.
- In pipeline-03's `requirements.txt`, **do not pin** `timm==0.9.16`. That pin exists only
  for ZoeDepth compatibility. Depth Anything V2 works with `timm>=1.0`.
- The ZoeDepth drop_path patch in `load_depth_model()` can be removed in pipeline-03
  since ZoeDepth is not being used.
- `rembg[gpu]` bracket syntax works in `requirements.txt` — keep it that way.

---

## First Successful Run Results (pipeline-02-zoedepth)

- **Input:** `human_one_person.jpg` — 5121×7678 px, 6.48 MB, RGB
- **Prepared:** `human_one_person_prepared.png` — 1201×1800 px, RGBA (background manually removed, then resized by script)
- **Depth model:** ZoeDepth (`ZoeD_NK`), CUDA, 6.3s inference
- **Depth output:** `human_one_person_prepared_zoedepth_standard_depth.png` (16-bit) + preview
- **Depth quality:** Arm extended toward camera = correctly closest (brightest). Head = close. Body fades to feet. Smooth gradient, no major artifacts. Approved for mesh step.
- **Run folder:** `one_person_v1`
