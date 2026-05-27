# K9 Crystal Pipeline

> **Version:** 1.0 &nbsp;|&nbsp; **Status:** Active

Professional-grade workflows for creating high-quality K9 crystal engravings from photographs, artwork, logos, and 3D models.

---

## Table of Contents

- [Project Vision](#project-vision)
- [Long-Term Goals](#long-term-goals)
- [Core Principles](#core-principles)
- [Workflow Overview](#workflow-overview)
- [Quality Standards](#quality-standards)
- [Software Guidelines](#software-guidelines)
- [Data Preservation](#data-preservation)
- [Crystal Product Categories](#crystal-product-categories)
- [Business Goals](#business-goals)

---

## Project Vision

This project builds expertise in every stage of the crystal engraving process:

| Stage | Description |
|---|---|
| Image Preparation | Sourcing and preparing input images |
| Background Removal | Isolating subjects from backgrounds |
| Depth Reconstruction | Generating believable depth information |
| Point Cloud & Mesh | Building and refining 3D representations |
| Relief Generation | Creating engravable relief surfaces |
| Production QC | Final quality control before engraving |

The objective is **not** to find one perfect workflow — it is to discover, test, compare, refine, and document **many** workflows over time.

Technology assists the artist. Human judgment makes the final quality decision.

---

## Long-Term Goals

- Develop knowledge to produce professional crystal products for tourists, families, couples, weddings, graduations, pets, memorials, corporate gifts, awards, trophies, and custom artwork.
- Create products that can compete with or exceed international crystal engraving standards.
- Become one of Iceland's leading providers of custom crystal engraving.

---

## Core Principles

| Principle | Summary |
|---|---|
| **Technology Assists** | AI and automation support the workflow; humans own quality decisions |
| **No Single Workflow** | Different subjects require different strategies |
| **Preserve Information** | Retain high-resolution intermediates; never overwrite originals |
| **Modern Software First** | Prefer modern versions; avoid unnecessary downgrades |
| **Quality Before Speed** | Quality takes priority over speed, automation, and convenience |
| **Manual Correction Expected** | Depth maps, point clouds, and meshes all require human review |
| **Document Everything** | Record successes, failures, experiments, and comparisons |

---

## Workflow Overview

Several workflow paths are actively researched and compared:

| Workflow | Input → Output |
|---|---|
| **A** | Prompt → AI Image → Depth Map → Point Cloud → Mesh → Export |
| **B** | Photograph → Background Removal → Depth Map → Point Cloud → Mesh → Export |
| **C** | Photograph → Human Segmentation → Depth → Point Cloud → Mesh → Export |
| **D** | Photograph → Face Reconstruction → Relief → Point Cloud → Export |
| **E** | Pet Photograph → Reconstruction → Relief Optimization → Export |
| **F** | Logo → Vector Cleanup → Point Generation → Export |
| **G** | Existing 3D Model → Optimization → Reduction → Export |

New workflow ideas should be added whenever they arise.

Each documented workflow should include: purpose, inputs, outputs, required software, advantages, disadvantages, recommended use cases, quality rating, and known issues.

---

## Quality Standards

Every workflow output is evaluated against:

- **Accuracy** — Does the output resemble the original subject?
- **Depth Quality** — Does the depth appear believable?
- **Face Quality** — Does the face preserve recognizable identity?
- **Relief Quality** — Does the relief appear natural?
- **Print Readiness** — Can the output be prepared for engraving?
- **Visual Quality** — Would a customer be satisfied with the final crystal?

---

## Software Guidelines

Research and evaluate tools across all categories without vendor lock-in:

- Image generators
- Background removal & segmentation tools
- Depth estimation models
- Human & pet reconstruction tools
- Point cloud & mesh editing software
- Crystal preparation software

When testing any tool, record: name, version, workflow used, strengths, weaknesses, quality score, and example outputs.

---

## Data Preservation

All project data is organized to prevent loss and support comparison:

```
project/
├── source_images/
├── depth_maps/
├── point_clouds/
├── meshes/
└── exports/
```

- Never overwrite original source files.
- Preserve intermediate stages whenever practical.
- Keep separate folders for each processing stage.

---

## Crystal Product Categories

| Category | Examples |
|---|---|
| **Standard Shapes** | Cubes, Rectangles, Hearts, Diamonds |
| **Awards & Trophies** | Awards, Trophies, Corporate Gifts |
| **Keepsakes** | Keychains, Ornaments, Memorial Crystals |
| **Custom** | Personalized shapes, Custom artwork |

---

## Business Goals

- Deliver premium-quality products focused on customer satisfaction.
- Build a reputation for quality craftsmanship.
- Develop repeatable production workflows before scaling.
- Build deep expertise first; automate later.

---

> This repository is guided by `INSTRUCTIONS.md`, which serves as the primary source of truth for project goals, rules, workflow philosophy, quality standards, research direction, and long-term decisions.
