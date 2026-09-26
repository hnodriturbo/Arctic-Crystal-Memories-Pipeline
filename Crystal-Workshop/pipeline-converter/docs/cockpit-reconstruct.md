<!--
Purpose: Operator workflow, reconstruction limitations, and local verification record.
-->

# Cockpit Reconstruct

## Current showroom preparation — 2026-09-13

The owner requires every DXF point. The reconstruction CLI/UI now defaults to
sample-rate 1. For paired showroom GLB and full RGB point PLY, use
`code/prepare_showroom.py`; it always reads every point and refuses overwritten
trials or ambiguous/rotated Cockpit scenes. The complete command, source-pairing
rules, output units, R2 handoff and agent workflow are documented in
`../../../../ACM-Web-Main/docs/Guides/CRYSTAL_SHOWROOM.md` (relative to this guide).
Older sampled runs below are historical evidence, not recommended defaults.

## Lower-body refinement — owner review

### Text-free source, 2026-09-13

The owner identified foreground scene text as the contaminating geometry and
provided `reference-gallery/cockpit-files/exported/amma-og-afi-new/amma-og-afi-without-text.dxf`.
New result: `20260913-110133-7513b74b.glb`, with the same smooth-grid settings
and provisional `amma-afi-tilraun-2.cockpit` texture, **lower repair disabled**.
636,351 sampled points produce 215,362 vertices / 427,872 triangles and a
16,350,936-byte GLB. A working DXF copy is available under
`input/cockpit-reconstruct/amma-og-afi-without-text.dxf`.
Visual review remains with the owner; no browser was opened for this run.

The owner confirmed the head and upper geometry are correct and requested changes
only to the lower body. `--repair-lower` therefore modifies only the bottom 42%
of the existing XY grid, with a feathered boundary; topology and upper positions
remain unchanged. The optional `--lower-repair-strength` (1–3) increases the local
morphological opening footprint and reduces the retained ridge allowance.

The initial accepted-direction trial is `20260913-105041-8bed9658.glb` (strength 1).
An actual GLB comparison with `20260913-103634-a93174c4.glb` found identical faces,
zero upper position change, and 27,027 adjusted lower vertices. The owner reported
improvement but remaining protrusions and requested the next trial without browser
automation. Strength 2.5 is the next experiment. Eight reconstruction tests pass,
including exact upper-region preservation and suppression of wider lower ridges.

This is a constrained geometric approximation, not a proven recovery of each
point's source entity. The exact contribution of scene text versus layered data
to each ridge has not been isolated. The user reviews results in their own browser;
leave the explicitly requested development server running and do not open Playwright.

Status: implementation in review, visual fidelity still being evaluated with the owner.
No public website or deployment work is part of this feature.

## Inputs

Use a Cockpit3D **POINT DXF** export, or the corresponding text CAD export.
Keep the exact source `.cockpit` beside it, or choose its original photograph.
The parser reads only plain scene XML and the named JPEG/PNG texture, never CI geometry.
CBF and RMD are not currently supported by this reconstruction module.

Place working copies in `pipeline-converter/input/cockpit-reconstruct/`, then
open **Cockpit Reconstruct** in the existing website sidebar and refresh its library.
Direct uploads stream to disk with a 1 GB ceiling; external proxies may impose smaller limits.

## Methods

- **Continuous relief** is the new default: sample every fourth source point,
  collapse projected depth layers to an 85th-percentile front envelope, estimate
  contour breaks within five grid cells, fill enclosed dark regions with harmonic
  interpolation, median-filter and smooth depth (sigma 1.5), then
  triangulate only locally supported grid cells. The longer grid edge is 512 samples.
- **Raw triangles** retains the original XY Delaunay approach for comparison.
  Layered points can produce roughness and triangles across empty areas.
- **Convex hull** creates an outer envelope and cannot preserve concave facial detail.

All methods export the same geometry to STL (millimetres) and GLB (metres).
The operator module uses the existing converter virtual environment.

Full-photo texture is the default color mode. Vertex colors remain available for
comparison. No photo means a light grey material. Unknown numeric Cockpit projection
enums require an explicit image plane; the implementation does not guess their meaning.
XY normally corresponds to the relief image plane. Horizontal/vertical mirroring is adjustable.
Photo projection currently uses mesh bounds; text entities, changed cropping and scene
transforms may require more sophisticated alignment. Matching filenames are suggestions only.

