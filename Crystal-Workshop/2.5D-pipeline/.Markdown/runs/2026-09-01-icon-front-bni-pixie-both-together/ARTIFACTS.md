<!--
File: .Markdown/runs/2026-09-01-icon-front-bni-pixie-both-together/ARTIFACTS.md
Purpose:
 - Map local raw tensors, A/B surfaces, QA files, and failure evidence for this run.
-->

# ICON front d-BiNI artifacts

Ignored local artifact root:

```text
output/research/icon-front-bni/both-together-ai-enhanced-pixie/
```

## Canonical inputs and outputs

- `icon-export-v2/icon-filter/front-data/*_icon_front_raw.npz`: lossless float32 ICON tensors.
- `icon-export-v2/icon-filter/front-data/*_icon_BNI.npy`: ECON-compatible normal/depth/mask payload.
- `front-surface-adaptive-fillet/*_icon_front_bni.obj`: canonical neutral geometry.
- `front-surface-adaptive-fillet/*_icon_front_bni.glb`: individual vertex-colored interchange files.
- `front-surface-adaptive-fillet/icon_front_bni_stats.json`: exact config and mesh metrics.
- `qa-adaptive-fillet/*_front.png`: neutral source-facing geometry QA.
- `qa-adaptive-fillet/*_30deg.png`: neutral angled geometry QA.
- `qa-adaptive-fillet/both_icon_front_bni_diagnostic.*`: side-by-side QA only; not source-camera fusion.

## Preserved negative/failure evidence

- `icon-export/`: rejected 1×512 depth export caused by a renderer shape assumption.
- `front-surface/`: first integration stopped after geometry while source texture tensor remained on CPU.
- `front-surface-v2/` + `qa/`: cut intersections and steep-face removal; visible cracks.
- `front-surface-no-cut/` + `qa-no-cut/`: no intersection cutting; cracks remained.
- `front-surface-continuous/` + `qa-continuous/`: keeps all steep faces; continuous but unfilleted.

All variants remain separate. None overwrite the frozen ECON or official ICON baselines.

## Exact code snapshot

- `code-snapshot/pipeline/`: local run, integration og QA scripts.
- `code-snapshot/upstream/`: exact modified ICON/ECON source files used by this run.
- `code-snapshot/patches/`: human-readable upstream change summaries.

Allar snapshot-kóðaskrár eru merktar read-only. Sjá
[code-snapshot/README.md](code-snapshot/README.md).
