<!--
File: docs/portrait-2.5d-pipeline-research-plan.md
Purpose:
 - Define the research and implementation path for a production-quality,
   print-ready portrait 2.5D pipeline between Model A and Model B.
 - Record model, geometry, licensing and validation decisions before purchase.
-->

# Production portrait 2.5D pipeline — research and build plan

**Status:** architecture and benchmark plan, 2026-08-29.

## Product boundary

The requested system is not a generic image-to-3D generator. It must preserve
the visible identity of one or more real people and produce a printable or
laser-sampleable front relief:

```txt
Model A prepared image + Cockpit3D blank metadata
    ↓
portrait 2.5D pipeline / AutoConvertTo3D equivalent
    ↓
one canonical relief geometry
    ├── GLB → Model B customer preview
    └── OBJ → point-cloud/DXF conversion → engraving
```

GLB and OBJ must continue to come from the same canonical surface.

"Perfect" means faithful visible frontal anatomy and a clean manufactured
relief. A single photograph cannot reveal the true back of a head or every
occluded feature, so the production target is not hidden-view ground truth.

## What the current pipeline already gets right

- 16-bit `bright = near` depth contract.
- Subject-only percentile normalization.
- Browser GLB and engraving OBJ from the same geometry.
- Millimetre axes and actual Cockpit3D `SIZE`, `BORDER` and `BEVEL` metadata.
- Real 101,248-point DXF output after the `ENTITIES` parser fix.
- Native Depth Anything resolution is retained because the measured 1024 px
  override costs 2.6× time without adding detail.
- BiRefNet portrait alpha is already available upstream.

## Root causes visible in the supplied face examples

1. **Global monocular depth is a low-frequency scaffold.** Upsampling a roughly
   518 px model result onto a 512-vertex mesh cannot create eye, lip, nostril or
   cheek geometry that the depth model did not predict.
2. **Depth alone is the wrong detail carrier.** Facial high-frequency relief is
   more reliably represented by a surface-normal field and a fitted anatomical
   face model than by one scene-depth plane.
3. **The current edge feather is cut short.** `depth_map.py` fades depth with
   alpha, but `depth_to_mesh.py` later drops every cell unless all four alpha
   samples exceed `0.5`. The surface is therefore cut before the taper reaches
   its back plane, leaving the vertical wall seen from oblique angles.
4. **One global normalization wastes face range.** Clothing, multiple people
   and scene separation can consume most of the 0..1 range and compress one
   person's nose/eyes into a narrow band.
5. **Photo restoration is not geometry.** GFPGAN can help an operator inspect a
   damaged photograph, but its invented pixels must not silently become a
   person's anatomical ground truth.

## Recommended architecture

### Stage 0 — deterministic input and quality gate

- Preserve the original photo and consent/job metadata.
- Run portrait matting and retain soft alpha, not only a binary cut-out.
- Detect every face, pose, occlusion, blur and pixels-across-face.
- Route non-human/object inputs around the face branch.
- Reject or request another photo when the visible evidence is insufficient.

### Stage 1 — global geometry ensemble

Benchmark three adapters behind the existing 16-bit depth contract:

| Candidate | Role | Commercial position to verify |
|---|---|---|
| Apple Depth Pro | sharp metric-depth and boundary baseline | Apple source/weight license is permissive, subject to its terms |
| MoGe-2 `vitl-normal` | primary depth + normal candidate | repository and HF model card say MIT; upstream weight-license ambiguity should be closed in writing before release |
| Marigold v1.1 depth + normals | slow premium/detail challenger | Apache code; model uses the published Marigold model license |
| Metric3D v2 | additional metric depth + normals baseline | BSD code; confirm checkpoint rights for commercial deployment |

Do not average normalized maps blindly. Align candidates by robust affine
scale/shift over the subject, preserve discontinuities, then select or fuse by
face-region confidence and edge quality.

### Stage 2 — human and face geometry

Use a fitted face surface for anatomy and the global model for hair, ears,
neck, clothing and person-to-person ordering.

| Candidate | Planned use | License decision |
|---|---|---|
| 3DDFA_V2 | fast MIT baseline; aligned dense face and depth render | suitable first production prototype, while checking bundled model/data notices |
| HRN | detailed face/head quality challenger | Apache repository; audit all dependent weights/assets before product use |
| DECA / EMOCA | expression and detail benchmark | public release is non-commercial; requires commercial rights |
| MICA | metric identity-shape benchmark | non-commercial public release; commercial licensing is explicitly offered by Max Planck |
| Sapiens2 pointmap/normals | research-only comparison | current license prohibits biometric processing; do not place in production without written permission |

Initial commercial path: 3DDFA_V2 first. If the controlled benchmark shows that
MICA/DECA materially improves printed likeness, request a commercial licence
before integrating their code, weights or output into the product.

For each detected face:

1. render the fitted face to aligned depth and normal maps;
2. solve a robust scale, shift and slight pose correction against the global
   map on cheek, temple and jaw anchor regions;
3. use a semantic skin/face mask that excludes hair and most ears;
4. blend across a distance-based soft band rather than an ellipse; and
5. retain separate confidence maps so low-confidence or occluded areas fall
   back to global geometry.

### Stage 3 — depth/normal fusion

The central upgrade is to combine low-frequency depth with high-frequency
surface normals. Bilateral Normal Integration already supports a coarse depth
prior:

```txt
global + face depth  ──► low-frequency prior
predicted normals    ──► high-frequency gradients
                               ↓
                 discontinuity-aware integration
                               ↓
                     refined fused depth
```

