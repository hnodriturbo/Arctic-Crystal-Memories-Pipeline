<!--
File: docs/portrait-2.5d-pipeline-research-plan.md
Purpose:
 - Define the research and implementation path for a production-quality,
   print-ready adaptive 2.5D pipeline between Model A and Model B.
 - Give the owner and future agents one evidence-backed plan for model access,
   licensing, evaluation, geometry, cost and staged delivery.
-->

# Production 2.5D pipeline — research and build plan

**Status:** living architecture and experiment plan, reviewed 2026-08-29.

**Scope:** local research branch first; no VPS/production deployment until a
phase explicitly passes its exit criteria.

**Commercial policy:** paid APIs, paid checkpoints and commercial/on-prem model
licences are allowed when measured quality and total cost justify them.

## 1. Objective

Build ACM's own `AutoConvertTo3D`-style middle stage:

```txt
Model A: crop and compose the source photograph
    ↓
adaptive 2.5D conversion
    ↓
canonical relief geometry
    ├── GLB → Model B / three.js customer preview
    └── OBJ → point-cloud converter → DXF → engraving
```

The pipeline must retain the visible likeness of real people, handle useful
non-human photographs, fit actual Cockpit3D blank metadata and create a
manufacturable front relief. GLB and OBJ must always come from the same
canonical surface.

This is not a generic full-3D generator. A single photograph does not contain
the hidden back of a person. The target is a faithful, high-quality 2.5D front
surface, not an invented 360-degree human.

## 2. Honest meaning of “works for any image”

Every browser-supported input should be read and classified automatically. It
is neither technically honest nor safe to promise that every input will pass
without review. Each job must end in exactly one state:

| State | Meaning | Product behaviour |
|---|---|---|
| `auto-pass` | evidence and geometry meet production thresholds | show GLB in Model B and enable export |
| `auto-repair` | a deterministic repair can resolve the issue | repair, re-score, then pass or review |
| `manual-review` | usable but uncertain face, occlusion, ordering or detail | show diagnostics and operator controls |
| `request-new-photo` | evidence is insufficient or unsafe to infer | explain exactly what new photograph is needed |
| `unsupported` | format/content cannot use a current route | preserve source and give a clear reason |

A face only a few pixels wide, a fully occluded face, extreme motion blur or a
person almost outside the crop should request a new photo rather than invent
anatomy.

## 3. Product invariants

These rules are not experiment variables:

1. Original source, crop transform and consent/job metadata are immutable.
2. Customer images are not training data without separate explicit consent.
3. Face geometry is used for surface reconstruction, not identity matching.
4. `bright = near` is the canonical 16-bit depth convention.
5. X = width, Y = height and Z = depth; units are millimetres after fitting.
6. Per-axis Cockpit3D `SIZE`, `BORDER` and `BEVEL` are authoritative.
7. One canonical mesh creates both GLB and engraving OBJ.
8. Point-cloud density is 250,000–1,000,000 points according to physical blank
   size and detail bandwidth, not one fixed count.
9. Model B preview dot size defaults to and remains `0.08`.
10. Every artifact records model id, weight revision, licence id, parameters,
    timing and hashes so a result can be reproduced.
11. A good-looking depth PNG is not acceptance evidence; the engraved crystal
    is the final quality gate.

## 4. Current baseline and known defects

### 4.1 What is already correct

- Python 3.11 environment is locked and health-checked.
- Depth Anything V2 provides the current global depth scaffold.
- Native model resolution was measured: forcing about 518 px to 1024 px cost
  2.6× runtime and slightly reduced measured detail energy.
- Subject-only percentile normalisation prevents the background consuming most
  of the depth range.
- A 512 grid creates 262,144 vertices and 522,242 triangles.
- The same geometry exports GLB and OBJ.
- DXF parsing is gated to `ENTITIES`, removing the false HEADER points from
  `$EXTMIN` and `$EXTMAX`.
- The tested converter produced 101,248 centred engraving points.
- Real Cockpit3D borders and bevels are available. Rectangular blanks are
  correctly generated as bevelled boxes because they have no OBJ.
- BiRefNet portrait alpha is already available upstream.

### 4.2 Why current faces can be flat or distorted

1. Global monocular depth is a low-frequency scene scaffold. It does not
   reliably encode eyelids, lips, nostrils or cheek planes.
2. Upsampling cannot recreate geometry the model never predicted.
3. One normalised range across several people and furniture can compress one
   face into a tiny fraction of the relief.
4. Depth alone is the wrong high-frequency carrier. Facial detail should come
   from surface normals and an anatomical face prior.
5. The current mesh performs a hard alpha-domain cut after feathering. The
   fade is removed before it reaches the back plane, leaving a visible
   “cardboard wall” at silhouettes.
6. Hair, fingers, glasses and intersections need different confidence and
   smoothing behaviour from cheeks or clothing.

The first defect to fix is deterministic geometry, not a new neural network.

## 5. End-to-end adaptive architecture

