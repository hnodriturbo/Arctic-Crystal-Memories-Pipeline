<!--
File: cockpit-reconstruct-handoff.md
Purpose:
 - Agent brief for building the "Cockpit Reconstruct" feature: turning a
   Cockpit3D DXF/CAD point-cloud export into a colored, web-ready GLB, first
   as an operator tool inside ACM-Web-Pipeline (pipeline.acm.is).
 - Part 1 is for people. Part 2 is the agent brief. Read Part 1 first either
   way. Written for a coding agent (Claude Code / Codex) running locally with
   full filesystem and git access to this workspace.
-->

# Cockpit Reconstruct — DXF/CAD point cloud → colored GLB

## Implementation update — 2026-09-13

The owner rejected raw Delaunay reconstruction as visually inadequate and authorized
a better surface estimator. The dedicated module now offers continuous relief:
front-layer quantiles, silhouette closing, interior depth interpolation, smoothing,
and grid triangulation, plus full photo texture or vertex colors. Raw Delaunay stays
available for comparison. This is a material extension of T1, explicitly requested.

The owner confirmed the reference-gallery `amma-1.dxf` was exported from Cockpit,
then selected `*Amma-og-Afi-Tester-Output*` for the next tests. See
`pipeline-converter/docs/cockpit-reconstruct.md` for exact results, remaining
lettering artifacts and the provisional photo pairing. Visual fidelity remains
in review. No ACM-Web-Main changes or deployment were made.

The owner also requested removal of top-level `pipeline/` and `pipeline-old/`;
these were removed after preserving input photographs. `converter` →
`Main-Pipelines-Web` remains pending a Windows lock held by Blender MCP runtimes.

**Status: 2026-09-13.** Nothing described here is built yet. This document
is the full brief for Phase 1 only. Phase 2 (a customer-facing showcase
page on `ACM-Web-Main` / www.acm.is using the GLBs this phase produces) is
explicitly out of scope for this pass — see "Stop condition" below.

---

# Part 1 — For people

## What problem this solves

Arctic Crystal Memories wants a page where customers can see and rotate
already-made 3D crystal pieces. The obvious source data is the `.cockpit`
scene files Cockpit3D produces per order — but `.cockpit` is a ZIP
containing a `.ci` geometry file whose payload bytes are **scrambled by an
unidentified, length-preserving transform** (documented in
`own_3d_preview_plan.md` and `pipeline-converter/docs/format-notes.md`,
investigated 2026-08-29, explicitly marked closed — do not re-investigate
that transform in this task).

The actual usable path is different, and already half-built:

**Cockpit3D itself can export a scene as DXF or CAD** — a plain-text point
cloud, no encryption, no mystery. `pipeline-converter/code/convert_dxf.py`
and `convert_cad.py` **already parse these formats today** into
`xyz/ply/obj/stl`. A real example already exists on disk:
`ACM-Pipeline/converter/2.5D-pipeline/reference-gallery/cockpit-files/exported/amma-exports/amma-1.dxf`
(227 MB, ~4.4 million points) plus sibling `.cad`/`.cbf`/`.rmd` exports of
the same scene.

What's missing is small and well-scoped — and it runs **backwards** through
the normal pipeline order. Normally: smooth relief/mesh → rasterize →
sparse laser-dot point cloud (what the engraver reads). Here we only have
the point cloud (the DXF/CAD export), and want to go back the other way —
point cloud → reconstructed smooth surface → GLB — so the web viewer shows
something closer to the soft, continuous relief look (like the pre-
rasterization preview), not a sparse cloud of dots:

1. **Surface reconstruction + GLB output.** `convert_cad.py`/`convert_dxf.py`
   already support `--formats stl --stl-method delaunay` — triangulating the
   raw point cloud into a **2.5D surface mesh** (there's also `convex` for a
   closed hull). This is already the "point cloud → smooth surface" step;
   it just doesn't export GLB yet, only STL. The task is to reuse that same
   triangulated mesh and add a GLB export path alongside it — not to build a
   separate sparse-point GLB. A raw `POINTS`-mode GLB (rendering dots, not a
   surface) is explicitly **not** the goal here.
