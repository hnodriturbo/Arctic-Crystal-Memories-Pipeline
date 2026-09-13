<!--
File: .Markdown/plans/2026-09-04-SMPL-X-HRN-HAIR-DEPTH-EXPERIMENT.md
Purpose:
 - Define the controlled personal SMPL-X, HRN, hair-shell, and portrait-depth experiment for 2026-09-04.
-->

# 2026-09-04 — SMPL-X + HRN + hair + deeper portrait test

Status: **READY FOR LOCAL PERSONAL RESEARCH**

## Why this test is needed

The reviewed `amma-2` 0.42/0.26 candidate is still too shallow in MeshLab:

- the head has insufficient front-to-back volume;
- the shoulders need more depth, while the reviewed lower garment/body is good;
- the closed HRN cranium is smooth and bald because HRN supplies a generic
  closed scalp, not source-derived hair geometry;
- the HRN-to-garment neck ownership seam is not finished.

The next run must therefore test depth, hair, and neck continuity separately.
Increasing head depth alone cannot repair missing hair.

The thin garment surface itself is accepted. Where that garment is truncated by
the source image frame, a separate frame-cut backfill must stretch the boundary
rearward; this is closure geometry, not artificial garment thickness.

## New research defaults

The portrait research defaults are raised to:

| Setting | Rejected reviewed value | New default |
| --- | ---: | ---: |
| Native HRN head depth span | 0.42 | **0.60** |
| MoGe lower body/clothing depth span | 0.26 | **0.26 — frozen** |
| Feathered shoulder-only boost | none | **+0.12** |
| Source-frame cut backfill | none | **disabled by default** |

The 0.60 head gives an estimated depth/width ratio near 0.95 for this registered
HRN mesh. It remains a source-facing 2.5D representation, but is no longer a
near-flat facial plate. The old values remain preserved in their immutable run
folders.

## Exact local inputs

- Source cut-out: `output/local-workbench/a3c0aadb7e3c/source-prepared.png`
- Original opaque MoGe input: `output/local-workbench/preprocess/898dfc7155e0/02-upscaled.png`
- MoGe-2 ViT-L metric depth: `output/research/portrait-v33-direct-hrn-original-moge/01-moge-original/depth_raw.npy`
- Native HRN head: `output/local-workbench/a3c0aadb7e3c/12-hrn-head/source-prepared/hrn-head.obj`
- HRN registration assets: `output/local-workbench/a3c0aadb7e3c/13-hrn-fusion-assets/`
- SMPL-X v1.1 archive: `Models/research/ECON/model-assets/downloads/models_smplx_v1_1.zip`
- Unpacked SMPL-X models: `Models/research/ICON/data/smpl_related/models/smplx/`
- PIXIE/SMPL-X 2020 support: `Models/research/ICON/data/pixie_data/`
- Legacy SMPLify archive, useful only as a historical comparison:
  `Models/research/ECON/model-assets/downloads/mpips_smplify_public_v2.zip`

The legacy `mpips_smplify_public_v2.zip` is **not SMPLify-X**. The requested
SMPLify-X implementation is the separate upstream repository at
<https://github.com/vchoutas/smplify-x/tree/master> and must receive its own
isolated checkout/environment.

The locked-head and Blender 10/300-shape packages are separate test inputs. If
they have not been downloaded from the signed-in official SMPL-X account before
the run, their variants are marked `BLOCKED_MISSING_ASSET`; they are not silently
replaced with a different package.

## Model ownership

```text
HRN native mesh
  -> visible face identity, ears, jaw, and source-registered front cranium

SMPL-X v1.1 / PIXIE fit
  -> anatomical neck, shoulder support, pose/camera prior, and closed hidden shell

Locked-head SMPL-X variant
  -> A/B candidate for a stable head-to-neck attachment ring

MoGe-2 ViT-L
  -> visible garment/body relief and source-relative metric depth

BiRefNet + projected HRN silhouette
  -> subject silhouette and source-evidence residual used to locate exterior hair

Source grayscale
  -> visible appearance
```