```txt
source + Model A crop + selected blank
    ↓
decode, orient, colour-manage, hash, quality measurements
    ↓
open-vocabulary detection + instance masks + matte refinement
    ↓
subject graph and route decision
    ├── human: pose + body parts + face geometry + global depth/normals
    ├── animal: instance mask + global depth/normals + fur edge rules
    ├── object: instances + global metric geometry
    ├── landscape: whole-frame depth + plane/sky protection
    └── graphic/text: controlled layered relief or review
    ↓
per-instance scale/shift alignment and occlusion ordering
    ↓
depth prior + high-frequency normal integration
    ↓
inward silhouette roll-off + relief dynamic-range compression
    ↓
fit Cockpit3D safe volume + mesh validation
    ↓
canonical mesh
    ├── GLB preview
    ├── OBJ sampler input
    ├── 250k–1M point cloud / DXF
    └── diagnostics + manifest + quality decision
```

## 6. Canonical job and artifact contract

Every stage reads a job directory and writes new immutable artifacts. No stage
silently overwrites an earlier prediction.

```txt
jobs/<job-id>/
  source/original.<ext>
  source/composed.png
  source/transform.json
  intake/quality.json
  intake/route.json
  masks/instances.json
  masks/instance-000.png
  masks/instance-000-soft-alpha.exr
  geometry/global-depth.exr
  geometry/global-normals.exr
  geometry/global-confidence.exr
  geometry/face-000-depth.exr
  geometry/face-000-normals.exr
  geometry/fused-depth.exr
  geometry/fused-normals.exr
  geometry/silhouette-distance.exr
  output/relief.glb
  output/relief.obj
  output/engraving.dxf
  output/diagnostics/
  job.json
```

Use floating-point EXR or NumPy/Zarr internally. PNG is an interchange/preview
format. The canonical compatibility depth PNG remains 16-bit.

Minimum `job.json` content:

```json
{
  "schemaVersion": 1,
  "jobId": "uuid",
  "sourceSha256": "...",
  "cropTransform": {},
  "blank": {"templateId": "...", "sizeMm": [], "borderMm": [], "bevelMm": []},
  "route": {"type": "multi-human-scene", "confidence": 0.97},
  "subjects": [],
  "models": [],
  "reliefProfile": {},
  "pointProfile": {"targetCount": 500000, "dotSize": 0.08},
  "quality": {"state": "manual-review", "reasons": []},
  "artifacts": []
}
```

Each `models[]` record stores repository, exact weight revision/hash, code
revision, environment version, licence classification and GPU/CPU time.

## 7. Stage 0 — intake, quality and provenance

### 7.1 Decode and normalise

- Apply EXIF orientation once and record it.
- Convert the working copy into consistent linear/sRGB colour; preserve ICC
  metadata in the protected source.
- Reject corrupt and decompression-bomb inputs safely.
- Record dimensions, alpha, bit depth, aspect ratio and file hash.
- Never enlarge before measuring the source's real evidence.

### 7.2 Quality measurements

Measure before expensive inference:

- full-image and per-face blur;
- pixels across each detected face/body;
- highlight/shadow clipping;
- JPEG blocks and ringing;
- pose angle and out-of-frame fraction;
- occlusion of face, hands and subject;
- matte uncertainty and fine-hair edge complexity;
- subject count and overlap graph;
- conflict between Model A crop and blank safe area.

Initial thresholds must be conservative and calibrated on engravings. Store raw
measurements separately from acceptance thresholds.

### 7.3 Privacy and safety

- Keep local-only experiments local.
- Strip location EXIF from derivatives while retaining the protected original
  only as business rules require.
- Encrypt hosted storage and use expiring URLs later.
- Record retention/deletion state per job.
- This product needs facial geometry, not facial recognition or identity search.

## 8. Stage 1 — image understanding and routing

### 8.1 Recommended first routing stack

1. **Grounding DINO** detects classes such as person, face, sofa, chair,
   animal, vehicle, building, flower and product.
2. **SAM 2.1** converts boxes/points into separate instance masks.
3. **BiRefNet** refines the selected foreground/portrait soft matte.
4. **MediaPipe Pose/Face Landmarker** supplies fast pose and landmark checks.
5. Deterministic features select the route. Add a vision captioner/classifier
   only after this router has a measured confusion matrix.

Grounding DINO code is Apache-2.0; SAM 2.1 code and official checkpoints are
explicitly Apache-2.0; BiRefNet is MIT; MediaPipe is Apache-2.0. Store exact
checkpoint notices separately from source-code licences.

### 8.2 Route decision table

| Evidence | Route | Special processing | Review/failure triggers |
|---|---|---|---|
| one large face/bust | `portrait-close` | face prior, skin normals, hair/global branch | tiny/occluded face, extreme yaw |
| one full/seated person | `human-single` | body parts, pose prior, face branch | uncertain limb crossings |
| two or more people | `human-group` | separate person masks and face ranges | merged masks, ambiguous arms/faces |
| people plus sofa/chair | `human-object-scene` | split people/furniture, composite instances | unresolved contact boundaries |
| animal/pet | `animal` | generic depth/normals, fur-aware matte | face/detail too small |
| isolated object/product | `object` | metric geometry and rigid-edge preservation | transparent/mirrored uncertainty |
| architecture/landscape | `scene` | whole-frame metric depth, sky/plane constraints | texture-depth confusion |
| logo/text/line art | `graphic` | controlled layered/luminance relief | not natural-depth input |
| mixed/low confidence | `ambiguous` | cheap secondary detector or review | never guess silently |

### 8.3 Subject graph and object splitting

Do not flatten a scene into one mask. Each node stores class, box, hard mask,
soft alpha, global-depth statistics, overlaps, front/behind relationships,
contact boundaries, human subregions, route and confidence.