2. **Per-vertex color from the paired photo.** Neither `.cad` nor `.dxf`
   carries confirmed RGB columns (`format-notes.md`: "No confirmed RGB or
   color columns have been identified yet"). The `.cockpit` file paired
   with an export **does** contain the real customer photo (a plain JPEG
   inside the same ZIP) — that photo can be back-projected onto the
   triangulated mesh's vertices to color it, since the point cloud came
   from projecting that exact photo in the first place.
3. **An operator page** to iterate on 1 and 2 quickly — pick a DXF/CAD
   file, tune sampling/triangulation, preview the result live as a smooth
   rotating model, before anything is called "done" and handed to the
   customer-facing site.

## Why the operator tool comes first

The owner (Hnodri) wants this proven inside `ACM-Web-Pipeline`
(`pipeline.acm.is`, the internal operator tool) as a new menu entry —
**not** built directly against `ACM-Web-Main` (www.acm.is, the public
site). Once the reconstruction method is validated there against real
exports, the *output GLBs* (not this feature's code) move over to a
separate `ACM-Web-Main` task for the customer-facing showcase.

**Do not start the `ACM-Web-Main` work in this pass.** See "Stop
condition" in Part 2.

## What already exists (do not rebuild)

- `pipeline-converter/code/convert_dxf.py`, `convert_cad.py` — working
  parsers, already used from the CLI. `utils/parsers.py` owns
  `parse_dxf_points_fast`, `parse_cad_points`, `calculate_bounds`,
  `center_points`, `dedupe_points`. `utils/writers.py` owns
  `write_selected_formats`.
- `ACM-Web-Pipeline/src/components/ModelViewer.jsx` — a working GLB viewer
  (`@google/model-viewer`, camera-controls, auto-rotate). Reuse as-is for
  previewing this feature's output; do not write a second viewer.
- `ACM-Web-Pipeline/src/lib/paths.js` — already resolves `CONVERTER_ROOT`,
  `PYTHON_EXE` (the pipeline-converter venv), `INPUT_DIR`, `OUTPUT_DIR`,
  and safe-filename helpers. Use these, don't re-derive paths.
- `ACM-Web-Pipeline/src/lib/navigation.js` — the sidebar's single source of
  truth (`SECTIONS`). A new page is one new entry here, not a parallel nav
  system.
- An existing operator UI pattern for exactly this kind of job
  (`ConverterClient.jsx` + `operations.js` + `python.js` + `JobResults.jsx`)
  — read it and follow its shape for the new page rather than inventing a
  different pattern.

## Real test data available right now

- `ACM-Pipeline/converter/2.5D-pipeline/reference-gallery/cockpit-files/exported/amma-exports/amma-1.{dxf,cad,cbf,rmd}`
  — a full real export, ~4.4M points. Use this as the first end-to-end
  test case before anything else.
- `ACM-Pipeline/converter/2.5D-pipeline/reference-gallery/cockpit-files/*.cockpit`
  and
  `ACM-Pipeline/converter/pipeline-converter/input/3d_files/CockPit3D_Scene_Files/*.cockpit`
  — source scenes. Each is a plain ZIP: `CockpitScene.xml` (readable UTF-8),
  a `.ci` (leave alone, unreadable), a `.jpg` (the real customer photo —
  this is what T2 needs), and a small `.png`. Confirm which `.cockpit`
  pairs with `amma-1`'s export by opening candidates
  (`amma.cockpit`, `amma_&_afi.cockpit`, `amma-4-september.cockpit`,
  `amma-afi-tilraun-2.cockpit` are all in the same folder — check
  `CockpitScene.xml`'s `Template`/entity data against `amma-1`'s point
  bounds rather than guessing from the filename alone).

## Performance target

~4.4M raw points is too many to triangulate and rotate smoothly in a
browser, especially on a phone. Downsample the point cloud **before**
triangulation to roughly **150,000–500,000 points** (fewer input points →
a lighter, still-smooth reconstructed surface and a smaller GLB), using
the existing `--sample-rate` / `--limit` / `--dedupe` /
`--stl-limit` flags — these already exist, this is a matter of choosing
good defaults and exposing them in the new UI, not building new
downsampling logic.

## Workspace rules that apply here

From `Arctic_Crystal_Memories/AGENTS.md` (workspace-wide) and
`converter/own_3d_preview_plan.md`:

- Stop any dev server you start (`npm run dev` for `ACM-Web-Pipeline`) as
  soon as you're done verifying — don't leave it running.
- Each Python pipeline keeps its own venv and `requirements.txt`; never
  merge them. Only `pipeline-converter`'s venv is touched by this task.
- `.cockpit` / `.ci` stays a closed question. Never attempt to decode the
  scrambled transform, in this task or as a "quick check" — that
  investigation already happened and the conclusion stands.
- Do the work on its own branch. Do not commit to `master`/`main`
  directly, and never `git add -A` — stage the exact files you touched.
- Ask the owner before doing anything that deploys, before touching
  `ACM-Web-Main`, and before treating this feature as "done" rather than
  "ready for review."

---

# Part 2 — Agent brief

You are working across two sibling checkouts under
`Arctic_Crystal_Memories/`:

```txt
Arctic_Crystal_Memories/
├── AGENTS.md                                  ← read first, workspace-wide rules
└── ACM-Pipeline/converter/
    ├── README.md                              ← read second, pipeline map
    ├── own_3d_preview_plan.md                 ← read third, the .cockpit background + closed question
    ├── pipeline-converter/                    Python 3.11 · THIS is where T1/T2 live
    │   ├── CLAUDE.md                          ← read before touching this folder
    │   ├── docs/format-notes.md                ← .cad/.dxf column layout, what's confirmed vs not
    │   ├── code/
    │   │   ├── convert_cad.py                  ← extend: add "glb" format
    │   │   ├── convert_dxf.py                  ← extend: add "glb" format
    │   │   └── utils/
    │   │       ├── parsers.py                  ← parse_dxf_points_fast, parse_cad_points, calculate_bounds, center_points, dedupe_points
    │   │       └── writers.py                  ← write_selected_formats — add the glb writer here
    │   ├── input/3d_files/CockPit3D_Scene_Files/*.cockpit
    │   ├── output/                             ← existing convention for converter output
    │   └── requirements.txt                    ← check whether trimesh/pygltflib are already present
    └── ACM-Web-Pipeline/                      Next.js 16 · pipeline.acm.is — THIS is where T3 lives
        ├── src/lib/navigation.js               ← add nav entry ("pipeline-converter" section)
        ├── src/lib/paths.js                    ← CONVERTER_ROOT / PYTHON_EXE / OUTPUT_DIR already resolved, use them
        ├── src/lib/operations.js               ← existing pattern for spawning python jobs — follow it
        ├── src/lib/python.js                   ← subprocess spawn wrapper
        ├── src/components/ConverterClient.jsx  ← existing converter UI — read for pattern, don't diverge without reason
        ├── src/components/JobResults.jsx       ← existing job-result / SSE display pattern
        └── src/components/ModelViewer.jsx      ← GLB viewer, reuse as-is, do not rewrite

ACM-Web-Main/                                  www.acm.is — DO NOT TOUCH in this task (see Stop condition)
```

Read, in this order, before writing any code:

1. `Arctic_Crystal_Memories/AGENTS.md`
2. `ACM-Pipeline/converter/README.md`
3. `ACM-Pipeline/converter/own_3d_preview_plan.md` (both parts)
4. `ACM-Pipeline/converter/pipeline-converter/CLAUDE.md`
5. `ACM-Pipeline/converter/pipeline-converter/docs/format-notes.md`
6. `ACM-Pipeline/converter/pipeline-converter/code/convert_cad.py`,
   `convert_dxf.py`, `code/utils/parsers.py`, `code/utils/writers.py`
7. `ACM-Web-Pipeline/src/lib/navigation.js`, `src/lib/paths.js`,
   `src/lib/operations.js`, `src/components/ConverterClient.jsx`,
   `src/components/ModelViewer.jsx`

## Invariants — do not break these

1. **`.cockpit` / `.ci` stays closed.** Only ever operate on `.dxf`,
   `.cad`, `.cbf`, `.rmd` — files Cockpit3D itself exported in the clear.
   Reading a paired `.cockpit`'s `CockpitScene.xml` or its embedded `.jpg`
   (both plain, unencrypted ZIP members) is fine and expected for T2; the
   `.ci` member inside it is not.
2. **Don't merge or repoint Python venvs.** `pipeline-converter` has its
   own `.venv`/`requirements.txt`. Add `trimesh`/`pygltflib` (whichever you
   end up using — see T1) to `pipeline-converter/requirements.txt` only.
3. **Phase boundary.** This task touches `ACM-Pipeline/converter/**` only.
   `ACM-Web-Main` is not touched, referenced in code, or prepared for in
   this pass beyond the output file convention in T3.
4. **Never commit large/derived binary data.** Raw exports (`.cockpit`,
   `.cad`, `.dxf`, `.cbf`, `.rmd`), intermediate point files (`.xyz`,
   `.ply`), and generated GLBs from this feature do not belong in git —
   confirm (and extend if needed) `.gitignore` coverage for
   `pipeline-converter/input/`, `pipeline-converter/output/`, and
   `2.5D-pipeline/reference-gallery/` before your first commit. If any of
   these are already tracked, flag it rather than force-removing history.
5. **Structure output for an eventual R2 handoff**, without building that
   handoff now. `own_3d_preview_plan.md`'s storage rule (VPS/local disk is
   a workspace, R2 is durable storage) is the established convention for
   this codebase. Write this feature's finished GLBs to one clearly named
   folder (e.g. `pipeline-converter/output/cockpit-reconstruct/<job-name>.glb`)
   so a later upload step is a simple loop over that folder, not a rewrite.
6. **Stop dev servers you start** (workspace `AGENTS.md`) and confirm the
   port is released before finishing.
7. **Branch discipline.** Create and work on a dedicated branch in the
   `ACM-Pipeline` repo (suggested name: `feature/cockpit-reconstruct`).
   Stage files explicitly; never `git add -A`.

## Tasks

Ranked, sequential. Each has an acceptance test — do not mark one done
without running it.

### T1 · Reconstructed-surface GLB export (not a sparse point cloud)

The goal is a **smooth, continuous surface** — the same kind of soft relief
look as the pre-rasterization preview — not a sparse dot cloud rendered as
`POINTS`. `convert_cad.py`/`convert_dxf.py` already triangulate the raw
point cloud into a 2.5D surface via `--formats stl --stl-method delaunay`
(or `convex` for a closed hull) — **that triangulation is the
reconstruction step**, already implemented. The task is only to export
that *same* triangulated mesh as GLB too, alongside STL, not to invent a
new geometry path.

Add `"glb"` to the `--formats` choices in both `convert_cad.py` and
`convert_dxf.py`, and implement the writer in `utils/writers.py` by reusing
whatever mesh object the `stl` writer already builds (check how the
existing Delaunay/convex triangulation is implemented there — it likely
already produces a `trimesh.Trimesh` or an equivalent vertex/face array
before writing STL) and exporting it with `trimesh`'s standard
**mesh** export path — `Trimesh(vertices=..., faces=...).export(file_type="glb")`
— which is the well-trodden, reliable path (unlike point-cloud-only GLB
export, which is inconsistent across trimesh versions and should be
avoided entirely here). Confirm `trimesh` is already a dependency (it is
used elsewhere in this workspace per `own_3d_preview_plan.md`'s T1 smoke
test) before adding it again.

**Acceptance:** running

```powershell
cd pipeline-converter
.\.venv\Scripts\python.exe code\convert_dxf.py --file "..\2.5D-pipeline\reference-gallery\cockpit-files\exported\amma-exports\amma-1.dxf" --formats glb stl --stl-method delaunay --stl-limit 300000 --dedupe --center
```

produces a `.glb` that shows a **smooth, continuous surface** (not visible
individual dots) when opened in `ModelViewer.jsx` (or any quick
`<model-viewer>` HTML sanity check) — recognizably the same shape as the
`.stl` written in the same run.

### T2 · Per-vertex color on the reconstructed mesh, from the paired photo

Add a way to color the T1 mesh from the real customer photo, since raw
`.cad`/`.dxf` carries no confirmed RGB (`format-notes.md`). Suggested
shape: an optional `--texture-from <path-to-photo-or-cockpit>` argument,
applied to the triangulated mesh's vertices (not to the raw point cloud —
color survives the triangulation just fine since vertices are a subset of
the original points).