SMPL-X must not replace HRN facial identity. Its visible contribution is clipped
below a bounded jaw/neck ring unless a separate QA result proves an improvement.

## Morning learning session — getting to know SMPLify-X

Before fitting an ACM image, walk through the upstream project in this order:

1. distinguish the **SMPL-X body model** from the **SMPLify-X optimizer**;
2. inspect `cfg_files/fit_smplx.yaml` and identify every required path;
3. inspect `smplifyx/main.py` as the command entry point;
4. follow image loading and OpenPose JSON keypoints through the fitting flow;
5. identify the camera, body-pose, hand, jaw, expression, and shape parameters;
6. understand VPoser as a body-pose prior rather than a depth estimator;
7. inspect the objective stages and optional self-intersection penalty;
8. locate mesh and parameter outputs and render them with
   `smplifyx/render_results.py`;
9. compare SMPL-X, SMPL+H, and SMPL configuration files;
10. record which outputs can become a bounded neck/shoulder prior for ACM.

The official input contract is:

```text
DATA_FOLDER/
  images/       # source images
  keypoints/    # matching OpenPose JSON output
```

The first upstream smoke command will be assembled from:

```text
python smplifyx/main.py
  --config cfg_files/fit_smplx.yaml
  --data_folder <isolated ACM test data>
  --output_folder <isolated research output>
  --visualize=False
  --model_folder <local licensed SMPL-X models>
  --vposer_ckpt <local VPoser checkpoint>
  --part_segm_fn <local smplx_parts_segm.pkl>
```

Do not run this command until OpenPose, VPoser, part segmentation, and the
isolated dependency environment have passed a read-only asset audit. Upstream
documents Python 3.6, CUDA 10.0, CuDNN 7.3, and PyTorch 1.0, so the first task is
compatibility planning rather than contaminating the current Python environment.

## Hair-shell method

The hair in the source visibly extends beyond the generic HRN scalp. Tomorrow's
hair candidate uses a source-evidence residual:

1. project the registered closed HRN head into the source camera;
2. subtract that projected scalp silhouette from the subject alpha inside a
   bounded head ROI;
3. keep only connected residual regions above and beside the cranium;
4. reject garment, glasses, skin holes, and background components;
5. create a watertight feathered multi-ring hair shell rather than independent
   horizontal fringe strips;
6. glide the shell into HRN over a bounded overlap band;
7. use MoGe/source luma to retain coarse hair volume and appearance.

The previously rejected `fringe` mode is not reused because it produced teeth
and side spikes.

## Independent eyeglasses layer

The source glasses must not remain painted into the HRN skin. A separate
`EYEGLASSES_FRAME` experiment is included after the head/hair ownership is
stable:

1. derive the glasses ROI from face and eye landmarks;
2. segment and trace both rims, the bridge, and visible temples;
3. fit a symmetric thin-frame template in the source camera;
4. project each curve against HRN facial depth and offset it slightly forward;
5. create bevelled frame geometry and optional shallow lens surfaces;
6. preserve face, glasses, and lenses as separate GLB layers.

The architecture follows dedicated single-image eyeglasses reconstruction
research, while remaining explicit about which hidden temple portions are
template-inferred. See [eyeglasses research](../models/EYEGLASSES/README.md).

## Source-frame cut backfill — rejected as a default

The first 0.24-deep frame-cut test made the naturally thin garment look like a
large block. User review rejected it for this portrait class. The subject may
touch the straight left, right, or bottom image boundary without implying that
the cut garment should become thick.

The implemented feature remains available only as an explicit research option:

- only boundary edges within 5 px of the image frame are selected;
- curved natural silhouette edges inside the image are left unchanged;
- the accepted front garment surface is left unchanged;
- rear depth must be selected per image and begin substantially below 0.24;
- a 7 px inward feather prevents a hard exposed 90-degree wall;
- left, right, top, and bottom edge counts are recorded independently.

