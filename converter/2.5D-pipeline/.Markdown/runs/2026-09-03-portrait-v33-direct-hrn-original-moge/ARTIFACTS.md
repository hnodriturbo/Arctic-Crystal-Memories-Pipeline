<!--
File: .Markdown/runs/2026-09-03-portrait-v33-direct-hrn-original-moge/ARTIFACTS.md
Purpose:
 - Map portrait v3.3 source evidence, intermediate artifacts, and QA outputs.
-->

# Portrait v3.3 artifacts

## Source and model evidence

- Prepared BiRefNet portrait: `output/local-workbench/a3c0aadb7e3c/source-prepared.png`
- Original opaque 2K image used by MoGe: `output/local-workbench/preprocess/898dfc7155e0/02-upscaled.png`
- MoGe-2 ViT-L raw metric depth: `output/research/portrait-v33-direct-hrn-original-moge/01-moge-original/depth_raw.npy`
- Official HRN native OBJ: `output/local-workbench/a3c0aadb7e3c/12-hrn-head/source-prepared/hrn-head.obj`
- HRN/source registration assets: `output/local-workbench/a3c0aadb7e3c/13-hrn-fusion-assets/`

## First clean candidate — head span 0.30

- Layered GLB: `output/research/portrait-v33-direct-hrn-original-moge/16-clean-closed-head-moge-body/portrait-v33-hrn-direct-moge-layered.glb`
- Layered OBJ: `output/research/portrait-v33-direct-hrn-original-moge/16-clean-closed-head-moge-body/portrait-v33-hrn-direct-moge-layered.obj`
- Model/quality statistics: `output/research/portrait-v33-direct-hrn-original-moge/16-clean-closed-head-moge-body/portrait-v33-composition-stats.json`
- Semantic-mask label: `01-birefnet-semantic-mask-not-depth.png`
- Subject-only MoGe depth: `02-moge-subject-depth-near-white.png`
- Inverted subject-only MoGe depth: `02b-moge-subject-depth-far-white.png`
- Neutral QA: `output/research/portrait-v33-direct-hrn-original-moge/16-clean-closed-head-moge-body/qa/`

## Preferred candidate — head span 0.42

- Layered GLB: `output/research/portrait-v33-direct-hrn-original-moge/18-clean-closed-head-depth042/portrait-v33-hrn-direct-moge-layered.glb`
- Layered OBJ: `output/research/portrait-v33-direct-hrn-original-moge/18-clean-closed-head-depth042/portrait-v33-hrn-direct-moge-layered.obj`
- Model/quality statistics: `output/research/portrait-v33-direct-hrn-original-moge/18-clean-closed-head-depth042/portrait-v33-composition-stats.json`
- Neutral QA: `output/research/portrait-v33-direct-hrn-original-moge/18-clean-closed-head-depth042/qa/`
- Reviewed comparison gallery: [artifacts/depth-042-gallery](artifacts/depth-042-gallery/README.md)

## Rejected — head 0.60 + shoulder/frame-cut backfill

- Layered GLB: `output/research/portrait-v33-direct-hrn-original-moge/20-depth060-shoulders-frame-backfill/portrait-v33-hrn-direct-moge-layered.glb`
- Layered OBJ: `output/research/portrait-v33-direct-hrn-original-moge/20-depth060-shoulders-frame-backfill/portrait-v33-hrn-direct-moge-layered.obj`
- Model/quality statistics: `output/research/portrait-v33-direct-hrn-original-moge/20-depth060-shoulders-frame-backfill/portrait-v33-composition-stats.json`
- Neutral front/30°/left-profile/right-profile QA: `output/research/portrait-v33-direct-hrn-original-moge/20-depth060-shoulders-frame-backfill/qa/`
- Reviewed gallery: [artifacts/depth-060-frame-backfill-gallery](artifacts/depth-060-frame-backfill-gallery/README.md)

This experiment selects 663 source-frame boundary edges: left 60, right 301,
top 0, and bottom 307. The accepted lower garment front is unchanged; the new
geometry is a separate 15,912-triangle rear fold. User review rejected the fold
because its 0.24 depth made the naturally thin garment look like a block.

## Current candidate — head 0.60 + shoulders + thin garment

- Layered GLB: `output/research/portrait-v33-direct-hrn-original-moge/21-depth060-shoulders-thin-garment/portrait-v33-hrn-direct-moge-layered.glb`
- Layered OBJ: `output/research/portrait-v33-direct-hrn-original-moge/21-depth060-shoulders-thin-garment/portrait-v33-hrn-direct-moge-layered.obj`
- Model/quality statistics: `output/research/portrait-v33-direct-hrn-original-moge/21-depth060-shoulders-thin-garment/portrait-v33-composition-stats.json`
- Neutral four-view QA: `output/research/portrait-v33-direct-hrn-original-moge/21-depth060-shoulders-thin-garment/qa/`
- Reviewed gallery: [artifacts/depth-060-thin-garment-gallery](artifacts/depth-060-thin-garment-gallery/README.md)

This is the same 0.60 head and +0.12 shoulder experiment with frame-cut
backfill disabled. The lower MoGe garment remains at 0.26 and visually thin.

## Preserved rejected/informative comparisons

- `03-layered-portrait`: deep open-front composition; rejected.
- `05-layered-shallow-glide`: explicit all-edge glide; rejected for spikes.
- `06-layered-shallow-heightfield-glide`: smoother support but open HRN side; informative.
- `07-layered-shallow-outer-glide`: explicit outer strip; rejected for side stripes.
- `11-complete-head-moge-body`: full generic HRN bust overlapped garment; rejected.
- `15-closed-head-hair-neck-overlap`: hair fringe preserved but produces side teeth; rejected.

The reviewed contact sheet and full-size copies are under
[artifacts/gallery](artifacts/gallery/README.md).
