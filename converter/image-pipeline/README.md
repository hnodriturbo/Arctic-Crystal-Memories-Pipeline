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
| `enhance.py`    | Face restoration, or tone and sharpness   | GFPGAN: GPU or explicit CPU; Pillow: CPU |
| `upscale.py`    | Enlarge to a target long edge             | Real-ESRGAN: GPU or explicit CPU; Lanczos: CPU |
| `remove_bg.py`  | Cut the subject out onto transparency     | No                     |

## Why the order is fixed

Restore at native resolution, upscale the restored image, then cut out last.
Cutting first would upscale a matte whose edge decisions are already baked in,
and the silhouette is the single thing Meshy is most sensitive to.

## Complete CPU environment, GPU optional

The VPS has no CUDA, but the complete CPU environment includes rembg,
Real-ESRGAN and GFPGAN:

```bash
python3 -m venv .venv
source .venv/bin/activate           # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Run `python code/download_models.py` once after installation. All six rembg
weights, GFPGAN and Real-ESRGAN then live in the shared model cache.

On a CUDA 12.1 workstation, replace only the paired CPU Torch wheels:

```powershell
pip install --force-reinstall torch==2.1.2+cu121 torchvision==0.16.2+cu121 `
  --index-url https://download.pytorch.org/whl/cu121
```

`auto` uses AI on CUDA and keeps the lightweight Pillow/Lanczos path on CPU.
Choose `gfpgan` or `realesrgan` explicitly to run the slower CPU AI pass. The
web runner serializes image chains so two large Torch jobs cannot exhaust the
6 GB VPS together.

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

Production preloads models into the shared `~/.u2net/` cache. They are not
duplicated inside releases or virtual environments.

`remove_bg.py` prints what fraction of the frame the subject covers. Above 95%
means it found no subject at all and kept everything — usually the wrong model
for the picture rather than a broken image.

## Folders

```txt
input/     photographs to work on
output/    every stage's result, numbered in running order
models/    shared rembg, Real-ESRGAN and GFPGAN weights
```

All three are git-ignored; only the structure is tracked.
