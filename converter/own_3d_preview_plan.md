<!--
File: own_3d_preview_plan.md
Purpose:
 - The plan for building Arctic Crystal Memories' own image-to-3D preview
   pipeline, in place of depending on Cockpit3D's AutoConvert-to-3D.
 - Part 1 is for people. Part 2 is the agent brief. Read Part 1 first either way.
-->

# Our own 3D preview pipeline

**Status: 2026-08-29.** The 2.5D pipeline and the glass viewer are built and
building. The website viewer is specified but not started. One investigation is
still outstanding and is described below.

---

# Part 1 — For people

## What we are actually replacing

3dcrystalglobal's portal has a button called **AutoConvert to 3D** (AC3D). You
give it a photograph, wait 1–3 minutes, and it shows you a rotatable model
sitting inside a crystal frame. Download gives you a `.cockpit` file that pulls
most of its data from their server.

We want the same capability, owned by us: a customer uploads a photograph on
acm.is, sees their crystal turning on screen before they buy, and the same
geometry becomes the dot cloud the engraver cuts.

## What AC3D probably is

We have no inside knowledge, so this is inference from behaviour:

- **1–3 minutes per subject.** That rules out a cheap feed-forward pass and is
  consistent with either a heavy depth model at high resolution, or a genuine
  3D reconstruction with ensembling. It is not a trade secret in the sense of
  being unobtainable — it is a well-resourced version of a public technique.
- **A relief in a crystal frame, before any point cloud exists.** The screenshot
  shows a surface, not dots. Point-cloud building is a separate later step, the
  same order our pipeline uses.
- **The preview is not the `.cockpit` file.** Almost certainly a lightweight web
  asset — GLB is the obvious candidate, a 16-bit depth PNG displaced in the
  browser is the cheap one. See the outstanding investigation below.

**There is no purchasable "AC3D".** It is their server-side service. But what it
does is a public class of problem with strong open models, which is the whole
basis of this plan.

## What is definitively known about their file format

Already established, recorded in
[`pipeline-converter/docs/format-notes.md`](pipeline-converter/docs/format-notes.md):

- `.cockpit` is a **ZIP archive**: `CockpitScene.xml` (plain readable UTF-8,
  carrying `PointXyDistance`, `PointZDistance`, `Toning`, `TrimToTemplate` and
  the blank name), plus `<random>.ci` geometry and `<random>.jpg` source photo.
- `.ci` has a fully understood 24-byte header (`CIBF`, version, vertex count,
  triangle count, floats/vertex, `CRUN`) and the size arithmetic is exact across
  every sample — **but the payload bytes are scrambled** by a length-preserving
  transform that was never identified. `CICockpit.exe` has packed .NET metadata,
  so the writer could not be read either.

**Conclusion, unchanged: do not try to author `.cockpit` files.** Reading the
scene XML for settings is easy and useful. The geometry is not writable.

What *is* plainly readable, and now used: `C:\ProgramData\Cockpit 3D\Shapes\**\*.obj`
are ordinary Wavefront OBJ, and `Templates\*.template` are trivial text.
`2.5D-pipeline/code/import_blanks.py` reads both into `blanks/` as centred
millimetre GLBs so the viewer frames a relief in the real product shape.

**Owner decision (2026-08-29): internal use, on the grounds that the crystals
themselves are purchased from Cockpit3D and these files describe those exact
blanks.** `blanks/` is git-ignored and regenerates in seconds on any machine
with the software, so their asset files never travel further than machines
already licensed to hold them. Shipping them in a public acm.is bundle is a
separate decision that has not been made.

What the import gives you, from 54 templates and 23 shape meshes:

- **22 real blank shapes** — Heart, Ornament and the Prestige families. Every
  rectangle and cube is implicit: a box with a `BEVEL`, which is why the viewer
  keeps a chamfered-box fallback. The AC3D screenshots show exactly that box,
  so the fallback is the *correct* shape for them, not a compromise.
- **31 templates that document a per-axis `BORDER`**, and it is far larger than
  a uniform 1 mm — the notched crystal declares `10 10 2`. That is authoritative
  margin data we did not have before and it directly affects fit.

## This ground has been walked before — read `pipeline-old/` first

**Do not treat the 2.5D pipeline as a first attempt.** `ACM-Pipeline/pipeline-old/`
holds three earlier runs at exactly this problem, and they contain findings that
cost real time to learn:

| Folder | What it was | What to take from it |
|---|---|---|
| `pipeline-01-depth-anything/` | 6-stage: upscale → bg → **facial landmarks** → depth → mesh → export → crystal scale | `md_helpers/03-depth-guide.md` — the `DEPTH_PROFILES` silhouette treatments, now ported into `depth_map.py --edge-profile` |
| `pipeline-02-zoedepth/` | ZoeDepth attempt, later restructured | `md_helpers/pipeline-02-zoedepth-changes.md` — why the order of operations changed, and the resolution finding below |
| `pipeline-03-pro/` | The consolidation attempt | `md_helpers/pipeline-guide.md` |
| `docs/texture-mesh-research.md` | Full survey of texture-mesh tooling, 2026-05-30 | Why laser **power** per point, not just position, is what carries likeness |

Three findings from that work that are already applied here:

1. **Depth models resize internally to ~384–518px, and going higher does not
   help.** Enlarging the photo before the processor accomplishes nothing — it
   resizes straight back down. `depth_map.py` now overrides the processor's
   `size` so `--resolution` genuinely applies, and then measurement confirmed
   the old finding for a deeper reason. On a 960px portrait, Large, CPU:

   | inference size | time | Laplacian detail energy |
   |---|---|---|
   | native ~518px | 25s | 3.12e-05 |
   | override 1024px | 66s | 3.03e-05 (**0.97×**) |

   2.6× the runtime for slightly *less* fine detail. Off the training
   distribution the ViT changes the map without improving it. **Resolution is
   not a quality knob** — quality has to come from the engine (Marigold) or
   from facial enhancement (T7). Default stays 0.
2. **Cut out before resizing, never after.** rembg on a 10K upscaled image tries
   to allocate ~29 GB and dies; at native resolution it also produces better
   hair edges. `image-pipeline`'s fixed order already reflects this.
3. **100K–500K triangles is the production sweet spot** for Cockpit3D — beyond
   that the meshes are slow to review and impractical to send to engravers.
   `--grid 512` lands at ~520K triangles; `--grid 384` (~294K) is squarely in
   range and is the safer default for customer-facing work.

And one that is **not yet applied**, and is the most interesting of them:
`pipeline-01` had `03b_facial_landmarks.py`, and `03-depth-guide.md` proposes a
"Step 3.5 — facial depth enhancement". A generic depth model treats a face as
just another surface; landmark-guided enhancement lets the nose, brow and lips
get the relief a portrait actually needs. That is task **T7** below.

The `texture-mesh-research.md` framing is also worth internalising: position
drives shape, but **laser power per point drives likeness** — the shadows under
the eyes, the highlight on the nose. `mesh_to_pointcloud.py --texture` and the
vertex colours `depth_to_mesh.py` writes are both serving that, not decoration.

## What is built now

```txt
image-pipeline  →  2.5D-pipeline  →  pipeline-converter
photograph          relief mesh       point cloud (DXF)
                    ↑ NEW
                 meshy-pipeline  →  pipeline-converter
                 full 3D subject
```

**`2.5D-pipeline/`** — two scripts. `depth_map.py` runs Depth Anything V2 or
Marigold and writes a 16-bit depth PNG. `depth_to_mesh.py` turns that into a
relief mesh, exported as **both** GLB (browser) and OBJ (sampler) from one
geometry. Python 3.11, own venv, own model cache.

**`web-converter/src/components/CrystalPreview.jsx`** — three.js viewer that
renders a GLB, a point-cloud DXF, or a plain photograph inside a real K9 blank,
with `MeshPhysicalMaterial` transmission, `ior: 1.5168` and dispersion.

**`web-converter`** — new sidebar step 3 with two tabs: *Build a relief* and
*Crystal viewer*. Sources come from direct upload, the image pipeline handoff,
or the durable R2 photo library. Finished reliefs hand their OBJ straight to the
converter with the blank already selected.

**Storage rule, enforced in code.** The VPS holds working files only. Every
source photograph goes to R2 as `relief-sources/<content-hash>-<name>`, every
finished job mirrors to `relief-jobs/<job-id>/`, and old local folders are
swept — but only ones confirmed present in the bucket.

## The face question

The Meshy turbofan is excellent, and Meshy's newest models do faces genuinely
well. So: should portraits go through Meshy, or through the relief pipeline?

**For a specific real person, the relief pipeline. Every time.**