Start with the official BiNI implementation and its `depth_map`, `depth_mask`
and `lambda1` inputs. Compare against the newer generic-camera normal
integration implementation only after the orthographic relief path is stable.

### Stage 4 — inward-floating silhouette

Replace alpha multiplication plus a `0.5` hard mesh cut with a signed-distance
roll-off. For an inside distance `d`, taper width `w`, fused surface `z` and
back plane `z_back`:

```txt
t = smoothstep(0, w, d)
z_final = z_back + t × (z - z_back)
```

Required geometry changes:

- build the mesh over the complete taper domain, not only `alpha >= 0.5`;
- use a very low outer alpha threshold only to stop geometry beyond the matte;
- allow separate taper widths for hair and solid body edges;
- cap edge slope so dots do not form a bright seam;
- avoid adding a vertical skirt to the engraving OBJ;
- optionally add a closed backing only to a separate 3D-print export.

This stage fixes the photographed "cardboard cut-out" wall independently of
which depth model wins.

### Stage 5 — physical relief mapping

- Fit to the selected blank's per-axis `BORDER`, not a universal 1 mm margin.
- Reserve roughly 8–16 mm relief for portrait benchmarks before considering
  deeper ranges.
- Use a monotonic, piecewise depth curve that preserves the nose/eye/chin range
  while compressing large body-to-body separation.
- Enforce maximum slope, minimum feature width and point spacing based on the
  actual laser and blank, not only pixel resolution.
- Generate GLB, OBJ and a diagnostic 16-bit depth/normal/confidence bundle from
  one job manifest.

## Benchmark before buying licences

### Dataset

Create an internal, consented set of 30–50 images:

- one and two people;
- frontal, three-quarter and mild profile poses;
- children, adults and elderly people;
- glasses, facial hair and varied hairstyles;
- dark/light skin and varied lighting;
- sharp modern photos plus damaged archival photos;
- full head, bust and seated/full-body compositions.

Add a smaller capture set with multi-view photogrammetry or phone depth as
evaluation truth. Do not train on customer photographs without explicit
separate consent.

### Experiment matrix

1. Current Depth Anything output — frozen baseline.
2. Depth Pro, MoGe-2 and Marigold depth-only outputs.
3. Each winner plus its normal map and BiNI fusion.
4. Face branch off/on with 3DDFA_V2.
5. Commercial face candidate only after evaluation rights are confirmed.
6. Edge taper widths in physical millimetres, not arbitrary pixels.

### Measurements

- face landmark reprojection and visible silhouette error;
- normal consistency and high-frequency facial energy;
- nose/eye/lip/chin ordering and usable depth range;
- maximum edge-wall height and edge slope;
- holes, non-manifold faces and disconnected point clusters;
- GLB/OBJ geometry equivalence;
- blind human likeness ranking;
- physical crystal A/B review under the same laser settings.

No model is accepted from a nice depth preview alone. The final gate is the
engraved result.

## Implementation phases

### Phase 0 — fix geometry before adding models

- Implement distance-transform edge roll-off.
- Decouple the mesh-domain threshold from the alpha display threshold.
- Add diagnostic side-view and edge-slope images.
- Add regression fixtures for one and two subjects.

### Phase 1 — model adapter benchmark

- Add a common `DepthResult` contract: depth, normals, confidence, intrinsics,
  model id, licence id and timing.
- Add Depth Pro and MoGe-2 adapters.
- Upgrade Marigold from the current LCM v1.0 checkpoint to v1.1 depth and
  normals for comparison.
- Keep every model in its own reproducible environment/container.

### Phase 2 — normal integration

- Add BiNI with depth prior.
- Tune only on the consented benchmark set.
- Preserve face and silhouette discontinuities while smoothing skin noise.

### Phase 3 — face fusion

- Add 3DDFA_V2 baseline and multi-face routing.
- Benchmark HRN and commercially licensable MICA/DECA candidates.
- Purchase rights only when a measured physical-print improvement justifies it.

### Phase 4 — production calibration

- Build blank/laser-specific profiles.
- Add automated quality scores and manual-review routing.
- Connect the hosted job API between Model A and Model B.

## Purchase recommendation

Do **not** purchase a model licence before Phase 0–2. The current edge wall is
a deterministic geometry defect, and normal integration may deliver most of
the missing facial detail with commercially usable open components.

The first paid conversation should be with Max Planck about MICA/DECA commercial
rights, but only after a side-by-side benchmark proves that their face surface
beats the MIT 3DDFA_V2 baseline in real engravings. Paid GPU compute is likely
more valuable earlier than paid model rights because it makes the Marigold,
MoGe and normal-integration matrix practical to run.

## Primary references

- Apple Depth Pro: https://github.com/apple/ml-depth-pro
- MoGe-2: https://github.com/microsoft/MoGe
- Marigold depth and normals: https://github.com/prs-eth/Marigold
- Metric3D v2: https://github.com/YvanYin/Metric3D
- Bilateral Normal Integration: https://github.com/xucao-42/bilateral_normal_integration
- 3DDFA_V2: https://github.com/cleardusk/3DDFA_V2
- HRN: https://github.com/youngLBW/HRN
- DECA: https://github.com/yfeng95/DECA
- MICA: https://github.com/Zielon/MICA
- FLAME 2023 Open Model: https://flame.is.tue.mpg.de/
- Sapiens2 licence: https://github.com/facebookresearch/sapiens2/blob/main/LICENSE.md