- If a `.cockpit` path is given, open it as a ZIP (`zipfile`, stdlib —
  no special handling needed, only the `.ci` member is opaque), read
  `CockpitScene.xml` for the `SolidEntity`'s `Texture` attribute, and load
  that JPEG member directly from the archive.
- If a bare image path is given, load it directly.
- Use `CockpitScene.xml`'s `ProjectionSetting Direction` (when a
  `.cockpit` is available) to determine which two of X/Y/Z are the image
  plane. Use the mesh's own bounds (`calculate_bounds`, already
  implemented, or the mesh's vertex bounding box post-triangulation) to
  map each vertex's plane coordinates to a normalized `[0,1]` UV, and
  sample the corresponding photo pixel as that vertex's RGB
  (`trimesh.Trimesh(..., vertex_colors=...)` carries straight through to
  GLB as a `COLOR_0` accessor — no separate UV-mapped texture image is
  required, though one is a reasonable alternative if it renders better).
- **When no photo/`.cockpit` is supplied, leave the mesh uncolored** (plain
  white or light grey) rather than guessing at a mapping. A wrong color is
  worse than no color.

**Acceptance:** a colored export of a portrait-containing test file is
visibly recognizable as that photograph on the smooth reconstructed
surface in `ModelViewer.jsx` (the same test used informally to eyeball
`own_3d_preview_plan.md`'s relief pipeline). An export run without a photo
still succeeds and shows an uncolored surface — confirm it doesn't crash or
silently produce garbage color.

### T3 · "Cockpit Reconstruct" operator page

Add a new nav entry to `SECTIONS` in `src/lib/navigation.js`, inside the
existing `"pipeline-converter"` section (step 3) alongside `"converter"` —
suggested `id: "cockpit-reconstruct"`, slug `"cockpit-reconstruct"` in
`NAV_SLUGS`. Build the page following `ConverterClient.jsx` /
`operations.js` / `python.js` / `JobResults.jsx`'s existing pattern (same
job-spawn and result-streaming approach already used for the rest of the
converter) rather than inventing a new one. The page should let an
operator:

