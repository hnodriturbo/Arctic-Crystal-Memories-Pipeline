<!--
File: README.md
Purpose:
 - What the 2.5D pipeline does, how to install it, and why it exists next to
   the Meshy stage rather than instead of it.
-->

# 2.5D-pipeline

A photograph becomes a **relief**: a learned height field, fitted to a crystal
blank without treating ordinary image darkness as physical depth. It is the fourth stage in the converter project,
and the local answer to what Cockpit3D's AutoConvert-to-3D does on their server.

```txt
image-pipeline → global depth → face refinement → head prior → surface depth → crystal tone → relief mesh
photograph         MoGe 9/9       crops + 468 QA      GNM Head v3   MoGe normals     RGB luminance   Blender GLB
```

The native acceptance contract is deliberately narrow:

```txt
photograph → dense 3D/2.5D triangular geometry → aligned texture + mask
```

The job is complete only when those three outputs are approval-ready. Blender,
ACM Scene Composer, point-cloud generation and DXF conversion are downstream
consumers; they must not be used to hide incorrect likeness, anatomy, depth
ordering, silhouette or surface detail in the native mesh.

Research challengers such as HRN, MICA and ECON live under `Models/research/`.
Their code, checkpoints and outputs are evaluation-only until their licences
and any required commercial permissions have been verified. Evaluation output
must remain labelled and must not silently replace a production stage.

## Why this exists alongside Meshy

Meshy solves a **full 3D subject** — a bust with a back and sides that exist. It
does that by inventing the parts the photograph never showed. For a turbofan or
a church that is exactly right. For a specific real person on a memorial
crystal it is a product defect: a hallucinated ear is not a likeness.

A portrait relief must not invent unconstrained identity. Controlled face,
head and body priors may infer missing volume where one photograph is
geometrically ambiguous, but the inferred anatomy must stay anchored to the
visible silhouette, landmarks, depth ordering and texture. This distinction is
what lets the pipeline form a rounded cheek, forehead or skull without treating
a hallucinated ear or hairstyle as verified likeness.

Depth is also the binding constraint in glass. A 60×80×40 blank with a 1 mm
margin leaves 38 mm of engravable depth, and a full 3D head runs out of that
long before it runs out of height. A relief wants 10–20 mm and looks better for
using less.

## The six active scripts

| Script             | What it does                                    | Model? |
|--------------------|-------------------------------------------------|--------|
| `depth_map.py`     | Photograph → global 16-bit depth map            | yes — MoGe-2 ViT-L 9/9 is production |
| `face_refine.py`   | Detect/refine every face → fused 16-bit depth   | yes — YuNet + MoGe face crops |
| `gnm_head_refine.py` | 468 points → fitted skull/face volume       | yes — Google GNM Head v3 |
| `detail_refine.py` | Normals → bounded surface micro-depth           | no new model — integrates MoGe normals |
| `appearance_refine.py` | RGB → monochrome crystal tone/detail map  | no — multi-scale perceptual lightness |
| `depth_to_mesh.py` | Depth + selected texture → relief GLB/OBJ       | no     |

The stages are deliberately separate so macro scene order, face shape and fine
surface orientation and visible crystal detail can be inspected independently.
The appearance stage preserves beard, hair, eyelid and wrinkle contrast without
turning colour or cast shadows into false millimetres of geometry.

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
.venv/bin/python code/download_models.py --baseline
.venv/bin/python code/healthcheck.py
```

`download_models.py` is not optional in practice. Left to itself the first real
job also becomes a multi-gigabyte download, which inside an SSE stream looks
exactly like a hung run. `--baseline` materialises MoGe-2 vitb-normal,
MoGe-2 vitl-normal and Apple Depth Pro in named folders under `Models/`.

This is a **fourth, separate venv**. It is not merged into `image-pipeline`'s:
that one is pinned to torch 2.1.2 + numpy 1.26.4 because basicsr and GFPGAN
need that exact ABI, and Depth Anything V2 wants a modern transformers on a
modern torch. Keeping them apart is what lets each stay on the pairing it
actually needs.

## Run it

```bash
# 1. global depth plus the normal/mask maps used later
python code/depth_map.py \
    --input input/portrait-cutout.png --output output/depth.png \
    --engine moge-2 --moge-model vitl --moge-resolution-level 9 \
    --aux-output output/geometry --mask-from-alpha

# 2. mandatory face detection/refinement (no faces becomes a proven pass-through)
python code/face_refine.py \
    --input input/portrait-cutout.png --depth output/depth.png \
    --output output/refined-depth.png --moge-model vitl \
    --moge-resolution-level 9

# 3. automatic parametric skull/face depth for every measured face
python code/gnm_head_refine.py \
    --depth output/refined-depth.png --faces output/refined-depth.json \
    --photo input/portrait-cutout.png --output output/head-refined-depth.png \
    --qa-dir output/head-refinement --head-span 0.34 \
    --front-headroom 0.12 --back-headroom 0.12 \
    --feather 24 --silhouette-taper 12

