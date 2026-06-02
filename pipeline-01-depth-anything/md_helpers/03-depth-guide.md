<!--
File: pipeline-01/md_helpers/03-depth-guide.md
Purpose: Stage 03 depth decisions log — profiles, model choices, blocked paths, and proposed enhancements.
-->

# Stage 03 — Depth Guide

> Covers: edge masking profiles, ZoeDepth blocker, paid tool evaluation, facial depth enhancement (Step 3.5), and workflow paths.
> For CLI usage and model list, see `pipeline-guide.md` Stage 03 section.

---

## Table of Contents

- [Depth Profiles](#depth-profiles)
  - [standard](#profile-standard)
  - [soft_edges_v1](#profile-soft_edges_v1)
  - [soft_edges_feathered](#profile-soft_edges_feathered)
  - [How to add a new profile](#how-to-add-a-new-profile)
- [ZoeDepth — Blocked](#zoedepth--blocked)
- [Paid Depth Tools Worth Evaluating](#paid-depth-tools-worth-evaluating)
- [Facial Depth Enhancement — Proposed Step 3.5](#facial-depth-enhancement--proposed-step-35)
- [Recommended Workflow Paths](#recommended-workflow-paths)
- [Pre/Post Run Checklist](#prepost-run-checklist)

---

## Depth Profiles

Every named profile in `DEPTH_PROFILES` has an entry here explaining what it does, why it was added,
and when. Old profiles are never deleted — they stay in the code and this log so any past run
can be reproduced exactly.

To use a profile:
```powershell
python 03_depth_estimate.py --profile soft_edges_feathered
```
Or set `DEPTH_PROFILE=soft_edges_feathered` in `.env` to make it the default.

---

### Profile: `standard`
**Added:** 2026-05-28 | **Status:** Stable (default)

Binary hard cut. Any pixel where alpha = 0 (background) is set to depth 0.
Subject pixels (alpha > 0) keep their raw model depth unchanged.

Added on initial implementation — simplest correct behaviour that prevents background
ghost geometry from entering the mesh.

**Limitation:** Creates a hard geometric cliff at the subject boundary. If the Stage 02 mask
is binary (no soft transitions at hair/edge), this cliff shows up in the mesh as a sharp wall
around the subject.

---

### Profile: `soft_edges_v1`
**Added:** 2026-05-29 | **Status:** Experimental

Uses the actual alpha channel value as a linear multiplier on depth.
A pixel with alpha=128 (50% transparent) gets 50% of its raw depth value.
Fully transparent (alpha=0) reaches 0. Fully opaque (alpha=255) is unaffected.

Added because Stage 02 often has semi-transparent pixels at hair and edge boundaries.
`standard` ignores this — any alpha > 0 passes through unchanged. This profile uses it
to create a natural depth fade at the silhouette without manual Photoshop correction.

**Limitation:** Only helps if the input mask has soft (semi-transparent) edges. On a binary mask,
this profile behaves identically to `standard`. Use `soft_edges_feathered` for binary masks.

---

### Profile: `soft_edges_feathered`
**Added:** 2026-05-29 | **Status:** Experimental

Combines both fixes:
1. Alpha value used as linear weight (same as `soft_edges_v1`)
2. Gaussian blur applied to the alpha weight before multiplication

The Gaussian blur (`sigma=10.0px` at 3840px resolution) widens the transition zone at the
silhouette boundary. Even a fully binary mask (0 or 255 only) gets a smooth ramp after blurring.
Depth near edges fades gradually to 0 rather than dropping off a cliff.

Added when Stage 02 alpha matting Cholesky step failed on the first production image, producing
a binary mask. Designed to recover acceptable edge quality from a binary mask without requiring
manual Photoshop correction.

**Tuning `--feather` at 3840×3840:**

| sigma | Fade width         | Use when                                         |
| ----- | ------------------ | ------------------------------------------------ |
| `5`   | ~10–15px narrow    | Soft mask already has good edges                 |
| `10`  | ~20–30px moderate  | Starting point for most images                   |
| `20`  | ~50px wide         | Very hard binary mask with visible cliff         |
| `50+` | Very wide          | Aggressive — may eat thin features (hair, ears)  |

`--feather` overrides the sigma. Output filename appends `_fXX` so different sigma runs
are kept as separate files and never overwrite each other.

---

### How to add a new profile

Add a new entry to `DEPTH_PROFILES` in `03_depth_estimate.py`:

```python
"my_profile_name": {
    "mask_mode": "alpha_weight",   # or "binary"
    "feather_sigma": 15.0,         # 0.0 = no blur
    "description": "One line explaining what this does.",
    "added": "YYYY-MM-DD",
    "status": "experimental",      # or "stable" / "deprecated"
},
```

Then add a section to this file explaining why it exists.

Never delete or rename an existing profile — output filenames embed the profile name,
so deleting a profile makes old output files uninterpretable.

---

## ZoeDepth — Blocked

**Blocked:** 2026-05-29 | **Resolution:** `pipeline-02-zoedepth` planned

ZoeDepth was tested against `pipeline-01`'s venv (timm 1.0.27, torch 2.6.0+cu124).
Two separate failures occurred:

1. **Load failure** — `state_dict` contained unexpected `relative_position_index` keys.
   Patched with `strict=False` in the cached hub code. Model loads after this patch.

2. **Inference failure** — `'Block' object has no attribute 'drop_path'`.
   timm 1.0 removed `Block.drop_path` and replaced it with `drop_path1`/`drop_path2`.
   ZoeDepth's MiDaS DPT backbone calls `.drop_path` directly. Cannot be patched with
   a one-liner — would require modifying multiple files across the MiDaS backbone.

Downgrading timm to 0.9.x risks breaking `depth_anything_v2` and `transformers` which
depend on timm 1.0+ APIs. ZoeDepth gets its own environment: `pipeline-02-zoedepth/`
with a separate `requirements.txt` pinning `timm==0.9.16`.

---

## Paid Depth Tools Worth Evaluating

These are libraries, APIs, or standalone tools — not subscription pipeline apps.

| Tool                         | Type           | Cost               | Relevant For                                       |
| ---------------------------- | -------------- | ------------------ | -------------------------------------------------- |
| **Topaz Photo AI**           | Desktop app    | ~$200 one-time     | Pre-processing sharpness; not a depth estimator    |
| **3DF Zephyr**               | Photogrammetry | Free–$180/yr       | Multi-photo 3D reconstruction (not single-image)   |
| **RealityCapture**           | Photogrammetry | Pay-per-input      | Best-in-class multi-photo reconstruction           |
| **Stability AI Depth API**   | Cloud API      | Per-call pricing   | Worth comparing output quality                     |
| **NVIDIA Instant NeRF / 3DGS** | Research     | Free               | Multi-photo; requires 30–200 photos of subject     |

**Key insight:** No paid single-image depth tool clearly outperforms the free models for portrait
work as of 2026. The biggest quality jump is not from switching depth models — it is from using
**facial 3DMM reconstruction** (see below) to replace the depth model on the face region.

---

## Facial Depth Enhancement — Proposed Step 3.5

### The problem with monocular depth on faces

Depth Anything V2 infers depth from pixel appearance (shading, perspective, occlusion). A face
photographed with flat lighting produces a flat depth map regardless of model quality — the model
has no other information. The actual geometric protrusion of the nose (~20–25mm in a real face)
is only approximated.

**Facial 3DMM reconstruction solves this.** A 3D Morphable Model fits a statistical face model
to the 2D photo using landmark positions and appearance. The output is a geometrically accurate
face mesh based on known face anatomy, not pixel shading.

### Proposed pipeline

```
Stage 03: Depth Anything V2 → full scene depth map
         ↓
Stage 3.5: 3DMM reconstruction → anatomically accurate face depth
         ↓
         Blend: replace face region with 3DMM geometry
         Preserve: hair, neck, clothing from Depth Anything
         ↓
Stage 04: Mesh generation from blended depth
```

### 3DMM tool options

| Tool                    | Quality   | Speed      | Difficulty | Notes                                                                       |
| ----------------------- | --------- | ---------- | ---------- | --------------------------------------------------------------------------- |
| **3DDFA_V2**            | High      | Fast (~1s) | Low        | Best starting point. Single-image, 3D landmarks + mesh. `cleardusk/3DDFA_V2` |
| **DECA**                | Very high | Medium     | Medium     | Detailed expression + shape. `YadiraF/DECA`                                 |
| **MediaPipe Face Mesh** | Medium    | Very fast  | Very low   | 468 landmarks, no full 3D geometry — useful for blend masking               |
| **NextFace**            | High      | Slow       | High       | Physically-based face reconstruction                                        |

**Recommended starting point: 3DDFA_V2** — single-image, handles multiple faces, exports depth
map aligned to the original photo, pip installable.

### When to use Step 3.5

| Scenario                             | Use 3.5?            | Reason                                                                    |
| ------------------------------------ | ------------------- | ------------------------------------------------------------------------- |
| Portrait with flat frontal lighting  | Yes — high priority | Depth model will flatten the face; 3DMM gives accurate geometry           |
| Portrait with strong side lighting   | Optional            | Depth model likely captures good structure; 3DMM still improves it        |
| Two-person overlapping portrait      | Yes, carefully      | 3DDFA_V2 handles multiple faces; helps separate overlapping depth regions |
| Pet or object (non-human)            | No                  | 3DMM only applies to human faces                                          |
| Artistic / illustration input        | No                  | 3DMM requires realistic facial photos                                     |

### Face region blending strategy

1. Run 3DDFA_V2 or MediaPipe Face Mesh to get face bounding region
2. Create soft elliptical mask around the face (feathered ~50–80px at 3840×3840)
3. Inside mask: use 3DMM depth, scaled to match overall depth range
4. Outside mask: use Depth Anything depth
5. At feathered boundary: linear blend between the two

---

## Recommended Workflow Paths

### Path A — Current (implemented)
```
01 Upscale → 02 Remove BG → 03 Depth Anything V2 → 04 Mesh
```
Good for: testing, quick iterations, non-portrait subjects, well-lit portraits.

### Path B — Recommended next upgrade
```
01 Upscale → 02 Remove BG → 03 Depth Anything V2
                           → 03.5 3DDFA_V2 face reconstruction
                           → 03.5 blend depth maps
                           → 04 Mesh
```
Good for: portrait production, close-up face shots, flat-lit photos.

### Path C — Benchmark run
```
Run image through both Depth Anything V2 AND Apple Depth Pro
Compare _preview_depth.png side by side
Keep whichever shows better nose projection, eye socket depth, cleaner hair boundary
```

### Path D — Premium multi-photo (future)
```
10–30 photos of subject from multiple angles
→ RealityCapture or 3DF Zephyr photogrammetry
→ Clean OBJ mesh (no depth map needed)
→ Stage 05 Export directly
```
Most accurate 3D reconstruction possible from photos. Requires controlled multi-angle shoot —
not practical for single-photo customer submissions, but ideal for premium products.

---

## Pre/Post Run Checklist

**Before Stage 03:**

- [ ] Face fills at least 50% of the upscaled image
- [ ] Lighting shows visible shadow/highlight variation across the face
- [ ] Image is sharp at the nose bridge and eyes
- [ ] Background has been removed (alpha mask applied)
- [ ] Head rotation is under 45° from frontal

**After Stage 03 — inspect `_preview_depth.png`:**

- [ ] Nose tip is the brightest/warmest point
- [ ] Forehead dome is visible (bright at center, darker at edges)
- [ ] Eye sockets are slightly darker (recessed) than surrounding cheeks
- [ ] Chin area is darker than the nose (further from camera)
- [ ] Background is pure black (mask applied correctly)
- [ ] No flat grey bands or staircase artifacts in smooth areas