- Pick an existing `.dxf`/`.cad` file under `pipeline-converter/input/` (or
  upload a new one — reuse the existing upload/library pattern from
  `PhotoLibrary.jsx`/`ImageClient.jsx` if there's a shared component for
  this, otherwise follow their shape).
- Optionally pick/upload the paired `.cockpit` (for T2's coloring) — if
  one is found alongside the chosen DXF/CAD by matching filename, offer it
  as a default rather than requiring manual selection every time.
- Adjust `--sample-rate` / `--limit` / `--dedupe` / `--center` via simple
  form fields, matching the existing `OptionFields.jsx` pattern if
  applicable.
- Run T1+T2's conversion and preview the resulting GLB live with
  `ModelViewer.jsx`.
- Re-run with different settings without leaving the page.
- Save the finished GLB under
  `pipeline-converter/output/cockpit-reconstruct/<job-name>.glb`.

**Acceptance:** from a browser at `pipeline.acm.is`, an operator can select
`amma-1.dxf`, optionally pair it with the right `.cockpit` for color,
adjust sampling, run reconstruction, see the result auto-rotating in the
page via `ModelViewer.jsx`, and end up with a saved `.glb` file. Repeat for
at least one of the four target pieces once its DXF/CAD has been exported
from Cockpit3D by the owner (`dad-fish-2`, `group-photo`,
`me-guitar-tenerife`, `volcanic-activity` — these currently have `.cockpit`
only, no export yet; don't block T1–T3 on waiting for those, `amma-1` is
sufficient to build and prove the feature).

### T4 · Stop condition — owner checkpoint

**Do not start any `ACM-Web-Main` work after T3.** Report back:

- What was built (T1–T3), with the exact acceptance-test commands/steps
  run and their results (screenshots or a short recording of
  `ModelViewer.jsx` showing a colored, rotating smooth model help here).
- Any deviation from this brief and why (e.g., trimesh's GLB path didn't
  work and a manual writer was used instead).
- Point-count and file-size numbers for the `amma-1` test export at the
  chosen default sampling, so the owner can judge whether 150k–500k points
  actually looks good enough before more pieces get exported.

Wait for explicit owner sign-off before a follow-up task defines the
`ACM-Web-Main` customer-facing showcase page (separate branch, separate
brief — that page will consume the GLBs this phase produces, most likely
via R2 rather than committed into either repo, per the storage rule
above).

## Gotchas already paid for elsewhere in this workspace

- **Windows heredocs eat backslashes.** Write files with an editor tool,
  not a shell heredoc, when content contains `\` or regex escapes
  (`own_3d_preview_plan.md`).
- **These exports are huge** (100–230 MB, millions of points). Never load
  a full file into memory naively for the T2 color pass — stream/process
  the same way the existing fast parsers already do
  (`parse_dxf_points_fast`, `parse_cad_points`), and test T1/T2 against a
  small `--limit` slice (e.g. 5,000 points) before running a full file.
- **`.cockpit` is a plain ZIP.** Python's `zipfile` opens it directly, no
  special tooling needed — only the `.ci` member inside is unreadable.
- **Verify GLB output by actually looking at it.** A successful `export()`
  call is not proof of a visible, smooth result — confirm in
  `ModelViewer.jsx` that the GLB shows the same recognizable surface as the
  STL written in the same run, not a degenerate or invisible mesh, and not
  a sparse cloud of individual dots (that would mean the mesh export
  accidentally fell back to a points-only path — treat it as a bug, not an
  acceptable result).
- **Multiple `.cockpit` files share ambiguous names** (`amma.cockpit`,
  `amma_&_afi.cockpit`, `amma-4-september.cockpit`,
  `amma-afi-tilraun-2.cockpit`). Confirm which one pairs with `amma-1`'s
  export by checking `CockpitScene.xml` content/bounds, not filename
  guessing.

## Related documents

- `ACM-Pipeline/converter/own_3d_preview_plan.md` — background, the closed
  `.cockpit`/`.ci` question, the wider 3D-preview roadmap.
- `ACM-Pipeline/converter/pipeline-converter/docs/format-notes.md` —
  `.cad`/`.dxf` column layout, current parser assumptions.
- `ACM-Pipeline/converter/README.md` — the four pipelines and how they
  chain together.
- This file — update it in place with a dated note under a new heading if
  T1/T2's approach changes materially, the same way `own_3d_preview_plan.md`
  is maintained.
