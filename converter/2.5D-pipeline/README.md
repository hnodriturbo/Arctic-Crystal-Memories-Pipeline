<!--
File: README.md
Purpose:
 - What the 2.5D pipeline does, how to install it, and why it exists next to
   the Meshy stage rather than instead of it.
-->

# 2.5D-pipeline

A photograph becomes a **relief**: a height field, deepest where the picture is
darkest, fitted to a crystal blank. The fourth stage in the converter project,
and the local answer to what Cockpit3D's AutoConvert-to-3D does on their server.

```txt
image-pipeline  →  2.5D-pipeline  →  pipeline-converter
photograph          relief mesh       point cloud the engraver reads
                    ↑
                    the alternative to meshy-pipeline, not a step after it
```

The **2.5D pipeline's acceptance boundary is the approved relief mesh**
(`relief.glb` / equivalent `relief.obj`). The point-cloud stage is a downstream
handoff to `pipeline-converter`; successful sampling does not prove that face
likeness, depth ordering or silhouette geometry is correct.

## Why this exists alongside Meshy

Meshy solves a **full 3D subject** — a bust with a back and sides that exist. It
does that by inventing the parts the photograph never showed. For a turbofan or
a church that is exactly right. For a specific real person on a memorial
crystal it is a product defect: a hallucinated ear is not a likeness.

A relief invents nothing. It only raises what is genuinely in the photograph,
which is why the whole sub-surface engraving industry uses relief for portraits
and full 3D mainly for objects and buildings.

Depth is also the binding constraint in glass. A 60×80×40 blank with a 1 mm
margin leaves 38 mm of engravable depth, and a full 3D head runs out of that
long before it runs out of height. A relief wants 10–20 mm and looks better for
using less.

## The two scripts

| Script             | What it does                                    | Model? |
|--------------------|-------------------------------------------------|--------|
| `depth_map.py`     | Photograph → 16-bit depth map                   | yes — the only one |
| `depth_to_mesh.py` | Depth map + photo → relief GLB **and** OBJ      | no     |

Everything after the first script is ordinary geometry. That is deliberate: the
depth engine can be swapped without any other file changing.

**Depth convention, fixed once so nothing downstream has to think about it:**
16-bit grayscale PNG, **bright = near = raised toward the viewer.** Depth
Anything predicts inverse depth and already reads that way; Marigold predicts
true depth and is flipped on the way out.

## Install

**Python 3.11, exactly** — same as the other three pipelines. The CPU torch
wheels are published per minor version and `healthcheck.py` fails the
environment on anything else.

```bash
python3.11 -m venv .venv                    # Windows: py -3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python code/download_models.py --model large
.venv/bin/python code/healthcheck.py
```

`download_models.py` is not optional in practice. Left to itself the first real
job also becomes a 1.3 GB download, which inside an SSE stream looks exactly
like a hung run.

This is a **fourth, separate venv**. It is not merged into `image-pipeline`'s:
that one is pinned to torch 2.1.2 + numpy 1.26.4 because basicsr and GFPGAN
need that exact ABI, and Depth Anything V2 wants a modern transformers on a
modern torch. Keeping them apart is what lets each stay on the pairing it
actually needs.

## Run it

```bash
# 1. depth
python code/depth_map.py \
    --input input/portrait-cutout.png --output output/depth.png \
    --engine depth-anything --model large --resolution 1024 --mask-from-alpha

# 2. canonical mesh — equivalent GLB and OBJ, then inspect and approve
python code/depth_to_mesh.py \
    --depth output/depth.png --photo input/portrait-cutout.png \
    --output output/relief.glb --obj output/relief.obj \
    --template 60x80x40 --relief-depth 16 --grid 512

# 3. downstream only after mesh approval — the existing converter
python ../pipeline-converter/code/mesh_to_pointcloud.py \
    --file output/relief.obj --texture input/portrait-cutout.png \
    --template 60x80x40 --upright y --toning 1.8 --layers 8 --stagger 2
```

Or drive all of it from the web UI: **2.5D pipeline → Build a relief**.

## The rule that matters most

`depth_to_mesh.py` writes the GLB and the OBJ from **one mesh**. The GLB is the
staging/approval artifact and the OBJ is the standard interchange copy consumed
later by the sampler. If those ever diverge there is no trustworthy approval,
so the geometry is built once and both writers receive the same arrays.

