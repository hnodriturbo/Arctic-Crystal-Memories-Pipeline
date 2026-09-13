<!--
File: .Markdown/runs/2026-09-04-amma2-v30-rewind-comparison/ARTIFACTS.md
Purpose:
 - Index the local v3.0 rewind output, metrics, QA and tracked comparison gallery.
-->

# Artifact index

## Tracked comparison evidence

- [V3.0–v3.3 and AC3D gallery](artifacts/gallery/README.md)
- HTML gallery: `artifacts/gallery/index.html`
- Contact sheet: `artifacts/gallery/00-contact-sheet.jpg`

## Local generated v3.0 artifacts

Allar eftirfarandi slóðir eru undir
`converter/2.5D-pipeline/output/research/2026-09-04-amma2-v30-rewind/` og haldast
staðbundnar samkvæmt `.gitignore`:

- Final crystal-tone GLB: `relief-crystal.glb`
- Frozen recipe manifest: `approved-v3-manifest.json`
- Source-camera metrics: `04-source-camera/source_camera_fusion_stats.json`
- MoGe depth and raw float data: `05-moge-scene-depth/`
- Scene-fusion metrics: `06-scene-fusion/scene_fusion_stats.json`
- Final pre-tone mesh: `07-depth-skirt-v3/both_people_scene_with_depth_skirts.glb`
- Stretch/filler metrics: `07-depth-skirt-v3/silhouette_depth_skirt_stats.json`
- Neutral four-view QA: `08-neutral-qa/`

## Reproduction

```powershell
.\code\research\run_approved_v3_self_service.ps1 `
  -Source .\output\local-workbench\a3c0aadb7e3c\source-prepared.png `
  -OutputDir .\output\research\2026-09-04-amma2-v30-rewind
```

Neutral QA was rendered with `code/research/render_single_front_depth_qa.py`
in Blender 5.1.2. The gallery was generated with
`code/research/build_run_gallery.py`.
