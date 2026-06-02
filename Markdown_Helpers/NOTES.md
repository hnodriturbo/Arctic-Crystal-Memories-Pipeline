# Highest Priority Research Question

- [ ] Learn how to generate point clouds containing both geometry and texture information suitable for SSLE crystal engraving.

---

# Pipeline Direction Change

## Previous Goal

Image → Depth Map → Point Cloud → Mesh

## Suggested New Goal (before)

The final deliverable for SSLE may not simply be:

- Mesh
- Point cloud
- Geometry

The final deliverable may instead be:

- Geometry
- Texture information
- Density information
- Point intensity information
- Laser-ready point cloud information

---

## New Goal

Image → Depth Map → Geometry → Texture Preservation → Textured Point Cloud → SSLE Optimization → Laser Output

## That Goal Becomes In Details This GOAL:

```text
PHASE 1 - Image Preparation
---------------------------
Image Acquisition
Image Quality Inspection
AI Upscaling
Image Enhancement
Automatic Background Removal
Manual Background Cleanup

PHASE 2 - Geometry Creation
---------------------------
Depth Estimation
Initial Point Cloud Generation
Texture Projection

PHASE 3 - Human Reconstruction
------------------------------
Human Reconstruction

PHASE 4 - 3D Asset Creation
---------------------------
Textured Point Cloud
Mesh Generation
Textured Mesh

PHASE 5 - Artist Stage
----------------------
Artist Correction Stage
Topology Cleanup

PHASE 6 - SSLE Preparation
--------------------------
SSLE Optimization
Point Density Optimization
Laser Preview

PHASE 7 - Manufacturing
-----------------------
Crystal Output
```

---

# Critical Discovery

## Existing Pipeline Problem

The current Python research pipelines primarily focus on:

- Depth estimation
- Geometry extraction
- Point cloud generation
- Mesh generation

The current research direction assumes that geometry alone is the primary objective.

---