## Choosing an engine

- **`depth-anything`** (default) — feed-forward, seconds on GPU. Right for
  almost every photograph. `--model large` is the quality choice at ~1.3 GB.
- **`marigold`** — diffusion-based and much slower, but resolves the soft brow
  and cheek relief a portrait lives on, which Depth Anything can flatten into a
  mask-like slab. `--ensemble` is the real quality lever and is linear in time.

The reference service takes 1–3 minutes per subject, so there is no reason to
economise on the one stage that decides how much relief detail exists at all.

## Settings that actually change the result

- **`--relief-depth`** — the single most important number. 0 uses the blank's
  whole usable depth, which is almost always too much: a portrait at 38 mm of
  relief reads as a distorted mask. Try 10–20 mm.
- **`--mask-from-alpha`** — needs a cut-out PNG from `image-pipeline`. Without
  it the background gets relief too and the subject fights it for depth range.
- **`--smooth`** — depth noise becomes physical bumps on the surface, which the
  sampler then faithfully turns into stray dots. Some smoothing is wanted; too
  much flattens the face.
- **`--grid`** — vertex count on the long edge. 512 ≈ 400k vertices, plenty for
  both the preview and the sampler.
- **`--invert`** — only if the relief comes out inside-out, nose sunken instead
  of raised.

## Real crystal blanks

`code/import_blanks.py` reads a local Cockpit 3D installation and writes the
actual blank geometry into `blanks/` as centred millimetre GLBs plus one
`blanks.json` catalogue:

```bash
python code/import_blanks.py                 # default C:/ProgramData/Cockpit 3D
python code/import_blanks.py --source "..." --force
```

The viewer then frames a relief in the real shape. Two things the source files
do not do for you, both handled by the script:

- **The OBJ is not at template scale.** "Heart, Flat Bottom.obj" measures
  102.78 × 89.36 × 60 in its own units while its template says 125 × 110 × 47,
  and the three ratios differ — so the mesh is fitted per axis, not uniformly.
- **The OBJ is not centred.** Z runs 0..depth rather than ±depth/2.

Only Heart, Ornament and the Prestige families ship an `.obj`. Every
rectangular blank and cube is implicit — a box with a `BEVEL`, which is why the
viewer keeps a chamfered-box fallback and uses the template's own bevel value.

The templates also document a **per-axis `BORDER`**, and it is much larger than
a uniform 1 mm: the notched crystal declares `10 10 2`. Treat that as the
authoritative margin for these blanks rather than this pipeline's default.

`blanks/` is **git-ignored on purpose.** It regenerates in seconds on any
machine with the software, so Cockpit3D's asset files never travel further than
the machines already licensed to hold them. Internal preview use only.

## Folders

```txt
input/     photographs waiting to be built
output/    one folder per job: source, depth.png, relief.glb, relief.obj, job.json
models/    the Hugging Face cache, pointed here so weights do not land in ~/.cache
blanks/    imported crystal geometry (git-ignored, regenerate with import_blanks.py)
```

All git-ignored; only the structure is tracked.

**Nothing here is storage.** The web runner uploads every source photograph to
R2 under `relief-sources/<hash>-<name>` and mirrors each finished job to
`relief-jobs/<job-id>/`, then sweeps old local folders. Content-hashed keys mean
re-running the same photograph months later reuses its object instead of piling
up near-duplicates. `RELIEF_KEEP_JOBS` (default 5) sets how many job folders
stay on local disk; a job that failed to mirror is never swept, because
deleting the only copy of something is not a cleanup.

## Where the preview lives

`ACM-Web-Pipeline/src/components/CrystalPreview.jsx` renders the GLB inside a real
blank with three.js — `MeshPhysicalMaterial`, `transmission: 1`, `ior: 1.5168`,
`dispersion`. It reads GLB, point-cloud DXF and plain photographs, and it is
the prototype for the customer-facing viewer on acm.is. See
`../own_3d_preview_plan.md` for the whole plan and
`ACM-Web-Main/.Markdown/Guides/CRYSTAL_GLASS_VIEWER_PLAN.md` for the website
build.