This estimates a relief; it does **not** recover the exact pre-rasterization CI mesh.
Surface smoothing cannot recover absent features or unseen sides. Review uncolored
geometry separately from texture, so a convincing photograph cannot hide poor shape.

## Files and verification

Each run writes a unique GLB, STL and JSON settings report under
`output/cockpit-reconstruct/`. Files stay local and are ignored by Git. R2 handoff is deferred.

Tests:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_cockpit_reconstruct.py -v
```

Six reconstruction tests cover GLB triangle mode and STL equivalence, metre conversion, photo
corners and scene reading without CI data, stream sampling, removal of layered
depth noise, and preservation of gaps between separate subjects.

On 2026-09-13:

- ESLint passed for the initial implementation. Next production build passed with
  `node node_modules/next/dist/bin/next build --webpack`; Turbopack worker spawning
  returned Windows access-denied even outside the sandbox.
- The operator page and ModelViewer were inspected at 1600×1100 and 390×844.
- `amma-1.dxf` was confirmed by the owner to be a Cockpit export from the reference
  gallery. Initial raw Delaunay output was visually inadequate and is not acceptance
  evidence for reconstruction quality. The original assumed photo pairing was not proven.
- The owner selected `DXF-Amma-og-Afi-Tester-Output.dxf` for the next comparison.
  Final continuous relief: 678,607 sampled points → 211,711 vertices / 419,816 triangles,
  10,966,976-byte uncolored GLB. Raw comparison at sample rate 16: 169,651 vertices /
  288,227 triangles, 8,210,200-byte GLB. These are technical metrics, not quality approval.
- An actual browser run selected `input/cockpit-reconstruct/DXF-Amma-og-Afi-Tester-Output.dxf`,
  used sample rate 4, grid 512, smoothing 1.5 and gap 5, and returned job
  `20260913-103508-48c057d0` through the streaming API with saved GLB/STL/report.
  ModelViewer reported loaded; desktop document width did not exceed viewport width.
- Provisional textured result `20260913-103634-a93174c4.glb` is 16,137,436 bytes.
  It uses `amma-afi-tilraun-2.cockpit` with explicit XY projection: its 2618×2800
  photo aspect ratio closely matches the 107.84×115.44 mm footprint. This is a
  reasoned candidate, **not confirmed scene pairing**. Different candidate scenes
  contain different crops, so they are not interchangeable.
- Visual review showed much more continuous clothing regions and recognizable
  portrait texture, but text entities still protrude around the hands/lower body.
  The next useful input is a portrait-only export from the exact scene, without
  lettering or other overlays. No claim of exact CI geometry recovery is made.
- All 10 converter regression tests passed, including the six reconstruction tests;
  final changed-file ESLint passed. Browser preview was stopped and port 3117 released.
- Final `next build --webpack` passed after all code changes. Both `convert_dxf.py`
  and `convert_cad.py` also completed `--formats glb stl --limit 5000 --dedupe --center`
  on the selected exports. Their partial GLBs were moved to `output/diagnostics/cli-smoke/`.

Screenshots are local under `CCM-Web-Pipeline/output/playwright/`:
`amma-afi-raw.png`, `amma-afi-continuous.png`, `amma-afi-textured.png`, and
`reconstruct-mobile.png`. Initial visually inadequate amma trials are retained
under `output/diagnostics/initial-amma-tests/` instead of the saved-surface library.

Implementation references: [SciPy Gaussian filtering](https://docs.scipy.org/doc/scipy/reference/generated/scipy.ndimage.gaussian_filter.html)
and [distance transform](https://docs.scipy.org/doc/scipy/reference/generated/scipy.ndimage.distance_transform_edt.html).

The corresponding CAD export is accepted by the same module. The exact paired
scene and visual quality remain owner checkpoints. Do not start ACM-Web-Main work.

### Confirmed source scene (2026-09-13)

The owner confirmed that the text-free Amma-og-Afi DXF belongs to `amma_&_afi.cockpit`.
Earlier trials incorrectly used `amma-afi-tilraun-2.cockpit`: its texture is 2618 x 2800,
whereas the confirmed scene texture is 2800 x 2002. Do not infer scene pairing from similarity.

`20260913-111424-4c0977c3.glb` uses the confirmed scene with the original 103634 settings,
no lower repair, and only the text-free DXF. Reload verification confirms vertices and
faces are identical to the prior text-free trial; only the texture changed. Visual
approval is pending the owner's browser review. No browser automation was opened.
The UI now makes scene selection explicit, uses XY by default, and collapses advanced
settings and logs. No intermediate DXF conversion is needed for this texture correction.