For two people on a sofa, create three primary nodes: person A, person B and
sofa. Process the people with the human branch, the sofa with the object branch,
then composite using global depth and occlusion boundaries. This is the relief
equivalent of Meshy's **Auto-Split**, performed before fusion while preserving
photographic ordering.

## 9. Stage 2 — masks, human parts and confidence

Keep three different fields:

- hard mask for topology/domain decisions;
- soft alpha for hair and anti-aliased transitions;
- confidence for uncertainty.

Required human labels include face skin, ears, hair, neck, torso/clothing,
left/right arm/hand, left/right leg/foot, accessories and unknown/occluded.

Sapiens/Sapiens2 are strong research references for parsing, pose, depth and
normals. Their public licences do not permit this commercial product: Sapiens
is CC BY-NC 4.0 and Sapiens2 adds restricted-use terms. Never ship either
without written commercial permission.

First production prototype: SAM 2 instances + MediaPipe constraints + an
audited part-segmentation model. If quality is insufficient, purchase a
commercial parsing licence or label a consented ACM set and fine-tune a
permissively licensed architecture.

## 10. Stage 3 — global depth, point maps and normals

Adapters emit one contract:

```python
DepthResult(
    depth,          # float32 monotonic camera depth
    normals,        # optional float32 HxWx3 outward camera normals
    confidence,     # optional float32 HxW
    valid_mask,
    intrinsics,
    scale_kind,     # metric | affine | relative
    model_record,
)
```

### 10.1 Production-capable candidates

| Candidate | Output/use | Access | Licence position | Priority |
|---|---|---|---|---|
| Depth Pro | sharp metric depth, focal estimate, boundary metrics | Apple repo/checkpoint | published Apple code/weight terms | Phase 1 baseline |
| MoGe-2 `vitl-normal` | metric points, depth, normals, mask, intrinsics | Microsoft repo + HF | repo MIT/Apache components; card marks MIT | Phase 1 baseline |
| MoGe-3 | newer fine-grained metric geometry | official repo/HF | verify selected card/revision | challenger |
| Metric3D v2 | metric depth, normals, confidence | Hub/HF/ONNX | BSD-2 code; authors request commercial contact | challenger |
| Marigold v1.1 | affine depth and high-detail normals | repo/Diffusers/HF | Apache code; OpenRAIL++-M weights | premium normals |
| SharpDepth | diffusion sharpening of metric prior | Qualcomm repo/release | BSD-3 Clear repo; audit Lotus/UniDepth assets | Phase 2 challenger |

### 10.2 Research/specialised candidates

| Candidate | Value | Limitation |
|---|---|---|
| DSINE | crisp in-the-wild normals and uncertainty | Imperial non-commercial licence; commercial contact required |
| MonoRelief V2 | direct depth/normal/mesh relief baseline | public model expects relief-style images, not raw natural scenes |
| Sapiens depth/normals | human-specific benchmark | public licence is non-commercial |

### 10.3 Fusion rule

Never average independently normalised maps. Convert conventions, retain scale,
robustly align scale/shift on confident regions, estimate local confidence,
select/fuse low-frequency depth by region, preserve instance discontinuities
and pass normals to integration instead of injecting noisy pixel depth.

## 11. Stage 4 — human-specific geometry

ECON is the closest published architectural reference. It predicts front/back
clothed-human normals, reconstructs 2.5D surfaces with depth-aware bilateral
normal integration and aligns a low-frequency body prior while keeping detail.
It also handles difficult clothes, poses and multiple people.

Its public licence is non-commercial. Commercial enquiries go to
`ps-license@tue.mpg.de`. ECON depends on SMPL-X, whose public model is academic;
commercial access is through `smpl@max-planck-innovation.de` or Meshcapade.

- Use ECON locally as a measured architecture/quality reference.
- Do not place its public weights/assets in production.
- Request commercial terms only if its benchmark gain is material.
- Independently build ACM's front-relief-specific path from appropriately
  licensed components when practical.

Pose is a constraint, not final surface geometry. It supplies connectivity,
side labels, plausible depth continuity and occlusion clues. Start with
Apache-2.0 MediaPipe Pose; consider paid SMPL-X/ECON only if pose remains a
dominant failure.

## 12. Stage 5 — face-specific geometry

The face branch supplies anatomy and normals inside a confidence-weighted skin
region. It must not replace hair, ears, neck or clothing.

### 12.1 Candidate ladder

| Candidate | Use | Public licence | Commercial action |
|---|---|---|---|
| MediaPipe Face | landmarks/pose/quality | Apache-2.0 code | audit task model |
| 3DDFA_V2 | fast dense alignment baseline | MIT repo | audit detector/BFM weights |
| HRN | detailed reconstruction challenger | Apache-2.0 repo | audit checkpoint/dependencies |
| FLAME 2023 Open | parametric face surface | CC BY plus stated restrictions; commercial allowed | register and attribute |
| DECA | expression/detail benchmark | non-commercial | contact `ps-license@tue.mpg.de` |
| MICA | metric identity-shape benchmark | non-commercial | contact `justus.thies@tuebingen.mpg.de` |
| Banuba Face AR SDK | paid mesh/landmark benchmark | commercial custom quote | validate still-image export and terms |

### 12.2 Face fusion

For each sufficiently large face:

1. crop with context and retain inverse transform;
2. fit and reject unstable landmark/pose solutions;
3. rasterise fitted depth/normals into original coordinates;
4. solve scale, shift and small pose correction against global geometry on
   stable cheek, temple, forehead and jaw regions;
5. create semantic skin mask excluding hair/accessories;
6. use face prior for low/mid-frequency anatomy;
7. use bounded predicted normals/displacement for detail;
8. blend by signed distance and confidence, not an oval;
9. fall back to global geometry where occluded/uncertain;
10. validate nose, lips, eyes and chin ordering.

GFPGAN/restoration may help operator inspection, but invented pixels cannot
silently become anatomical ground truth.

## 13. Stage 6 — depth/normal integration

```txt
global + face/body depth ──► low-frequency prior
predicted normals        ──► high-frequency gradients
confidence + masks       ──► weights and discontinuities
                                  ↓
                     integrated relief depth
```

Start from Bilateral Normal Integration (BiNI): it supports orthographic and
perspective cameras, outliers, discontinuities and a coarse depth prior. Record
normal convention, mask, prior depth/mask, `lambda1`, `k`, iterations and
convergence.

The official repo is GPL-3.0. Before production, deliberately comply, obtain
permission, or implement an independently specified solver from the paper with
legal review. Do not copy code and call it a clean-room implementation.

### 13.1 Frequency-aware relief

Classic relief research explains why linear depth scaling is insufficient:

1. base/scene ordering is heavily compressed but monotonic;
2. body/face form receives moderate compression;
3. eyes, lips, wrinkles, fabric and hair receive bounded enhancement;
4. model/sensor noise is suppressed.

Weyrich et al. treat relief as gradient-domain tone mapping. Ji et al. show
normal composition and screened-Poisson integration. These guide ACM's physical
mapping even though they are not pretrained models.

## 14. Stage 7 — inward-floating silhouette

Replace alpha multiplication plus a `0.5` mesh cut with a signed-distance
roll-off. For inside distance `d`, taper width `w`, surface `z` and back plane
`z_back`:

```txt
t = smoothstep(0, w, d)
z_final = z_back + t × (z - z_back)
```

Requirements:

- mesh the full taper domain and stop at a very low outer-alpha threshold;
- taper inward to the back plane before geometry ends;
- specify taper in physical millimetres;
- use wider/softer hair taper and narrower solid-clothing taper;
- cap edge slope and derivative changes;
- retain person/person and person/object contact discontinuities;
- never add a vertical skirt to engraving OBJ;
- add backing only to a separate 3D-print export.

This directly fixes the supplied “cardboard cut-out” side wall and must precede
model purchases.

## 15. Stage 8 — physical blank, relief and point calibration

### 15.1 Real blank fitting

- Use per-axis `BORDER`, including values such as `[10, 10, 2]`.
- Use template `BEVEL` for implicit rectangular/cube blanks.
- Fit imported OBJ per axis; source coordinates are not guaranteed mm/uniform.
- Reserve safety from glass surface and bevel.
- Keep the Model A transform linked to the fitted relief.

### 15.2 Relief curve

Start portrait benchmarks at 8–16 mm total relief. Use a monotonic piecewise
curve: preserve ordering, allocate extra face/contact range, compress large
scene gaps, preserve minimum visible differences, limit slope/feature width.

### 15.3 Point-cloud profile

| Setting | Meaning | Behaviour |
|---|---|---|
| target points | total samples | 250k–1M by usable area and detail class |
| point distance | XY separation | physical blank/laser calibration; override allowed |
| layer distance | Z separation | physical mm constrained by laser/optics |
| layers | depth layers | benchmark current 8, then calibrate |
| stagger | row/layer offset | preserve option; benchmark `2` |
| toning | density/intensity transfer | preserve and calibrate by material/photo route |
| dot size | Model B preview | default always `0.08` |

One million points cannot recover missing geometry. Count must follow physical
feature bandwidth, not input pixel count alone.

## 16. Model acquisition and isolated environments

Every external model lives in its own environment/container and communicates
through file/API contracts. Do not force incompatible Torch/CUDA stacks into
the current Python 3.11 venv.

### 16.1 Intake

#### Grounding DINO

- Official: <https://github.com/IDEA-Research/GroundingDINO>
- Clone, select CUDA-matched environment, `pip install -e .`.
- Download official Swin-T release weight.
- Emit boxes/labels/confidence; SAM owns masks.
- Paid challenger: official Grounding DINO 1.5/1.6 Pro/DeepDataSpace API when
  unusual classes fail locally. Upload only under approved privacy terms.

#### SAM 2.1

- Official: <https://github.com/facebookresearch/sam2>
- Follow official install/checkpoint script.
- Code, training code and official checkpoints are Apache-2.0.
- Use the image as one frame; save separate masks for detector prompts.

#### BiRefNet

- Official: <https://github.com/ZhengPeng7/BiRefNet>
- Python 3.11 environment; repository requirements or audited HF loading path.
- MIT repo; verify the exact checkpoint card.
- Role: high-resolution soft matte, not semantic naming.

#### MediaPipe

- Official: <https://github.com/google-ai-edge/mediapipe>
- `pip install mediapipe` in a small routing environment.
- Apache-2.0 code; record task-model provenance separately.

### 16.2 Global geometry

#### Apple Depth Pro

- Official: <https://github.com/apple/ml-depth-pro>
- Use recommended Python 3.9 conda environment, then `pip install -e .`.
- Run `source get_pretrained_models.sh` for `checkpoints/`.
- Output metric metres and focal length; reuse official boundary metrics.

