# Depth Estimation — Processing Decisions Log

Every named profile in `DEPTH_PROFILES` has an entry here explaining what it does,
why it was added, and when. Old profiles are never deleted — they stay in the code
and in this log so any past run can be reproduced exactly.

To use a profile:
```
python 03_depth_estimate.py --profile soft_edges_feathered
```
Or set `DEPTH_PROFILE=soft_edges_feathered` in `.env` to make it the default.

---

## Profile: `standard`
**Added:** 2026-05-28  
**Status:** Stable (default)

### What it does
Binary hard cut. Any pixel where alpha = 0 (background) is set to depth 0.
Subject pixels (alpha > 0) keep their raw model depth unchanged.

### Why it was added
This is the simplest correct behaviour — it prevents background ghost geometry
from entering the mesh. Added on initial implementation.

### Known limitation
Creates a hard geometric cliff at the subject boundary. If the mask from step 02
is binary (no soft transitions at hair/edge), this cliff shows up in the mesh as
a sharp wall around the subject. On a perfect soft mask it is less visible, but
still present because the model's own depth near silhouette edges tends to be
noisy/abrupt.

---

## Profile: `soft_edges_v1`
**Added:** 2026-05-29  
**Status:** Experimental

### What it does
Uses the actual alpha channel value as a linear multiplier on depth.
A pixel with alpha=128 (50% transparent) gets 50% of its raw depth value.
Fully transparent pixels (alpha=0) still reach 0. Fully opaque (alpha=255)
are unaffected.

### Why it was added
The step 02 mask often has semi-transparent pixels at hair and edge boundaries.
The `standard` profile ignores this information — any alpha > 0 passes through
unchanged. This profile uses that information to create a natural depth fade at
the silhouette, which produces a smoother mesh boundary without manual Photoshop
correction.

### Limitation
Only helps if the input mask actually has soft (semi-transparent) edges.
On a binary mask (common when alpha matting fails), this profile behaves
identically to `standard` because all alpha values are either 0 or 255.
Use `soft_edges_feathered` for binary masks.

---

## Profile: `soft_edges_feathered`
**Added:** 2026-05-29  
**Status:** Experimental

### What it does
Combines both fixes:
1. Alpha value used as linear weight (same as `soft_edges_v1`)
2. Gaussian blur applied to the alpha weight before multiplication

The Gaussian blur (`sigma=10.0px` at 3840px resolution) widens the transition
zone at the silhouette boundary. Even a fully binary mask (0 or 255 only) gets
a smooth ramp after blurring. The depth near edges fades gradually to 0 rather
than dropping off a cliff.

### Why it was added
The step 02 alpha matting Cholesky step failed on the first production image,
producing a binary mask. This profile was designed to recover acceptable edge
quality from a binary mask without requiring a manual Photoshop correction.
It also makes soft masks even smoother.

### Tuning
`feather_sigma` in the profile dict controls the blur width. At 3840×3840:
- `sigma=5`  → narrow fade (~10–15px)
- `sigma=10` → moderate fade (~20–30px) — starting point
- `sigma=20` → wide fade, may eat into thin features (hair strands, ears)

To experiment with sigma without creating a new profile, add a custom profile
entry to `DEPTH_PROFILES` in the script — the dict is designed to be extended.

---

---

## ZoeDepth — Isolated Pipeline Environment
**Blocked:** 2026-05-29  
**Resolution:** `pipeline-02-zoedepth` created on 2026-05-30

### What happened
ZoeDepth was tested against `pipeline-01`'s venv (timm 1.0.27, torch 2.6.0+cu124).
Two separate failures occurred:

1. **Load failure** — `state_dict` contained unexpected `relative_position_index` keys.
   Patched with `strict=False` in `~/.cache/torch/hub/isl-org_ZoeDepth_main/zoedepth/models/model_io.py`.
   Model loads after this patch.

2. **Inference failure** — `'Block' object has no attribute 'drop_path'`.
   timm 1.0 removed `Block.drop_path` and replaced it with `drop_path1`/`drop_path2`.
   ZoeDepth's MiDaS DPT backbone calls `.drop_path` directly during the forward pass.
   This cannot be patched with a one-liner — it would require modifying multiple files
   in the cached hub code across the MiDaS backbone.

### Why not downgrade timm
Downgrading timm to 0.9.x in `pipeline-01` risks breaking `depth_anything_v2` and
`transformers` which depend on timm 1.0+ APIs. Not worth the risk for this env.

### Current plan
ZoeDepth now has its own isolated environment: `pipeline-02-zoedepth/` with a separate
`requirements.txt` pinning `timm==0.9.16` and `torch 2.x`. This keeps `pipeline-01`
clean and lets ZoeDepth run correctly. The two depth outputs can then be compared
side-by-side before choosing which depth map to pass to stage 04.

---

## How to add a new profile

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

Never delete or rename an existing profile — output filenames embed the profile
name, so deleting a profile makes old output files uninterpretable.
