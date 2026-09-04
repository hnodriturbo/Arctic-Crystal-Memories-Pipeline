<!--
File: .Markdown/models/EYEGLASSES/README.md
Purpose:
 - Record research and the planned geometry route for eyeglasses in portrait reconstruction.
-->

# Eyeglasses geometry research

## Current failure

HRN reconstructs the face surface and samples source appearance onto it. In the
`amma-2` portrait, the visible frame is therefore largely baked into the face
colour/relief instead of existing as independent eyeglasses geometry. FLAME,
SMPL-X, and ordinary morphable face models do not provide a subject-specific
eyeglasses mesh as part of their anatomical topology.

## Relevant dedicated research

The ECCV 2020 paper *Eyeglasses 3D shape reconstruction from a single face
image* explicitly separates eyeglasses from the face. Its method combines
glasses segmentation, glasses landmarks, head-relative pose, and planar and
symmetric frame priors. The associated public GitHub repository identifies
itself as the official implementation, but currently leaves dataset,
installation, and usage as `TODO`; it is not a runnable checkpoint for ACM yet.

A 2024 thin-frame reconstruction method uses a class-specific frame template,
42 keypoints, camera estimation, free-form deformation, differentiable
rendering, silhouette consistency, and symmetry constraints. This is a strong
architectural reference, but a complete public pretrained implementation has
not been confirmed.

References:

- <https://www.ecva.net/papers/eccv_2020/papers_ECCV/html/5056_ECCV_2020_paper.php>
- <https://github.com/wang-yating/EyeglassesReconstruction>
- <https://arxiv.org/abs/2408.05402>

## ACM implementation route

Eyeglasses become a separate `EYEGLASSES_FRAME` mesh layer:

1. define a glasses ROI from the detected face and eye landmarks;
2. segment dark frame strokes separately from skin, eyes, and glare;
3. trace left rim, right rim, bridge, and visible temples as ordered curves;
4. fit a symmetric front-frame template to those curves;
5. anchor the bridge and rims slightly in front of the HRN nose/eye surface;
6. bevel the curves into thin printable/visible tubes;
7. infer temple depth against the HRN head and ears;
8. represent lenses as optional separate shallow surfaces, or omit them for a
   laser-dot output when transparent lens geometry adds no useful engraving;
9. remove or suppress the baked frame relief from the skin ownership region;
10. export face and glasses as distinct named GLB layers.

## QA rule

The glasses layer is accepted only if the front projection matches the source,
the bridge floats in front of the nose rather than entering it, rims do not
become facial grooves, and temples terminate plausibly near the ears in both
30-degree and profile views. Missing hidden temple geometry must be marked as
template-inferred rather than source-observed.

