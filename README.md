# K9 Crystal Pipeline — Project Context & Vision

Version: 4.1
Status: Active
Repository: `K9-Crystal-Pipeline`
Purpose: Image prep pipeline and local operator UI for K9 crystal production workflows.

---

## Table of Contents

1. [Project Identity](#1-project-identity)
2. [Project Vision](#2-project-vision)
3. [Current Production Strategy](#3-current-production-strategy)
4. [What This Repo Is For](#4-what-this-repo-is-for)
5. [What This Repo Is Not For](#5-what-this-repo-is-not-for)
6. [Core Principles](#6-core-principles)
7. [Experimental Workflow Categories](#7-experimental-workflow-categories)
8. [Quality Standards](#8-quality-standards)
9. [Repository Structure](#9-repository-structure)
10. [`web/` — Next.js Operator Interface](#10-web--nextjs-operator-interface)
11. [`pipeline/` — Image Preparation Pipeline](#11-pipeline--image-preparation-pipeline)
12. [`pipeline-converter/` — File Conversion / Inspection](#12-pipeline-converter--file-conversion--inspection)
13. [End-to-End Operator Workflow](#13-end-to-end-operator-workflow)
14. [Vendor Role](#14-vendor-role)
15. [Customer File and Data Rules](#15-customer-file-and-data-rules)
16. [Development Rules](#16-development-rules)
17. [Web App Technical Rules](#17-web-app-technical-rules)
18. [Pipeline Technical Rules](#18-pipeline-technical-rules)
19. [Converter Technical Rules](#19-converter-technical-rules)
20. [Future Work](#20-future-work)
21. [Agent Behavior Rules](#21-agent-behavior-rules)

---

## 1. Project Identity

A local dev project built to automate and explore the image preparation steps for K9 optical crystal production. The same results (upscaling, background removal, enhancement) can be done in Photoshop — this repo exists to automate and explore those steps programmatically.

The product context: personalized K9 crystal keepsakes (portraits, pets, memorials, etc.) produced via subsurface laser engraving.

This repo is **not** the ecommerce store or the business research system. It is a local tool.

---

## 2. Project Vision

Build professional-grade workflows for creating high-quality K9 crystal engravings from photographs, artwork, logos, and 3D models.

The goal is to develop expertise in:

- Image preparation and background removal
- Depth reconstruction and point-cloud generation
- Mesh generation and refinement
- Relief generation and engraving preparation
- Production quality control

This project prioritizes craftsmanship, experimentation, and continuous improvement over automation.

Technology is a tool that assists the artist and technician — technology is not the artist.

The objective is not to discover one perfect workflow. The objective is to discover, test, compare, refine, document, and improve many workflows over time.

---

## 3. Current Production Strategy

```text
Customer image
  -> quality review
  -> convert to PNG if needed
  -> optional upscaling
  -> optional enhancement
  -> optional background removal
  -> operator review / approve or deny
  -> upload prepared image to vendor
  -> vendor creates production file
  -> finished K9 crystal product
```

Local focus is image intake, format conversion, upscaling, enhancement, background removal, and operator preview/approval. Vendor handles the professional 3D/laser production file creation.

---

## 4. What This Repo Is For

- Local image-preparation pipeline (Python)
- Next.js local operator interface (browser-based workflow)
- PNG conversion and preservation
- CAD/DXF inspection utilities
- Documenting technical decisions for agents

---

## 5. What This Repo Is Not For

- Full point-cloud or mesh generation from scratch
- Full SSLE printer-file generation
- Replacing vendor conversion tools
- The final customer-facing ecommerce website

Old research can remain as reference but must not drive current architecture.

---

## 6. Core Principles

**Technology assists the artist.** AI, reconstruction software, and automation tools assist the workflow. Human judgment remains responsible for final quality decisions.

**No single workflow assumption.** Different image types require different processing strategies. Every workflow should be evaluated on its own merits.

**Preserve maximum information.** Retain high-resolution intermediate files whenever practical. Always preserve original source files.

**Modern software first.** Prefer modern package versions and architectures. Do not downgrade software merely to force compatibility unless absolutely necessary.

**Quality before speed.** Quality takes priority over convenience, automation, and processing speed.

**Manual correction is expected.** Depth maps, point clouds, and meshes all require review. Human correction is a normal part of the workflow.

**Document everything.** Document successes, failures, experiments, discoveries, improvements, and comparisons. Build long-term project knowledge.

---

## 7. Experimental Workflow Categories

The project investigates and compares multiple approaches:

| Workflow | Steps |
| -------- | ----- |
| A | Prompt → AI Image → Depth Map → Point Cloud → Mesh → Engraving Export |
| B | Photograph → Background Removal → Depth Map → Point Cloud → Mesh → Engraving Export |
| C | Photograph → Human Segmentation → Depth Generation → Point Cloud → Mesh → Engraving Export |
| D | Photograph → Face Reconstruction → Relief Generation → Point Cloud → Engraving Export |
| E | Pet Photograph → Reconstruction → Relief Optimization → Engraving Export |
| F | Logo → Vector Cleanup → Point Generation → Engraving Export |
| G | Existing 3D Model → Optimization → Reduction → Engraving Export |

Additional workflows should be added whenever new ideas arise.

---

## 8. Quality Standards

Every workflow should be evaluated on:

- **Accuracy** — Does the output resemble the original subject?
- **Depth quality** — Does the depth appear believable?
- **Face quality** — Does the face preserve recognizable identity?
- **Relief quality** — Does the relief appear natural?
- **Print readiness** — Can the output be successfully prepared for engraving?
- **Visual quality** — Would a customer be satisfied with the final crystal?

---

## 9. Repository Structure

```text
K9-Crystal-Pipeline/
├── README.md                           # This file — root context
├── Arctic-Crystal-Memories.md          # Shared cross-repo company context
├── .gitignore
├── K9-Crystal-Pipeline.code-workspace
├── docs/                               # Old instructions, research, PDF helpers
│   ├── pipelines_md_helpers/           # Pipeline setup guides and templates
│   ├── INSTRUCTIONS-OLD.md
│   ├── INSTRUCTIONS-OLD-DETAILED.md
│   ├── texture-mesh-research.md
│   └── texture-mesh-guide.md
├── pipeline/                           # Active Python image-prep pipeline
├── pipeline-converter/                 # CAD/DXF + format conversion utilities
├── pipeline-old/                       # Legacy research pipelines (reference only)
│   ├── pipeline-01-depth-anything/
│   ├── pipeline-02-zoedepth/
│   ├── pipeline-03-pro/
│   ├── pipeline-stl-obj-xyz-dxf-old/
│   └── py_step_files/
└── web/                                # Next.js local operator interface
```

Folder docs:

```text
pipeline/          -> CLAUDE.md, pipeline-guide.md, pipeline-info.md, pipeline-setup.md
pipeline-converter/-> INSTRUCTIONS.md, README.md, pipeline-setup.md
web/               -> AGENTS.md, CLAUDE.md, PROJECT_CONTEXT.md
```

---

## 10. `web/` — Next.js Operator Interface

Local browser UI to run and review pipeline operations without using the terminal directly.

Current features:
- Browse and preview source/output images
- Trigger Python pipeline scripts via `POST /api/process`
- Stream live terminal output with Server-Sent Events
- Approve or deny results, auto-delete denied outputs
- Login-protected local access

### Stack

```text
Framework: Next.js 16 / App Router
React:     19
Styling:   Tailwind CSS 4
Auth:      NextAuth / Auth.js v5
Database:  PostgreSQL + Prisma 7
Language:  JavaScript-first
Bridge:    Node.js route handlers spawning Python scripts
Streaming: Server-Sent Events
```

### Key routes and structure

```text
web/
├── src/
│   ├── auth.js
│   ├── core/
│   │   ├── prisma.js
│   │   └── pgUrl.js
│   └── app/
│       ├── layout.js
│       ├── page.jsx                          # Dashboard / image browser
│       ├── globals.css
│       ├── login/page.jsx                    # Login UI
│       ├── process/page.jsx                  # Image operation page
│       ├── context/AppContext.jsx
│       ├── components/
│       │   ├── ClientShell.jsx
│       │   ├── ImageGrid.jsx
│       │   ├── ImageModal.jsx
│       │   ├── Navbar.jsx
│       │   ├── ProcessingPanel.jsx
│       │   ├── Sidebar.jsx
│       │   ├── Terminal.jsx
│       │   └── ThemeToggle.jsx
│       └── api/
│           ├── auth/[...nextauth]/route.js   # Auth.js v5 handler
│           ├── image/[...imgpath]/route.js   # Serves pipeline images
│           ├── images/route.js               # Lists pipeline images
│           ├── process/route.js              # Spawns Python scripts
│           └── run/route.js                  # Deletes denied outputs
├── prisma/
│   ├── schema.prisma
│   ├── seed.js
│   └── prisma.md
├── prisma.config.ts
├── middleware.js
├── next.config.mjs
├── AGENTS.md
├── CLAUDE.md
└── PROJECT_CONTEXT.md
```

---

## 11. `pipeline/` — Image Preparation Pipeline

Active Python image-prep backend.

| Operation | Script | Output folder |
| --------- | ------ | ------------- |
| Upscale | `code/upscale.py` | `output/upscaled/` |
| Enhance | `code/enhance.py` | `output/enhanced/` |
| Remove BG | `code/remove_bg.py` | `output/bg_removed/` |

Scripts are independent and can run in any order.

```text
pipeline/
├── code/
│   ├── upscale.py
│   ├── enhance.py
│   ├── remove_bg.py
│   ├── codeformer_arch.py
│   └── vqgan_arch.py
├── input/
├── output/         (upscaled/, enhanced/, bg_removed/, logs/)
├── models/         (realesrgan/, gfpgan/, codeformer/)
├── CLAUDE.md
├── pipeline-guide.md
├── pipeline-info.md
├── pipeline-setup.md
└── requirements.txt
```

Rules: preserve originals, never overwrite inputs, export PNG, preserve alpha, keep scripts callable from CLI and web app.

---

## 12. `pipeline-converter/` — File Conversion / Inspection

Two purposes:
1. Convert customer image formats to PNG before preparation.
2. Convert/inspect vendor-returned `.cad` / `.dxf` files into readable formats.

```text
pipeline-converter/
├── code/
│   ├── convert_cad.py
│   ├── convert_dxf.py
│   ├── inspect_file.py
│   └── utils/
│       ├── parsers.py
│       └── writers.py
├── docs/
│   └── format-notes.md
├── input/
├── output/
├── INSTRUCTIONS.md
├── README.md
├── pipeline-setup.md
└── requirements.txt
```

Keep lightweight unless merged with `pipeline/`.

---

## 13. End-to-End Operator Workflow

```text
1. Copy original customer image into input folder.
2. Convert to PNG if not already PNG.
3. Inspect image quality.
4. Upscale if useful.
5. Enhance if useful.
6. Remove background if useful.
7. Review output in web app.
8. Approve or deny.
9. Upload approved PNG to vendor.
10. Inspect returned files when needed.
```

Not every image needs every step.

---

## 14. Vendor Role

Vendor (e.g. Cockpit3D) handles the professional 2D/2.5D/3D conversion, point cloud generation, human artist correction, and production file creation. This repo prepares clean image inputs for that handoff. If vendor returns `.cad` / `.dxf` files, use converter tools to inspect them.

---

## 15. Customer File and Data Rules

- Never commit real customer images or personal data.
- Never commit API keys, passwords, or auth secrets.
- Preserve originals; use output folders for processed files.

Recommended `.gitignore`:

```text
pipeline/input/
pipeline/output/
pipeline/models/
pipeline-converter/input/
pipeline-converter/output/
web/.env*
*.psd *.tif *.tiff *.cad *.dxf *.stl *.ply *.obj *.xyz
```

---

## 16. Development Rules

- Work locally. Don't push or open PRs unless explicitly asked.
- Prefer minimal patches. Don't rewrite working code without reason.
- Inspect files before editing.
- Update folder-level docs when behavior changes.
- No emoji in code comments unless requested.

---

## 17. Web App Technical Rules

```text
Next.js:   15+ (project may use 16)
React:     19+
Routing:   App Router
Language:  JavaScript unless TypeScript is required
Styling:   Tailwind CSS 4
Auth:      NextAuth / Auth.js v5 (not v4)
Database:  Prisma 7 + PostgreSQL
Rendering: Server components by default; client only when needed
Imports:   @/ absolute imports when configured
```

- Keep Python spawning isolated in route handlers.
- Validate file paths — do not expose arbitrary filesystem access.
- Do not use legacy API routes.

---

## 18. Pipeline Technical Rules

```text
Python:    3.11 (3.12+ breaks basicsr/RealESRGAN/GFPGAN)
GPU:       RTX 3060 Laptop GPU — CUDA required
PyTorch:   CUDA build — install before requirements.txt
Tools:     RealESRGAN, GFPGAN, rembg, Pillow, OpenCV
```

- Do not silently fall back to CPU for AI operations.
- Preserve PNG alpha after background removal.
- Output naming: `<stem>_upscaled.png`, `<stem>_enhanced.png`, `<stem>_bg_removed.png`

---

## 19. Converter Technical Rules

- Keep dependencies lightweight while separate from `pipeline/`.
- Do not add AI/CUDA deps to `pipeline-converter/` unless merge plan changes.
- Prefer inspectable outputs: `.xyz`, `.ply`, `.obj`, `.stl`, reports.
- Preserve max quality when converting to PNG. Never destroy source files.

---

## 20. Future Work

- Image-format-to-PNG conversion in web UI.
- Decide `pipeline-converter/` merge.
- Converter UI routes in web app.
- Workflow history / `ProcessRun` records.
- Approved output folder / status tracking.
- Returned-file inspection workflow (CAD/DXF/XYZ/PLY).

Implement incrementally — one focused change at a time.

---

## 21. Agent Behavior Rules

1. Read this file first.
2. Read folder-level docs for the area being edited.
3. Inspect files before editing.
4. Make minimal, targeted changes.
5. Do not revive local point-cloud/mesh generation as the main workflow.
6. Keep `web/`, `pipeline/`, and `pipeline-converter/` aligned.
7. Update docs when architecture or behavior changes.