#### MoGe-2 / MoGe-3

- Official: <https://github.com/microsoft/MoGe>
- Python 3.10+; `uv sync` is recommended, or `pip install -e .` with explicit
  PyTorch CUDA index.
- Baseline weight: `Ruicheng/moge-2-vitl-normal`.
- Load with matching `MoGeModel.from_pretrained(...)`.
- Capture points, depth, mask, normals and intrinsics.
- Test newer MoGe-3 large as challenger; test giant only if VRAM/cost warrants.
- ONNX optimisation comes after PyTorch parity.

#### Marigold v1.1

- Official: <https://github.com/prs-eth/Marigold>
- On Windows use recommended WSL2/Linux; isolated Python 3.10 environment.
- Depth: `prs-eth/marigold-depth-v1-1`.
- Normals: `prs-eth/marigold-normals-v1-1`.
- Start ensemble 1; larger ensembles only in controlled benchmarks.
- Store uncertainty when ensemble supports it.
- Apache code; OpenRAIL++-M weights and restrictions.

#### Metric3D v2

- Official: <https://github.com/YvanYin/Metric3D>
- Install `requirements_v2.txt`.
- First test: `torch.hub.load('yvanyin/metric3d',
  'metric3d_vit_small', pretrain=True)`.
- Capture depth/confidence and v2 normals/normal confidence.
- Compare ViT-S then ViT-L only if quality/GPU-second improves.
- BSD-2 code; follow repository request for commercial inquiry and verify
  checkpoint terms.

#### SharpDepth

- Official: <https://github.com/Qualcomm-AI-research/SharpDepth>
- Build supplied Docker image; configure Accelerate.
- Download/join official multipart v1 checkpoint per README.
- Treat as metric-depth refiner, not face anatomy or routing.
- BSD-3-Clause-Clear repo; audit required Lotus/UniDepth weights.

#### MonoRelief V2

- Official: <https://github.com/glp1001/MonoreliefV2>
- Apache-2.0 repo with `requirements.txt` and `relief_test.py`.
- Test raw Model A and a controlled relief-style intermediate separately.
- Authors explicitly say current public version expects relief images, not raw
  people/animals/scenes. Generative style conversion is not production-safe
  until likeness/hallucination is measured.
- MonoRelief V3 is available by author contact; paid evaluation is allowed
  after V2 proves the approach useful.

### 16.3 Integration

#### BiNI

- Official: <https://github.com/xucao-42/bilateral_normal_integration>
- Install requirements; CPU uses NumPy/SciPy, GPU uses CuPy.
- Begin `k=2`; provide coarse depth and tune `lambda1`.
- Float arrays internally, 16-bit normals only for interchange.
- GPL-3.0 production architecture/legal decision is mandatory.

### 16.4 Human and face

#### ECON

- Official: <https://github.com/YuliangXiu/ECON>
- Prefer Docker/Linux; repo includes Windows guidance.
- Research target: NVIDIA GPU around 12 GB+ VRAM.
- Record every downloaded dependency/asset licence.
- Public use non-commercial; commercial: `ps-license@tue.mpg.de`.

#### Sapiens / Sapiens2

- <https://github.com/facebookresearch/sapiens>
- <https://github.com/facebookresearch/sapiens2>
- Quarantined local research only. No production without written permission.

#### 3DDFA_V2

- Official: <https://github.com/cleardusk/3DDFA_V2>
- Follow official setup/ONNX path; wrap dense face/PNCC/depth artifacts.
- MIT repo, but complete dependency/weight BOM first.

#### HRN

- Official: <https://github.com/youngLBW/HRN>
- Use its conda/checkpoint setup; test only large enough face crops.
- Audit checkpoint, RetinaFace and BFM assets independently.

#### DECA

- Official: <https://github.com/yfeng95/DECA>
- Register for required FLAME assets; local research only under public terms.
- Licence explicitly forbids commercial artifacts.
- Commercial: `ps-license@tue.mpg.de`.

#### MICA

- Official: <https://github.com/Zielon/MICA>
- Run `./install.sh` or supplied conda environment.
- Register for FLAME2020; place MICA checkpoint and separately audit required
  InsightFace weights.
- Output PLY and FLAME parameters for rasterising a face prior.
- Public licence non-commercial; commercial:
  `justus.thies@tuebingen.mpg.de`.

#### FLAME and SMPL-X

- FLAME licences: <https://flame.is.tue.mpg.de/modellicense.html>
- SMPL-X licence: <https://smpl-x.is.tue.mpg.de/modellicense.html>
- Prefer FLAME 2023 Open when sufficient; commercial use is allowed under its
  CC BY terms and stated restrictions.
- Older FLAME and public SMPL-X are non-commercial.
- SMPL-X commercial: `smpl@max-planck-innovation.de`.

#### Paid Banuba benchmark

- Official: <https://www.banuba.com/banuba-pricing-face-ar-sdk>
- Request free trial/POC and written quote.
- Confirm server-side still processing, mesh derivation/export, privacy and
  intended volume. AR tracking alone is not a relief geometry contract.
- Benchmark landmark fit and physical engraving, not marketing renders.

## 17. Licence gate

Engineering triage, not legal advice; exact revisions/dependencies matter.