# 4. conservative detail for eyelids, facial planes, hair/fur and surfaces
python code/detail_refine.py \
    --depth output/head-refined-depth.png --normal output/geometry/normal.png \
    --mask output/geometry/mask.png --output output/final-depth.png \
    --aux-output output/detail-refinement

# 5. crystal appearance — visible detail, explicitly not physical depth
python code/appearance_refine.py \
    --input input/portrait-cutout.png --output output/crystal-tone.png \
    --aux-output output/appearance-refinement --toning 1.8

# 6a. RGB inspection GLB and canonical OBJ
python code/depth_to_mesh.py \
    --depth output/final-depth.png --photo input/portrait-cutout.png \
    --output output/relief.glb --obj output/relief.obj \
    --template 60x80x40 --relief-depth 16 --grid 512

# 6b. same geometry with the monochrome crystal appearance
python code/depth_to_mesh.py \
    --depth output/final-depth.png --photo input/portrait-cutout.png \
    --texture-image output/crystal-tone.png \
    --output output/relief-crystal.glb \
    --template 60x80x40 --relief-depth 16 --grid 512
```

Or drive all of it from the web UI: **2.5D pipeline → Build a relief**.

### Mandatory face rule

`face_refine.py` runs on every native job. YuNet detects multiple faces; an
upstream UI or API can instead supply repeated `--face-box` values and
`--known-face-count`. A declared face-count mismatch is a hard failure, never a
silent unrefined export. When no face exists, the stage writes an unchanged
depth plus explicit `face_refinement_required: false` provenance.

The current production refinement is local MoGe-2 ViT-L 9/9 crop fusion. It
raises the effective model resolution around eyes, nose, lips and jaw, aligns
the local crop back to global scene depth, and feather-blends the correction so
the body and background ordering cannot jump at the face edge.

### Parametric-head rule

`gnm_head_refine.py` runs after face-crop refinement and before surface
micro-detail. It fits the Apache-2.0 Google GNM Head v3 model independently to
all 468 MediaPipe landmarks on every detected face. Only the broad,
low-frequency skull, forehead, cheek, nose, chin and neck form comes from GNM;
MoGe depth and normals retain the photograph-specific beard, hair, eyelid,
wrinkle and skin detail. A no-face job is an explicit pass-through. QA writes
the landmark fit, the head prior, before/prior/after depth, and one fitted GNM
OBJ per face. Before fitting, the human depth is centred with 12% free space at
both the front and back of its normalized envelope. This prevents the nearest
nose or the farthest skull surface from being clipped at 0/1 while the anatomy
prior is moving it.

### Surface-detail rule

`detail_refine.py` integrates MoGe normals into a height field, retains only a
controlled medium/high-frequency band, suppresses corrections at depth jumps
and caps the added range. It does not turn RGB brightness into geometry: beard
colour, make-up and cast shadows must not become deep grooves. This generic
stage applies to people, pets, fur, feathers, cloth and hard-surface objects.
Its default 0.018 strength is intentionally subtle; broad head/body shape still
belongs to MoGe and face refinement.

### Crystal-appearance rule

`appearance_refine.py` produces a separate grayscale texture. It combines
perceptual lightness with bounded local and micro contrast so beard hairs,
eyelids, wrinkles, hair and fabric survive the crystal preview. This map must
never be substituted for the depth map and is not a laser-power calibration.
The web pipeline exports both `relief.glb` (RGB) and `relief-crystal.glb`
(monochrome), built from exactly the same final geometry.

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
- **Depth profiles** — the web UI and Composer share `shallow` (up to 8 mm),
  `balanced` (up to 16 mm), `deep` (up to 24 mm) and exact `custom`; every
  profile is clamped to the selected blank's usable depth.
- **`--grid`** — vertex count on the long edge. Auto-grid targets roughly
  0.12 mm spacing and is capped at 512, keeping a 1:1 80 mm test GLB near
  10 MB instead of producing an unnecessarily huge file.
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

All 27 locally extracted 2D Cockpit templates are exposed in the web form.
Named template IDs are resolved to exact millimetre dimensions before Python is
called; specialised Heart, Ornament and Prestige meshes are used where local
GLBs exist, and the remaining templates use the dimension-correct bevelled-box
preview.

`blanks/` is **git-ignored on purpose.** It regenerates in seconds on any
machine with the software, so Cockpit3D's asset files never travel further than
the machines already licensed to hold them. Internal preview use only.

## Folders

```txt
input/     photographs waiting to be built
output/    one folder per job: source, staged depth maps, QA images and relief mesh
Models/    direct model folders plus the local Hugging Face cache
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
build. The relief page defaults to the monochrome surface GLB, provides
before/both/after and RGB/crystal toggles, and downloads the approved GLB for
ACM Scene Composer in Blender. Point display remains only an optional future
production check.