The default candidate contains no frame-cut backfill. The thin source-facing
garment is preserved.

## AC3D reference comparison

The user will generate an AC3D result from the same `amma-2.jpeg` source on
2026-09-04. Preserve that output as external reference evidence; do not tune ACM
to an unrecorded screenshot.

Collect:

- the exact AC3D input image and its SHA-256;
- exported AC3D mesh/file if available;
- AC3D model/version, chosen preset, depth, crop, and output-size settings;
- front, 30-degree, left-profile, and right-profile screenshots;
- triangle/vertex count and physical dimensions when the application exposes them.

Normalize AC3D and ACM only for camera, orientation, and overall height. Do not
silently change depth independently. Compare:

1. face identity and wrinkles;
2. front-to-back head depth;
3. source-derived hair volume;
4. independent glasses geometry versus painted relief;
5. jaw, neck, and shoulder transition;
6. treatment of image-frame-cut garment edges;
7. side-view spikes, holes, and invented anatomy.

The AC3D result is a benchmark, not training data and not proof of which internal
models it uses. Every observed advantage becomes a separately controlled ACM
hypothesis.

## Controlled run matrix

| Run | Head | Body | SMPL-X role | Hair role | Purpose |
| --- | ---: | ---: | --- | --- | --- |
| A | 0.60 | 0.26 + 0.12 shoulder-only | None | None | Deeper head/shoulder control; lower torso unchanged |
| B | 0.68 | 0.26 + 0.12 shoulder-only | None | None | Upper head-depth bound; detect over-depth |
| C | Best A/B | Same as A | PIXIE + SMPL-X v1.1 neck/shoulder support | None | Isolate neck continuity gain |
| D | Best C | Same as A | Same as C | Source-residual watertight hair shell | Full candidate |
| E | Best D | Same as A | Locked-head package | Same hair shell | Locked-head comparison, asset permitting |
| F | Best D | Same as A | Blender 10-shape, then 300-shape | Same hair shell | Shape-capacity comparison, asset permitting |
| G | Best D/E/F | Same as A | Winning neck/head support | Same hair shell + independent glasses | Verify accessory geometry |

Only one variable changes between adjacent runs. The Unity package is not part
of geometry selection; it gets a later GLB/rig/axis/scale interchange test.

## QA and acceptance criteria

Every run must produce and be visually inspected as:

- front render;
- 30-degree render;
- left profile;
- right profile;
- MeshLab/Blender wireframe or neutral-material geometry check;
- artifact gallery with full-resolution images and contact sheet.

A candidate passes only when:

- the face still resembles the source;
- cranium depth is visibly credible and not stretched;
- white hair has source-aligned volume instead of a smooth bald scalp;
- no hair teeth, horizontal strips, or 90-degree walls appear;
- neck and garment meet without a black hole or jagged overlap;
- no hidden hands, torso, or anatomy are presented as source-derived detail;
- GLB validates and imports in both the local viewer and Blender/MeshLab;
- model roles, parameters, hashes, triangle count, and rejection reasons are recorded.

## Environment and isolation

This is a personal, local, non-production research test. SMPL-X/SMPLify-X files,
derived fitting caches, and outputs remain under `converter/2.5D-pipeline` and
are not deployed to the production website. SMPLify-X has an old upstream
dependency stack, so its environment is kept separate from the working local
workbench virtual environment.

## Deliverable

The final deliverable for the test day is one comparison gallery containing A–F
or an explicit `BLOCKED_MISSING_ASSET` card for unavailable official packages,
plus a written decision for:

- default portrait head/body depth;
- HRN versus locked-head ownership;
- 10 versus 300 shape fitting value;
- accepted hair-shell method;
- accepted neck stitch method;
- accepted eyeglasses frame/lens method;
- next run to expose in the local workbench.
