<!--
File: .Markdown/runs/2026-09-04-ac3d-cockpit-amma-reference/ARTIFACTS.md
Purpose:
 - Index reproducible geometry, reports, QA renders, and user-visible galleries
   for the September 4 AC3D reference comparison.
-->

# Artifact index

## Samanburðargallerí

- [Staðfest AC3D/Cockpit reference](artifacts/gallery/ac3d-reference/README.md)
- [Höfnuð v3.1 endurkeyrsla](artifacts/gallery/v31-rerun/README.md)

HTML útgáfur eru í sömu möppum sem `index.html`.

## Geometry og report

- AC3D/Cockpit GLB:
  `output/research/2026-09-04-ac3d-cockpit-amma-reference/ci-glb/amma-ci-scene-mm.glb`
- AC3D/Cockpit report:
  `output/research/2026-09-04-ac3d-cockpit-amma-reference/ci-glb/report.json`
- V3.1 GLB:
  `output/research/2026-09-04-ac3d-cockpit-amma-reference/our-v31-rerun/04-bounded-silhouette-backfill/portrait-with-silhouette-backfill.glb`
- V3.1 manifest:
  `output/research/2026-09-04-ac3d-cockpit-amma-reference/our-v31-rerun/portrait-refinement-manifest.json`

## Reproduction

- CI decoder: `code/research/extract_cockpit_ci_mesh.ps1`
- GLB builder: `code/research/build_glb_from_cockpit.py`
- Frozen v3.1 runner: `code/research/run_portrait_hrn_moge_refinement.ps1`
- Neutral QA renderer: `code/research/render_source_portrait_qa.py`