A generative 3D model produces a *plausible* head. It invents the back, the
sides, the ear the photograph never showed. For a game asset that is the
feature. For a memorial crystal of someone's grandmother it is the product
failing: the family knows what she looked like, and an invented cheekbone reads
as wrong without anyone being able to say why. A relief cannot make this
mistake, because it only raises what is actually in the photograph.

This is almost certainly why the industry — Cockpit3D and 3dcrystal included —
uses relief for portraits and full 3D mainly for objects and buildings.

### If we do want real 3D heads later

The right tool is **not** a generic image-to-3D model. It is a **parametric head
model**, which constrains the geometry to the space of real human heads so it
*cannot* hallucinate a non-face. Options, with licensing as the deciding factor:

| Option | What it is | Commercial use |
|---|---|---|
| **FLAME** (Max Planck) | The standard 3D head morphable model, with a real expression space. Most avatar work builds on it. | Free for research; **commercial licence available from Max Planck Innovation** — this is the "buy access" answer |
| **DECA / EMOCA / MICA** | Research pipelines that fit FLAME from a single photograph | Typically non-commercial, and they inherit FLAME's licence |
| **Avatar SDK (itSeez3D)** | Commercial API, selfie → rigged 3D head | Straightforwardly purchasable |
| **Didimo** | Commercial API, photo → rigged avatar with expressions | Straightforwardly purchasable |
| **Basel Face Model** | Older 3DMM | Licensable |
| **Hunyuan3D / TRELLIS** | Open-weight general image-to-3D, self-hostable | Permissive, but generic — same hallucination problem |
| **Rodin / Hyper3D, Tripo3D** | Commercial APIs, strong on characters | Purchasable, same generic caveat |
| **MetaHuman (Epic)** | Superb faces | **Check the EULA carefully** — it is written around use inside Epic's ecosystem, which is a poor fit for engraving a physical product |

**Recommendation: do not buy any of these yet.** Ship the relief pipeline,
engrave real portraits, and see whether customers actually ask for a full 3D
head. If they do, FLAME under a commercial licence is the honest starting point,
because it is the only one on that list whose geometry is constrained to be a
real human face.

## Outstanding investigation — needs your browser

**I could not do this one.** Not a permissions issue: I have no browser tool in
this session, and their preview sits behind a login I cannot and should not
drive. It takes about fifteen minutes and it settles the last open question.

1. Open the 3dcrystalglobal portal, DevTools → **Network**, clear it.
2. Run AutoConvert to 3D on any photograph.
3. When the preview appears, look at what was downloaded. Filter Fetch/XHR, then
   check **Other** and **Img** too.
4. Record: the file extension, the size, the `Content-Type`, and whether
   `view-source` mentions `three`, `babylon` or `model-viewer`.

What each answer means:

- **A `.glb` / `.gltf` arrives** → they do exactly what we now do. Our GLB path
  is already correct and there is nothing further to learn.
- **A `.png` arrives and the page loads three.js** → they ship a depth map and
  displace it in the browser. Cheaper than us on bandwidth. Worth copying:
  `depth.png` already exists in every one of our job folders, so it is a viewer
  change only, not a pipeline change.
- **A `.ply` / `.drc`** → they send a point cloud straight to the browser, which
  would be a stronger preview than a relief surface and is a real option for us
  once a DXF exists.

Whatever it is, write it into this file under a dated heading.

## Honest limits

- **We will not match their speed on the current VPS,** and per your own note we
  do not need to — 1–3 minutes is the bar, not seconds. But `image-pipeline`'s
  README is right that the VPS is CUDA-less with 6 GB, so Marigold with a large
  ensemble will be minutes on CPU. Options in order of sanity: compute the
  preview at save time rather than live; a GPU box for batch work; a hosted
  inference API.
- **Toning is not code, it is calibration.** `Toning 1.8` is Cockpit3D's
  documented default and `mesh_to_pointcloud.py` already implements the same
  idea, but matching their *look* in glass is a matter of test engravings across
  layer count, stagger and dot pitch. No amount of software gets there without
  burning some blanks.
- **`.cockpit` authoring stays closed.** Settled, do not revisit.

---

# Part 2 — Agent brief

You are working in `ACM-Pipeline/converter/`. Read `converter/README.md` and
`AGENTS.md` at the repo root before changing anything. Part 1 above is context;
this part is the contract.

## Repository map