| Class | Examples | Allowed now |
|---|---|---|
| production candidate | Depth Pro, MoGe-2 card, SAM 2.1, Grounding DINO, BiRefNet, MediaPipe, FLAME 2023 Open | benchmark; production after BOM/terms review |
| conditional/review | Marigold OpenRAIL, Metric3D weights, SharpDepth stack, 3DDFA/HRN assets, BiNI GPL | benchmark; legal/architecture decision before production |
| research-only public | Sapiens, Sapiens2, DSINE, ECON, DECA, MICA, SMPL-X public | local non-commercial evaluation only |
| paid commercial path | ECON/DECA/SMPL-X/possibly MICA, Banuba, paid Grounding DINO | request terms after measured benefit |
| unknown | checkpoint with no attributable licence | do not place in production cache or ship |

Maintain `model-registry.json` with status (`research-only`,
`evaluation-approved`, `production-approved`), code/weight/data licences,
revision, source, commercial contract, privacy boundary and review date. The
production runner must refuse unapproved adapters.

## 18. Paid access and buy-versus-build

Paid access is allowed, but payment must buy measured quality or reduce
operational risk/cost.

### 18.1 Valid spending categories

1. Commercial on-prem model licence: DECA/ECON/SMPL-X/MICA-type rights.
2. Specialised SDK/API: Banuba or Grounding DINO Pro when it wins.
3. GPU compute: RunPod, Modal, Hugging Face Endpoints or similar.
4. Consented data/expert labelling and physical engraving evaluation. This may
   create more durable value than another generic subscription.

### 18.2 Cost model

```txt
reference_monthly_cost = images_per_month × 10 USD

compute_per_image = gpu_seconds × gpu_hourly_rate / 3600
internal_per_image = compute + storage/egress
                   + expected_review_minutes × labour_rate/60

break_even_images =
  (licence + hardware + integration_cost + annual_support)
  / (10 USD - internal_variable_cost_per_image)
```

As of 2026-08-29, official RunPod posted serverless examples include about
USD 0.69/hour for a 24 GB class worker and USD 1.10/hour for a 4090-class
worker. At USD 1.10/hour, three GPU minutes cost about USD 0.055 and ten about
USD 0.183 before cold start, storage, retries, review and engineering. Prices
change; recompute from official pages. The likely dominant costs are review
labour, integration and licence amortisation rather than raw inference.

Dedicated endpoints bill while active/initialising and suit steady volume.
Per-second serverless is better for early bursts; a local workstation becomes
better at predictable utilisation.

### 18.3 Purchase gates

Before annual/perpetual licence purchase:

- fix deterministic edge/mesh defects;
- compare open and paid candidate on the same locked benchmark;
- complete at least 10 blind physical A/B engravings;
- confirm customer-artifact, hosting and privacy rights in writing;
- include manual review in per-image economics;
- understand fallback/export rights if vendor service ends.

Paid trials and modest GPU spend are encouraged earlier.

## 19. Benchmark dataset and truth

Build a consented versioned 50–100 image set:

- close portraits, busts, seated/full bodies;
- one, two and groups;
- people on furniture/holding objects;
- frontal, three-quarter, mild profile, crossed limbs;
- children, adults and elderly people;
- diverse skin, hair, facial hair, glasses and hats;
- modern photos and damaged archival images;
- pets, rigid products, architecture, flowers and landscapes;
- transparent/reflective/low-texture failure cases;
- intentionally bad images for gate tests.

For a smaller truth subset obtain consented multi-view/phone-depth/scans,
corrected masks/ordering, approved relief and physical crystal. Freeze
development, validation, blind-test and production-shadow splits. Do not tune
repeatedly on one attractive example.

## 20. Metrics and acceptance

### 20.1 Geometry

- mask IoU and boundary F-score;
- face landmark reprojection;
- face/body/occlusion quality-gate accuracy;
- depth boundary accuracy/completion;
- normal angular error where truth exists;
- depth-normal consistency/integrability residual;
- silhouette distance, wall height and slope;
- facial feature ordering;
- bounded detail energy;
- instance ordering;
- holes, non-manifold edges, degenerates/components;
- GLB/OBJ geometry equivalence.

### 20.2 Manufacturing

- point count and nearest-neighbour distribution;
- layer separation and out-of-volume points;
- local slope and minimum feature width;
- silhouette bright seams;
- border/bevel clearance;
- file/converter/laser time;
- blind likeness under identical glass/laser/lighting.

### 20.3 Operations

- GPU seconds, VRAM, cold start and total latency;
- retries and failure reason;
- pass/repair/review/reject rates by route;
- manual minutes per accepted image;
- internal cost per accepted image;
- performance by model revision.

Initial release requires no visible vertical edge wall, no unsafe-volume points,
reproducible manifests, correct review routing and production-approved licences.
Set numeric quality targets after measuring the frozen baseline; physical blind
comparison with the current paid reference is the final gate.

## 21. Controlled experiment matrix

1. Frozen Depth Anything baseline.
2. Same prediction with signed-distance edge fix.
3. Depth Pro, MoGe-2, MoGe-3 and Metric3D depth-only.
4. Marigold/Metric3D/MoGe normals with one coarse prior.
5. Integration settings with identical depth-normal pair.
6. Face branch off/on with 3DDFA_V2.
7. HRN, DECA/MICA research and paid Banuba trial on same crops.
8. Per-person range allocation off/on.
9. Semantic taper widths in physical mm.
10. Relief curves at fixed 8/12/16 mm.
11. 250k/500k/750k/1M sampling by blank.
12. Physical A/B against paid reference.

