<!--
File: converter/2.5D-pipeline/benchmarks/amma-og-afi-current-best.md
Purpose:
 - Record the reproducible current-best geometry baseline for the amma-og-afi tester.
-->

# Amma og afi — current best baseline

## Winner

- Engine: MoGe-2
- Checkpoint: `Ruicheng/moge-2-vitl-normal`
- Hugging Face revision: `b135031bae30b5ac2ae141a0e68717795ce38340`
- Local checkpoint SHA-256: `280741fd09bc3f403ccff9967784c2a391b52d2c0742ae3efdb21d9f90cc1a01`
- MoGe-2 runtime commit: `07444410f1e33f402353b99d6ccd26bd31e469e8`
- Inference detail: `9/9`
- Production/final-quality default: `9/9`
- Preview detail: `5/9`
- Precision/device: FP16 autocast, NVIDIA RTX 3060 Laptop GPU 6 GB
- Scene mode: full scene, `apply_mask=False`
- Source: `input-testers/amma-og-afi/cockpit-embedded-texture.jpg`
- Final-quality elapsed time: 24.56 seconds, including model load and file writes

## Outputs

- Depth: `output/model-tests/amma-og-afi/moge-2-vitl-level9-full-scene/depth.png`
- Normal: `output/model-tests/amma-og-afi/moge-2-vitl-level9-full-scene/aux/normal.png`
- Validity mask: `output/model-tests/amma-og-afi/moge-2-vitl-level9-full-scene/aux/mask.png`
- Metadata: `output/model-tests/amma-og-afi/moge-2-vitl-level9-full-scene/depth.json`

## Why it currently wins

The metric depth preserves the large scene ordering: people in front, sofa behind.
The RGB-encoded normal map preserves substantially more facial, neck, hand, clothing,
and sofa-seam shape than the grayscale depth map alone. Compared with ViT-L level
5/9, level 9/9 increased measured high-frequency facial geometry by approximately
13–17% on this tester. It also increased flat-sofa variation by approximately 20%,
so final fusion must apply normal detail selectively rather than displacing every
surface equally.

## Implemented use

1. Use metric depth for macro scene placement and occlusion.
2. Detect every human face and re-run ViT-L 9/9 on enlarged crops before meshing.
3. Integrate the normal map into bounded, edge-aware surface displacement with
   `detail_refine.py`; default normalized strength is `0.018`.
4. Protect silhouette discontinuities from normal-integration ringing.
5. Scale the relief envelope in millimetres (initial rule: depth about 10% of the
   displayed image span, constrained by the crystal blank).
6. Use Blender for geometry comparison, inspection and difficult local repairs.

## 2026-08-30 face and detail validation

- Tester: `input/test-cutout.png`, two faces declared and detected.
- Global geometry: MoGe-2 ViT-L `9/9` on CUDA.
- Face baseline: two enlarged MoGe face crops, affine depth alignment and soft fusion.
- Surface detail: Fourier integration of MoGe normals, `1.2..24 px` frequency band.
- Detail correction at a 16 mm relief envelope:
  - mean absolute correction: approximately `0.0505 mm`;
  - maximum capped correction: `0.288 mm`.
- All three meshes use identical topology: `221,334` vertices and `439,854` triangles.
- Geometry tests verify normal integration and broad-tilt rejection.

The face-crop stage is a working baseline, not the final identity/head solution.
The next head-shape candidates are evaluated as complementary inputs:

1. GNM Head as the modern commercial-safe parametric head template; it still
   needs a photo-fitting/perception layer.
2. HRN as a Linux/CUDA research challenger for exported high-frequency face
   geometry.
3. DAD-3DHeads for stable full-head/pose geometry, with a non-commercial license.
4. KeenTools FaceBuilder as the human-supervised identity correction and QA path.

FaceLift is not the first fusion candidate because its output is 3D Gaussian
splats rather than a directly usable watertight/height-field mesh.