```txt
converter/
├── image-pipeline/       Python 3.11 · photo clean-up (rembg, GFPGAN, Real-ESRGAN)
├── meshy-pipeline/       workspace · full 3D via the Meshy API (Node client lives in web-converter)
├── 2.5D-pipeline/        Python 3.11 · photo → depth → relief mesh          ← newest
├── pipeline-converter/   Python 3.11 · mesh → POINT-cloud DXF for the SSLE engraver
└── web-converter/        Next.js 16 · drives all four
```

Each Python pipeline has **its own venv and its own `requirements.txt`**. They
are not interchangeable and must never be merged — `image-pipeline` is pinned to
torch 2.1.2 / numpy 1.26.4 for basicsr's ABI, `2.5D-pipeline` needs a modern
torch for transformers.

## Invariants — do not break these

1. **One mesh, two exports.** `depth_to_mesh.py` writes the GLB and the OBJ from
   the same geometry. The GLB is what the customer sees; the OBJ is what becomes
   laser dots. If they ever diverge, the preview stops being a promise about the
   product. This is the reason the pipeline exists.
2. **Depth convention is fixed:** 16-bit grayscale PNG, bright = near = raised.
   Engines normalise *to* this, never away from it.
3. **The VPS is a workspace, not storage.** Durable data lives in R2.
   `lib/relief/library.js` owns this; `pruneLocalJobs()` never removes a folder
   it has not confirmed in the bucket.
4. **Axes:** X = width, Y = height (up), Z = depth toward the viewer, millimetres,
   centred on the origin. This is what `mesh_to_pointcloud.py --upright y`
   expects. Do not introduce a Z-up path.
5. **Blank names are their own dimensions.** Every key in `CRYSTAL_TEMPLATES`
   (`printer_dxf.py`) and `CRYSTAL_BLANKS` (`crystal-blanks.js`) is literally
   `WIDTHxHEIGHTxDEPTH`. Parse the name; do not add a fourth copy of that table.
   `printer_dxf.py` stays authoritative for the real fit.
6. **Python 3.11 exactly**, all four pipelines. `healthcheck.py` enforces it.
7. **Do not attempt `.cockpit` authoring.** Closed question, see Part 1.

## File ownership

| Concern | Owner |
|---|---|
| Depth estimation | `2.5D-pipeline/code/depth_map.py` — the only file with a model in it |
| Relief geometry | `2.5D-pipeline/code/depth_to_mesh.py` |
| Blank dimensions, fit, dot spacing | `pipeline-converter/code/utils/printer_dxf.py` |
| Form fields + argv | `web-converter/src/lib/relief/catalog.js` — a new flag is added here and nowhere else |
| Job orchestration, R2, pruning | `web-converter/src/lib/relief/{chain,library,state}.js` |
| Glass rendering | `web-converter/src/components/CrystalPreview.jsx` |
| Pipeline roots and venvs | `web-converter/src/lib/paths.js` |

## Commands

```bash
# 2.5D-pipeline
python3.11 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python code/download_models.py --model large
.venv/bin/python code/healthcheck.py          # JSON; non-zero exit means unusable

# web-converter
npm run dev
npx eslint src/...          # required before finishing
npm run build               # required before finishing
```

## Open tasks

Ranked. Each has an acceptance test — do not mark one done without it.

### T1 · Prove the pipeline end to end on a real portrait
**Done for a smoke test (2026-08-29), not yet judged by eye.** The venv is
installed (Python 3.11.9, torch 2.13.0+cpu, transformers 5.16.1, trimesh 5.0.0)
and the full chain runs on `input/test-portrait.jpg`:

```txt
depth_map.py       Large, native size, CPU    25s
depth_to_mesh.py   512 grid, 16mm relief      262,144 verts / 522,242 tris
                   GLB 10.4 MB, OBJ 21 MB, vertex colours 0..255
mesh_to_pointcloud.py --texture --toning 1.8 --layers 8 --stagger 2
                   101,248 points, 4.6 MB DXF, Z centred at ±8mm
```

Geometry verified: bounds are millimetres, centred, X=width Y=height Z=depth.
The browser DXF parser reads that file back to exactly 101,248 points.

**Still open, and it needs your eyes not a test:** run a real cut-out portrait
(this smoke test used a photo with no alpha, so the whole rectangle got
geometry) and judge it in the Crystal viewer. Record the `--relief-depth` that
looked right in `2.5D-pipeline/README.md` — that number is the one thing no
document can tell you in advance.
**Watch for:** relief inside-out (`--invert`), background stealing depth range
(`--mask-from-alpha` needs a cut-out PNG from the image pipeline), a face
flattened into a slab (try `--engine marigold`).