Cache model outputs so geometry experiments do not rerun expensive inference.

## 22. Implementation roadmap

### Phase 0 — deterministic geometry and harness

**Work:** signed-distance roll-off; decouple mesh threshold; side/slope
diagnostics; manifest/model registry; one-person/two-person/person+sofa
fixtures; shared point/layer/stagger/toning profile with 0.08 preview dot.

**Exit:** supplied edge reaches back plane without wall; GLB/OBJ parity passes;
baseline reproducible; no purchase required.

### Phase 1 — router and subject graph

**Work:** quality measurements; Grounding DINO + SAM 2.1 + BiRefNet; MediaPipe
checks; route table; instance/occlusion graph; review reasons/UI.

**Exit:** measured routing confusion matrix; two people + sofa become three
stable nodes; uncertain cases never auto-pass.

### Phase 2 — global adapter benchmark

**Work:** `DepthResult`; Depth Pro and MoGe-2 first; Metric3D/Marigold;
MoGe-3/SharpDepth; MonoRelief specialised test; time/VRAM/licence metadata.

**Exit:** winner selected per route and quality/GPU-second; research-only
adapters blocked from production; conventions aligned.

### Phase 3 — normal integration and frequency mapping

**Work:** depth-prior BiNI prototype; normal comparison; multi-band relief;
instance discontinuities/noise suppression; 8/12/16 mm physical tests.

**Exit:** measured and physical detail improvement without edge/noise penalty;
solver licence/implementation decision recorded.

### Phase 4 — face branch

**Work:** 3DDFA baseline; rasterised face depth/normals; semantic skin blending;
HRN, DECA/MICA research and Banuba trial; commercial quote only for winner.

**Exit:** blind face/likeness improvement; multi-face separate range; full
production rights/BOM.

### Phase 5 — body/pose/occlusion

**Work:** body-part constraints; ECON/Sapiens research benchmark; commercial
SMPL-X/ECON terms if necessary; crossed limbs/hands/clothes/contact fixes;
manual repair tools.

**Exit:** target seated/full-body/group pass-review rates; no invented hidden
anatomy; commercial decision complete.

### Phase 6 — laser/point calibration

**Work:** map blank/detail to 250k–1M; calibrate distances, layers, stagger,
toning; laser/glass profiles; measure density/seams/feature survival.

**Exit:** profiles visible in manifest/UI; no unsafe points; 0.08 preview keeps
correct physical density ordering.

### Phase 7 — shadow production and hosted integration

**Work:** paid reference and ACM side-by-side; shadow mode; cost/manual metrics;
queue/privacy/retention/retries/observability; Model A → 2.5D → Model B UI.

**Exit:** sustained representative quality/cost; paid fallback remains; explicit
approval before any VPS deployment.

### Phase 8 — train/distil ACM models

Only after deterministic/ensemble labels are trustworthy:

- gather separately consented RGB/masks/normals/depth/approved reliefs;
- accept pseudo-labels only with multi-model agreement + review;
- train route-specific matte/normal/depth refiners first;
- distil expensive ensemble into faster ACM student;
- track immutable experiment lineage;
- balance demographics, pose and source quality;
- blind-test on identities absent from training.

Exit requires quality parity, lower cost, dataset/model cards and documented
consent/provenance.

## 23. Recommended first 30 working days

**Days 1–5:** freeze benchmark; edge-domain fix; diagnostics; manifest/registry;
two physical edge samples.

**Days 6–10:** detector/SAM/BiRefNet graph; person+sofa split; quality states.

**Days 11–17:** Depth Pro/MoGe-2 wrappers; full time/VRAM/edge/face benchmark;
choose coarse-depth baseline per route.

**Days 18–23:** Marigold/Metric3D normals; prior-guided integration; frequency
mapping; 8/12/16 mm comparison.

**Days 24–30:** 3DDFA baseline; ten controlled physical A/Bs; evidence pack for
commercial trials; choose next work from measured failure categories.

## 24. Agent working rules

Future agents must:

1. use the local 2.5D branch unless production is explicitly authorised;
2. never deploy research models/customer photos to VPS;
3. inspect code/fixtures before architecture changes;
4. add one adapter/environment at a time;
5. record code, weight and dependency licences before production caching;
6. never call research-only weights commercially safe;
7. preserve hashed baselines;
8. make small reversible commits after tests;
9. compare physical geometry, not marketing images;
10. review/reject insufficient evidence rather than hallucinating;
11. update this plan with measured results and failed experiments;
12. never push GitHub without the user's explicit instruction.

## 25. Open decisions

- Available local GPU/VRAM/driver/CUDA?
- Real laser minimum XY/Z spacing by glass/blank?
- Relief range matching paid Cockpit3D reference?
- GPL BiNI compliance/licence versus independent solver?
- Can FLAME 2023 Open + permissive fitting match DECA/MICA?
- Will Banuba licence still-image mesh export/server processing?
- Does paid MonoRelief V3 accept natural photos?
- Monthly volume and manual minutes defining break-even?
- Customer consent/retention rules before hosting?

## 26. Primary sources

### Intake

