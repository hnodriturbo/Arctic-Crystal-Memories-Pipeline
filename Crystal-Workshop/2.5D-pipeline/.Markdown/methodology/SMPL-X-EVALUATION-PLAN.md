<!--
File: .Markdown/methodology/SMPL-X-EVALUATION-PLAN.md
Purpose:
 - Define how the available SMPL-X packages and SMPLify-X code will be evaluated in the local 2.5D research pipeline.
-->

# SMPL-X evaluation plan

Status: **ACTIVE LOCAL RESEARCH PLAN**

## What is already present and proven

The local ICON data audit reports these assets as `READY`:

- SMPL-X male, female, and neutral body models;
- PIXIE and its SMPL-X support assets;
- PARE and PyMAF alternative human-pose-and-shape estimators;
- ICON checkpoints and SMPL/SMPL-X conversion data.

PIXIE + SMPL-X has already been used successfully as the anatomical, pose, and
camera prior in the accepted ECON front-surface baseline. SMPL-X is therefore
not a future-only idea; it is already one proven layer in the research stack.

The downloaded local model archive is
`Models/research/ECON/model-assets/downloads/models_smplx_v1_1.zip`
(870,108,517 bytes) and is already unpacked in the ECON staging tree. The
legacy SMPLify research-code archive `mpips_smplify_public_v2.zip` is also
present, but it is not the separate SMPLify-X repository requested for the
2026-09-04 learning session.
The locked-head, Blender add-on/shape variants, and Unity package were not found
as separate local archives in the current inventory and remain explicit
download/evaluation items.

## Package-by-package test matrix

| Package or code | Intended ACM role | First controlled test | Priority |
| --- | --- | --- | --- |
| SMPL-X v1.1 model files | Common body, neck, head, hand, pose, and camera prior | Reproduce the current PIXIE/ECON baseline and record exact topology/version | High — archive present and model already in use |
| SMPL-X locked-head archive | Stable head/neck attachment and closed rear support | Compare it with the current native HRN closed head at the neck seam | High |
| Blender-ready SMPL-X v1.1 | Inspect topology, units, rig, pose blendshapes, and export behavior directly in Blender | Import, neutral-pose render, GLB round trip, and millimetre-scale validation | High |
| Blender add-on, 10 shapes | Fast low-dimensional body fitting baseline | Fit the same portrait/full-body evidence and measure silhouette/neck error | Medium |
| Blender add-on, 300 shapes | Higher-capacity shape fitting | Run only after the 10-shape baseline; compare fit gain, stability, time, and overfitting | Medium |
| SMPLify-X code | Explicit optimization of body, hands, and face from 2D keypoints | Isolated research environment using a full-body test image with reliable OpenPose keypoints | High |
| SMPL-X Unity package | Interchange/runtime compatibility, not depth generation | Import an exported fitted body and verify axes, rig, scale, and materials | Low for current 2.5D quality work |

## Composition rule

The variants are evaluated separately before any fusion. They are not all
stacked into a single mesh merely because they are available.

For a close portrait such as `amma-2`, the planned ownership is:

```text
HRN native geometry      -> visible identity, face, ears, and cranium
SMPL-X / locked head     -> optional hidden support and neck/body continuity
MoGe-2                   -> visible clothing and source-relative body depth
BiRefNet                 -> semantic silhouette only
source grayscale         -> appearance
```

SMPL-X may replace or support a region only when front, 30-degree, and profile
QA show an improvement over the current candidate. It must not overwrite the
accepted HRN facial identity merely to obtain a cleaner generic head.

## Immediate experiment order

1. Keep portrait v3.3 head-depth `0.42` as the comparison candidate.
2. Fit or register the available SMPL-X v1.1 prior to the portrait evidence.
3. Use SMPL-X only below a bounded jaw/neck ownership ring.
4. Stitch HRN to that ring, then blend SMPL-X into the MoGe garment surface.
5. Compare against the no-SMPL-X candidate in front, 30-degree, and profile views.
6. Repeat on a genuine full-body image before changing router defaults.
7. Evaluate locked-head and 10-shape Blender variants before the 300-shape variant.
8. Preserve every accepted, candidate, and rejected run in its own artifact gallery.

## Licensing boundary

The official SMPL-X Model/SMPLify-X license permits specified non-commercial
research, education, and artistic use, but not incorporation into a commercial
product or service without separate permission. The separately defined
**SMPL-X Body** subset is offered under CC BY 4.0 and excludes the model's shape
blendshapes/tools. Research assets and outputs must therefore remain isolated
from production until the exact package and intended use have been reviewed.

Official references:

- <https://smpl-x.is.tue.mpg.de/download.php>
- <https://smpl-x.is.tue.mpg.de/modellicense.html>
- <https://smpl-x.is.tue.mpg.de/bodylicense.html>
- <https://github.com/vchoutas/smplify-x>
