<!--
File: .Markdown/runs/2026-09-03-portrait-v33-direct-hrn-original-moge/README.md
Purpose:
 - Record the amma-2 portrait v3.3 model provenance, controlled experiments, and candidate result.
-->

# Portrait v3.3 — direct HRN + original-source MoGe

Status: **CANDIDATE — not yet accepted**

## What the two grayscale images actually are

The almost-white silhouette is **not a depth map** and no depth model made it.
It is a BiRefNet Portrait semantic foreground mask:

- black = background;
- white = person;
- it contains no internal distance or relief information.

The earlier grayscale person with visible internal depth was
`man_icon_front_depth.png`. It came from official ICON front normals integrated
with ECON's d-BiNI solver. It is real-valued surface depth, not a segmentation
mask and not MoGe output.

## Root cause of the misleading white MoGe preview

The earlier portrait route fed a transparent cut-out to code that converted it
to RGB. Transparent pixels became black and affected MoGe's scene inference.
The displayed depth was then globally percentile-normalized across foreground
and background. That combination compressed the visible person range and made
the preview look almost flat/white.

This run separates the inputs by role:

1. the original opaque 2K photograph is the only MoGe input;
2. BiRefNet alpha is used only as a silhouette/ownership mask;
3. MoGe percentiles are measured only inside the largest subject component;
4. native HRN topology owns the close-portrait face and head;
5. grayscale source luma owns appearance.

MoGe-2 ViT-L produced a subject p99-p1 metric range of **0.2563 m**, above the
new 0.08 m quality threshold. The depth is therefore demonstrably non-flat.

## Controlled geometry experiments

The direct HRN front patch kept facial form better than the rejected v3.2
raster-heightfield, but remained open in profile. Explicit multi-ring strips
closed portions of the edge but created horizontal side spikes. Those runs are
preserved as rejected evidence.

The first clean candidate instead used:

- complete native HRN side/back topology;
- a shallow 0.30 working-unit head span;
- a horizontal lower-neck crop that does not cut away the rear hemisphere;
- MoGe body/clothing at a 0.26 working-unit span;
- a continuous 14 px support glide near the ownership boundary;
- no experimental MoGe hair-fringe geometry.

The resulting GLB contains separate named HRN and MoGe layers. User review of
its profile found the cranium too shallow. A controlled second candidate changed
only the native HRN head span from **0.30 to 0.42**. The new profile has visibly
more credible cranial volume while the front-facing identity remains stable.
The 0.42 version improved the cranium but remained too shallow in MeshLab.
A third controlled experiment raises the native HRN head span to **0.60**, keeps
the accepted lower garment at **0.26**, adds only a **+0.12 feathered shoulder
boost**, and folds source-frame-cut edges **0.24** rearward over 13 rings. User
review rejected that frame-cut fold because it made the naturally thin garment
look like a block. Frame-cut backfill is now disabled by default and preserved
only as opt-in rejected evidence.

## Remaining limitation

The lower HRN-neck boundary and MoGe garment still meet as two overlapping
surfaces. The narrow jagged seam is visible in neutral QA. This candidate must
not replace an accepted preset until a dedicated boundary stitch/remesh pass
connects those rings and passes all three camera views.

The source hair is also absent from the native closed HRN scalp, and the glasses
remain largely baked into the face appearance. Both require independent
source-aligned geometry layers before the portrait can be accepted.

The removed hair-fringe experiment is also preserved. A future hair solution
must use a smooth bounded silhouette shell or a hair-specific model; raw masked
heightfield edges are not accepted because they form side-view teeth.

## Result

- Rejected frame-cut GLB: `output/research/portrait-v33-direct-hrn-original-moge/20-depth060-shoulders-frame-backfill/portrait-v33-hrn-direct-moge-layered.glb`
- Rejected frame-cut statistics: `output/research/portrait-v33-direct-hrn-original-moge/20-depth060-shoulders-frame-backfill/portrait-v33-composition-stats.json`
- Latest thin-garment candidate GLB: `output/research/portrait-v33-direct-hrn-original-moge/21-depth060-shoulders-thin-garment/portrait-v33-hrn-direct-moge-layered.glb`
- Latest thin-garment candidate OBJ: `output/research/portrait-v33-direct-hrn-original-moge/21-depth060-shoulders-thin-garment/portrait-v33-hrn-direct-moge-layered.obj`
- Latest statistics: `output/research/portrait-v33-direct-hrn-original-moge/21-depth060-shoulders-thin-garment/portrait-v33-composition-stats.json`
- Visual gallery: [artifacts/gallery/README.md](artifacts/gallery/README.md)
- Controlled 0.30/0.42 comparison: [artifacts/depth-042-gallery/README.md](artifacts/depth-042-gallery/README.md)
- Rejected 0.60 + frame-cut backfill gallery: [artifacts/depth-060-frame-backfill-gallery/README.md](artifacts/depth-060-frame-backfill-gallery/README.md)
- Current 0.60 thin-garment gallery: [artifacts/depth-060-thin-garment-gallery/README.md](artifacts/depth-060-thin-garment-gallery/README.md)

No PARE, ICON, or ECON body prior is used in this close-portrait candidate.
Those models remain available for full-body and multi-person routes; they are
not globally excluded based on one image class.

SMPL-X is also scheduled as a bounded hidden neck/body support experiment for
this close-portrait class. It will not replace HRN identity geometry. See the
[SMPL-X evaluation plan](../../methodology/SMPL-X-EVALUATION-PLAN.md).
