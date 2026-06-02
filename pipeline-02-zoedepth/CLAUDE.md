# pipeline-02-zoedepth — Memory
<!-- Living memory for pipeline-02-zoedepth. Keep this focused on local pipeline progress. -->

---

## Pipeline File Status

| File                    | Status   | Notes |
| ----------------------- | -------- | ----- |
| `utils/file_utils.py`   | modified | Added `prepared` stage to `STAGE_OUTPUT_DIRS`; removed `upscaled`/`nobg` |
| `utils/image_utils.py`  | modified | Added `compute_target_size`, `resize_image`, `extract_alpha_mask` |
| `01_prepare.py`         | new      | Merged bg removal + aspect-ratio-safe resize; reads from `input/` |
| `02_depth_estimate.py`  | modified | Was `03_depth_estimate.py`; reads from `output/prepared/` |
| `03_mesh_generate.py`   | renamed  | Was `04_mesh_generate.py`; unchanged otherwise |
| `04_export.py`          | renamed  | Was `05_export.py`; stub only — not implemented |

---

## Last Worked On

**2026-05-31** — Pipeline restructured: merged upscale+bg removal into `01_prepare.py`, renumbered all scripts, `prepared` stage replaces `upscaled`/`nobg`. Aspect-ratio functions moved to `image_utils.py`.

**2026-05-30** — Documentation restructured. `pipeline-guide.md` is now the official guide at the pipeline root. Pipeline-local `INSTRUCTIONS.md` and copied `md_helpers/pipeline-setup.md` were removed in favor of root `md_helpers/pipeline-setup.md`.

---

## Pipeline Purpose

This pipeline is an isolated ZoeDepth test environment. It exists because ZoeDepth is incompatible with `timm >= 1.0`, while `pipeline-01` should remain clean for Depth Anything V2 and other model experiments.

---

## Known Issues & Setup Notes

- ZoeDepth uses `torch.hub.load("isl-org/ZoeDepth", "ZoeD_NK", pretrained=True)` inside `02_depth_estimate.py`.
- The `drop_path` fix is already in `02_depth_estimate.py`: timm 0.9.x BeiT `Block` stores the layer as `drop_path1` but MiDaS hub code calls `self.drop_path` — the script patches `Block.__init__` to alias it before loading ZoeDepth.
- `requirements.txt` pins `timm==0.9.16` to avoid the ZoeDepth `Block.drop_path` failure seen in `pipeline-01`.
- `04_export.py` is intentionally only a stub. Do not implement it during the ZoeDepth setup task.
- Pipeline order is: bg removal → resize → depth → mesh (no upscaling step).
- Aspect ratio rule: always use `compute_target_size()` from `image_utils.py` — never compute target dimensions inline.
- If the virtual environment is rebuilt, reapply the `basicsr` import patch from root `md_helpers/pipeline-setup.md`.

---

## Pipeline Run Results

No pipeline stages have been run yet in `pipeline-02-zoedepth`.

---

## Key Decisions Made

- Default depth model changed to `DEPTH_MODEL=zoedepth`.
- The new pipeline gets its own virtual environment so dependency pins do not disturb `pipeline-01`.
- Sample images from root `input_images_samples/` were copied into this pipeline's `input/` folder.