### T2 · The DevTools investigation
**Assigned to Claude Cowork (2026-08-29), which is delivering its own md file.**
Part 1 has the procedure and what each answer means. Fold the result into Part 1
under a dated heading when it arrives.

### T3 · Freeze the dependency pins
The Windows install resolved to torch 2.13.0+cpu, transformers 5.16.1,
diffusers 0.40.0, trimesh 5.0.0, numpy 2.4.6, Python 3.11.9 — and the code works
against transformers 5.x, which is worth knowing because the v4→v5 API change
was the main risk in this stack.
**Remaining:** `pip freeze > requirements.lock.txt` on Windows, then install and
freeze again on the VPS.
**Accept when:** both lock files exist and a fresh venv from one passes
`healthcheck.py`.

### T4 · Image-pipeline → 2.5D handoff button
`/api/handoff` already accepts `to: "relief-input"`. `ImageClient.jsx` only
offers *Send to Meshy*.
**Accept when:** a cut-out in the image pipeline can be sent to the 2.5D tab in
one click, the way it can be sent to Meshy today.

### T5 · Depth-map preview mode in the viewer
Every job folder already has `depth.png`. Add a `kind: "depth"` branch to
`CrystalPreview.jsx` that displaces a plane in the browser from the 16-bit PNG.
**Accept when:** the depth branch and the GLB branch of the same job are visually
indistinguishable. That equivalence is what would let acm.is ship ~200 KB per
preview instead of several MB. Blocked on nothing; T2 informs whether it is
worth prioritising.

### T7 · Facial depth enhancement — the highest-value open idea
`pipeline-old/pipeline-01-depth-anything/03b_facial_landmarks.py` exists, and
`md_helpers/03-depth-guide.md` proposes it as "Step 3.5". A generic depth model
treats a face as one more surface; landmark-guided enhancement gives the nose,
brow, lips and eye sockets the relief a portrait lives on.

This is almost certainly a large part of why AC3D's portraits look as good as
they do, and it is the single most likely reason a first relief run looks
technically correct but subtly lifeless.

Read the old script before writing a new one.
**Accept when:** the same portrait, run with and without enhancement, shows
visibly more defined nose and brow relief in the Crystal viewer, without the
face reading as a caricature.

### T6 · Batch mode
One relief at a time is fine interactively; a shop order of twenty is not.
`runReliefChain` already serialises through `withReliefSlot`.
**Accept when:** a queue survives a browser tab closing, the way Meshy jobs do.

## Gotchas already paid for

- **`transmission` renders flat black without an environment map.** `RoomEnvironment`
  + `PMREMGenerator` is why the glass looks like glass. Removing it does not
  make it dimmer, it makes it wrong.
- **Additive blending is not a style choice.** Each laser dot is a microfracture
  that scatters light outward, so dots stacking along the view axis genuinely
  get brighter. That is the mechanism behind toning, and additive is what
  reproduces it.
- **Quads are dropped whole at the silhouette, never clipped.** Clipping produces
  sliver triangles, and the point sampler distributes dots by triangle area, so
  slivers become bright seams around the subject.
- **Percentile normalisation, not min/max.** One stray predicted pixel at an
  extreme value otherwise takes the whole useful range and leaves the face in
  the middle 5%.
- **Depth noise becomes physical bumps.** `--smooth` is not cosmetic.
- **`purify_dxf.py` only understands POINT entities.** A mesh DXF run through it
  comes out empty — `mesh_to_pointcloud.py` first, always.
- **Windows heredocs eat backslashes.** Write files with an editor tool, not a
  shell heredoc, when the content contains `\` or regex escapes.

## Related documents

- [`2.5D-pipeline/README.md`](2.5D-pipeline/README.md) — the pipeline itself
- [`pipeline-converter/docs/format-notes.md`](pipeline-converter/docs/format-notes.md) — Cockpit3D formats, `.ci`, `.cockpit`
- [`pipeline-converter/CLAUDE.md`](pipeline-converter/CLAUDE.md) — the point-cloud stage
- `ACM-Web-Main/.Markdown/Guides/CRYSTAL_GLASS_VIEWER_PLAN.md` — the acm.is viewer
