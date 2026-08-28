<!--
File: README.md
Purpose:
 - What the image pipeline does, how to install it, and why it is CPU-first.
-->

# image-pipeline

Photo clean-up, and the first of the three stages the converter project chains
together:

```txt
image-pipeline  →  meshy-pipeline  →  pipeline-converter
photograph          3D model           point cloud the engraver reads
```

Three scripts, run in that order when more than one is asked for:

| Script          | What it does                              | Needs a GPU?           |
|-----------------|-------------------------------------------|------------------------|
| `enhance.py`    | Face restoration, or tone and sharpness   | GFPGAN yes, pillow no  |
| `upscale.py`    | Enlarge to a target long edge             | Real-ESRGAN yes, lanczos no |
| `remove_bg.py`  | Cut the subject out onto transparency     | No                     |

## Why the order is fixed

Restore at native resolution, upscale the restored image, then cut out last.
Cutting first would upscale a matte whose edge decisions are already baked in,
and the silhouette is the single thing Meshy is most sensitive to.

## CPU first, GPU optional

The VPS has no CUDA, so the baseline install is CPU-only and every script says
what it fell back to rather than failing:

```bash
python3 -m venv .venv
source .venv/bin/activate           # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

That gives background removal at full quality — rembg runs on onnxruntime and
a portrait takes a few seconds — plus lanczos upscaling and pillow tone
adjustment.

On the workstation, add the GPU extras for Real-ESRGAN and GFPGAN:

```powershell
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu130
pip install -r requirements-gpu.txt
```

`--engine auto` then resolves to the AI engines. Without torch it resolves to
lanczos and pillow and says so in the output. **Do not install the GPU extras
on the VPS** — a CPU torch build is a 2 GB download and a Real-ESRGAN pass slow
enough to time out.

## Calling the scripts

Every script takes explicit `--input` and `--output` paths. Nothing writes to a
guessed filename in a fixed folder, so the web UI owns the whole temporary-file
lifecycle:

```bash
python code/remove_bg.py --input input/photo.jpg --output output/cutout.png \
    --model birefnet-portrait

python code/upscale.py --input output/cutout.png --output output/big.png \
    --target 2048

python code/enhance.py --input input/photo.jpg --output output/better.png \
    --engine pillow --sharpness 1.3 --contrast 1.1
```

## Choosing a cut-out model

- `birefnet-portrait` — people. The sharpest hair edges of the set, ~900 MB on
  first run.
- `birefnet-general` — objects, buildings, anything not a person.
- `isnet-general-use` — solid general fallback with a much smaller download.
- `u2net_human_seg`, `u2net` — older, softer, kept for comparison.

Models download to `~/.u2net/` on first use, not into this folder.

`remove_bg.py` prints what fraction of the frame the subject covers. Above 95%
means it found no subject at all and kept everything — usually the wrong model
for the picture rather than a broken image.

## Folders

```txt
input/     photographs to work on
output/    every stage's result, numbered in running order
models/    Real-ESRGAN and GFPGAN weights, downloaded on demand
```

All three are git-ignored; only the structure is tracked.