- [Grounding DINO repository](https://github.com/IDEA-Research/GroundingDINO)
- [Grounding DINO paper](https://arxiv.org/abs/2303.05499)
- [Grounding DINO 1.5 API](https://github.com/IDEA-Research/Grounding-DINO-1.5-API)
- [SAM 2 repository/licence](https://github.com/facebookresearch/sam2)
- [BiRefNet repository](https://github.com/ZhengPeng7/BiRefNet)
- [MediaPipe repository](https://github.com/google-ai-edge/mediapipe)
- [MediaPipe Pose API](https://ai.google.dev/edge/api/mediapipe/python/mp/tasks/vision/PoseLandmarker)

### Depth and normals

- [Depth Pro repository](https://github.com/apple/ml-depth-pro)
- [Depth Pro paper](https://arxiv.org/abs/2410.02073)
- [MoGe repository](https://github.com/microsoft/MoGe)
- [MoGe-2 paper](https://arxiv.org/abs/2507.02546)
- [MoGe-2 depth/normal card](https://huggingface.co/Ruicheng/moge-2-vitl-normal)
- [Metric3D v2 repository](https://github.com/YvanYin/Metric3D)
- [Metric3D v2 paper](https://arxiv.org/abs/2404.15506)
- [Marigold repository](https://github.com/prs-eth/Marigold)
- [Marigold paper](https://arxiv.org/abs/2312.02145)
- [Marigold model licence](https://github.com/prs-eth/Marigold/blob/main/LICENSE-MODEL.txt)
- [SharpDepth repository](https://github.com/Qualcomm-AI-research/SharpDepth)
- [SharpDepth CVPR paper](https://openaccess.thecvf.com/content/CVPR2025/html/Pham_SharpDepth_Sharpening_Metric_Depth_Predictions_Using_Diffusion_Distillation_CVPR_2025_paper.html)
- [DSINE repository](https://github.com/baegwangbin/DSINE)
- [DSINE CVPR paper](https://openaccess.thecvf.com/content/CVPR2024/html/Bae_Rethinking_Inductive_Biases_for_Surface_Normal_Estimation_CVPR_2024_paper.html)

### Relief and integration

- [MonoRelief V2 repository](https://github.com/glp1001/MonoreliefV2)
- [MonoRelief V2 paper](https://arxiv.org/abs/2508.19555)
- [BiNI repository](https://github.com/xucao-42/bilateral_normal_integration)
- [BiNI ECCV 2022 paper](https://www.ecva.net/papers/eccv_2022/papers_ECCV/html/3202_ECCV_2022_paper.php)
- [Digital Bas-Relief from 3D Scenes](https://people.eecs.berkeley.edu/~sequin/CS285/PAPERS/SIGGRAPH_07/032-weyrich_3D_BasRelief.pdf)
- [Normal Image Manipulation for Bas-relief](https://arxiv.org/abs/1804.06092)
- [Bas-relief Modeling from Normal Images](https://orca.cardiff.ac.uk/id/eprint/58823/)

### Human and face

- [Sapiens paper](https://arxiv.org/abs/2408.12569)
- [Sapiens repository/licence](https://github.com/facebookresearch/sapiens)
- [Sapiens2 repository/licence](https://github.com/facebookresearch/sapiens2)
- [ECON repository](https://github.com/YuliangXiu/ECON)
- [ECON CVPR paper](https://openaccess.thecvf.com/content/CVPR2023/html/Xiu_ECON_Explicit_Clothed_Humans_Optimized_via_Normal_Integration_CVPR_2023_paper.html)
- [ECON licence/commercial path](https://github.com/YuliangXiu/ECON/blob/master/LICENSE)
- [3DDFA_V2 repository](https://github.com/cleardusk/3DDFA_V2)
- [3DDFA_V2 paper](https://arxiv.org/abs/2009.09960)
- [HRN repository](https://github.com/youngLBW/HRN)
- [HRN CVPR paper](https://openaccess.thecvf.com/content/CVPR2023/html/Lei_A_Hierarchical_Representation_Network_for_Accurate_and_Detailed_Face_Reconstruction_CVPR_2023_paper.html)
- [DECA repository](https://github.com/yfeng95/DECA)
- [DECA paper](https://arxiv.org/abs/2012.04012)
- [DECA licence/contact](https://github.com/yfeng95/DECA/blob/master/LICENSE)
- [MICA repository](https://github.com/Zielon/MICA)
- [MICA paper](https://arxiv.org/abs/2204.06607)
- [MICA licence/contact](https://github.com/Zielon/MICA/blob/master/LICENSE)
- [FLAME licences](https://flame.is.tue.mpg.de/modellicense.html)
- [SMPL-X licence/commercial path](https://smpl-x.is.tue.mpg.de/modellicense.html)
- [Banuba Face AR pricing/features](https://www.banuba.com/banuba-pricing-face-ar-sdk)

### Compute pricing

- [RunPod pricing](https://www.runpod.io/pricing)
- [Hugging Face Endpoints pricing](https://huggingface.co/docs/inference-endpoints/pricing)
- [Modal pricing](https://modal.com/pricing)
- [Replicate pricing](https://replicate.com/pricing)

## 27. Immediate recommendation

Implement **Phase 0** next: signed-distance silhouette domain and side-view
regressions. In parallel freeze the benchmark and model registry. Then add
Depth Pro and MoGe-2 before a long-term licence purchase. Paid trials and GPU
compute are welcome during benchmarking; annual licences wait for physical A/B
evidence.
