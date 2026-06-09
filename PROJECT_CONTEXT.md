# K9 Crystal Pipeline — Code Agents Reference

> Any AI coding agent can read this file to immediately understand the project,
> its structure, what works, what is not yet connected, and the rules for contributing.

---

## Project Identity

- **Repository name:** `K9-Crystal-Pipeline`
- **Business name:** Crystal Clear Memories
- **Owner:** Hreidar Petursson (Iceland)
- **Purpose:** Local operator tooling for preparing customer images before Cockpit3D crystal engraving production, plus a converter utility for reading Cockpit3D-exported point-cloud files.

The company sells personalized K9 optical crystal keepsakes (subsurface laser engraving) for tourists, Icelandic families, weddings, pets, memorials, and corporate clients.

---

## Production Strategy

```
Customer image
  → local quality review
  → optional upscaling (RealESRGAN / GFPGAN)
  → optional background removal (rembg)
  → optional enhancement (GFPGAN face / brightness-contrast)
  → upload prepared image into Cockpit3D workspace
  → Cockpit3D 3D conversion, point cloud, mesh, preview
  → printer handoff → finished K9 crystal product
```

**The local pipeline ends at the prepared image.** Cockpit3D handles all 3D conversion. Do not rebuild Cockpit3D features locally.

---

## Folder Structure

### Project Root

```
K9-Crystal-Pipeline/
├── code-agents.md          ← this file
├── INSTRUCTIONS.md         ← legacy root instructions (backup; superseded by this file)
├── .gitignore
├── pipeline/               ← active image-preparation pipeline (Python)
├── pipeline-converter/     ← Cockpit3D CAD/DXF point-cloud converter (Python, NOT yet in web UI)
├── web/                    ← Next.js operator web interface
├── Markdown_Helpers/       ← old notes and research docs
└── pipeline-03-pro/        ← legacy pipeline (reference only)
```

---

### pipeline/ — Image Preparation Pipeline

```
pipeline/
├── CLAUDE.md
├── pipeline-guide.md
├── pipeline-info.md
├── pipeline-setup.md
├── requirements.txt
├── .venv/                  (excluded from git)
├── models/                 (excluded from git — large model weights)
├── input/                  (excluded from git — source images)
├── output/                 (excluded from git — generated outputs)
│   ├── upscaled/
│   ├── enhanced/
│   ├── bg_removed/
│   └── logs/
└── code/
    ├── upscale.py          ← RealESRGAN / GFPGAN upscaling (CUDA required)
    ├── enhance.py          ← GFPGAN face enhance + brightness/contrast/sharpness/color
    ├── remove_bg.py        ← rembg background removal (CUDA required)
    ├── codeformer_arch.py  ← CodeFormer architecture (used by enhance)
    └── vqgan_arch.py       ← VQGAN architecture (used by enhance)
```

**Hardware:** RTX 3060 Laptop GPU. All scripts MUST use CUDA. Never add CPU fallback.

**Scripts are invoked by the web app via `POST /api/process`.** The `PIPELINE_ROOT` env var points the web app at this folder.

---

### pipeline-converter/ — Cockpit3D CAD/DXF Converter

```
pipeline-converter/
├── INSTRUCTIONS.md
├── README.md
├── pipeline-setup.md
├── requirements.txt
├── .venv/                  (excluded from git)
├── input/
│   ├── cad/                ← drop .cad files here
│   └── dxf/                ← drop .dxf files here
├── output/
│   ├── xyz/                ← simplest point-cloud output
│   ├── ply/                ← recommended for CloudCompare
│   ├── obj/                ← vertices-only OBJ
│   └── reports/            ← inspection logs
└── code/
    ├── convert_cad.py      ← converts Cockpit3D .cad → xyz/ply/obj
    ├── convert_dxf.py      ← converts .dxf → xyz/ply/obj
    ├── inspect_file.py     ← inspects raw file structure / coordinate rows
    └── utils/
        ├── parsers.py      ← coordinate row extraction
        └── writers.py      ← xyz / ply / obj output writers
```

**Status: NOT yet integrated into the web UI.** This is a standalone CLI utility only.
Do NOT add PyTorch, RealESRGAN, GFPGAN, or any AI/CUDA deps here — it must stay lightweight.

---

### web/ — Next.js Operator Interface

```
web/
├── CLAUDE.md / AGENTS.md   ← IMPORTANT: read before writing Next.js code
├── INSTRUCTIONS.md
├── next.config.mjs
├── middleware.js            ← route auth guard (NextAuth v5)
├── prisma.config.ts         ← Prisma 7 datasource config
├── .env / .env.local        ← PIPELINE_ROOT, DATABASE_URL, NEXTAUTH_SECRET, etc.
├── prisma/
│   ├── schema.prisma        ← User + ProcessRun models (PostgreSQL)
│   └── seed.js              ← seeds initial admin user
├── src/
│   ├── auth.js              ← NextAuth v5 config (Credentials + bcrypt + Prisma)
│   └── app/
│       ├── layout.js        ← root layout
│       ├── page.jsx         ← home / image selection (ImageGrid)
│       ├── globals.css
│       ├── login/
│       │   └── page.jsx     ← login form
│       ├── process/
│       │   └── page.jsx     ← main operator page: preview → run → approve/deny
│       ├── api/
│       │   ├── auth/[...nextauth]/route.js  ← NextAuth v5 handler
│       │   ├── image/[...imgpath]/route.js  ← serves pipeline output images
│       │   ├── images/route.js              ← lists images in a pipeline folder
│       │   ├── process/route.js             ← spawns pipeline Python script (SSE stream)
│       │   └── run/route.js                 ← DELETE: removes a denied output file
│       ├── components/
│       │   ├── Navbar.jsx          ← top bar with theme toggle + sign-out
│       │   ├── Sidebar.jsx         ← folder/file browser sidebar
│       │   ├── ImageGrid.jsx       ← grid of images in selected folder
│       │   ├── ProcessingPanel.jsx ← operation selector (Upscale / Enhance / Remove BG)
│       │   ├── Terminal.jsx        ← live SSE log output during pipeline run
│       │   ├── ThemeToggle.jsx     ← light/dark toggle
│       │   ├── ImageModal.jsx      ← full-size image lightbox
│       │   └── ClientShell.jsx     ← client wrapper for AppProvider
│       └── context/
│           └── AppContext.jsx      ← global theme + modal state
│   └── core/
│       ├── prisma.js        ← singleton PrismaClient
│       └── pgUrl.js         ← constructs DATABASE_URL from env
```

---

## Web App — Chapter Reference

### Session and NextAuth v5

- NextAuth **v5** (not v4). API and file conventions differ from training data — check `node_modules/next/dist/docs/` if unsure.
- Config lives in `src/auth.js` — exports `{ handlers, signIn, signOut, auth }`.
- Strategy: JWT sessions, Credentials provider, bcrypt password check against PostgreSQL via Prisma.
- Route handler: `src/app/api/auth/[...nextauth]/route.js`.
- `middleware.js` at web root protects all routes except `/login` and `/api/auth/**`.
- Session user has `id`, `name`, `email`, `role` fields (role stored in JWT).

### Database — Prisma 7 + PostgreSQL

- **Prisma 7**: datasource URL is in `prisma.config.ts`, NOT in `schema.prisma`.
- Schema models: `User` (username/email/password/role) and `ProcessRun` (image/operation/engine/status/outputPath/approved).
- Singleton client at `src/core/prisma.js`.
- Seed: `prisma/seed.js` creates initial admin user.

### Routes

| Path                             | Purpose                                                           |
| -------------------------------- | ----------------------------------------------------------------- |
| `/`                              | Home — shows ImageGrid for browsing pipeline input/output folders |
| `/login`                         | Login form (Credentials)                                          |
| `/process?file=X&folder=Y`       | Main operator page — preview, run operation, approve/deny         |
| `GET /api/images?folder=X`       | Lists image files in a pipeline folder                            |
| `GET /api/image/{folder}/{file}` | Serves a pipeline image file                                      |
| `POST /api/process`              | Spawns pipeline Python script, streams stdout/stderr as SSE       |
| `DELETE /api/run`                | Deletes a denied output file                                      |
| `/api/auth/[...nextauth]`        | NextAuth handler                                                  |

### Added Packages

Key packages beyond Next.js defaults:

- `next-auth@5` — authentication
- `@prisma/client` + `prisma` — PostgreSQL ORM (Prisma 7)
- `bcryptjs` — password hashing
- `pg` — underlying PostgreSQL driver

### Components

| Component         | Role                                                        |
| ----------------- | ----------------------------------------------------------- |
| `Navbar`          | Top bar — logo, theme toggle, sign-out button               |
| `Sidebar`         | Folder browser — lists input/output subfolders              |
| `ImageGrid`       | Thumbnail grid for a folder; click → navigate to `/process` |
| `ProcessingPanel` | Tab UI — Upscale / Enhance / Remove BG with per-op options  |
| `Terminal`        | Live log: renders SSE lines from `/api/process` stream      |
| `ThemeToggle`     | Light/dark switch stored in AppContext                      |
| `ImageModal`      | Lightbox overlay for full-size image view                   |
| `ClientShell`     | Client boundary wrapping AppProvider in layout              |

### Modal

`ImageModal` is opened via `openModal({ name, folder, relativePath })` from `AppContext`. It fetches the image from `/api/image/{folder}/{filename}` and renders it full-size with a close button.

### Core Parts — process/page.jsx

The main operator workflow page:

1. Reads `?file` and `?folder` from search params.
2. Shows the source image (left) via `/api/image/{folder}/{file}`.
3. `ProcessingPanel` lets operator pick operation + options and fires `handleRun`.
4. `handleRun` POSTs to `/api/process` and streams SSE lines into `Terminal`.
5. On `done` event with `code === 0`: sets `outputFile` + `outputTs` state, shows output image + approval row.
6. Approve: marks approved, hides approval row.
7. Deny: calls `DELETE /api/run` to delete the output file.

**Important:** `outputTs` is a state variable set once when `outputFile` is set (via `setOutputTs(Date.now())` inside the async handler). The image `src` uses `?t=${outputTs}` — never `Date.now()` directly in JSX (impure function / React rules violation).

---

## pipeline/ — Stage Reference

All scripts live in `pipeline/code/` and are invoked by the web app via `POST /api/process`.

| Script         | Operation key | What it does                                                                                                             |
| -------------- | ------------- | ------------------------------------------------------------------------------------------------------------------------ |
| `upscale.py`   | `upscale`     | RealESRGAN or RealESRGAN-Face upscaling. Outputs to `output/upscaled/`. CUDA required.                                   |
| `enhance.py`   | `enhance`     | GFPGAN face enhancement + brightness/contrast/sharpness/color adjustments. Outputs to `output/enhanced/`. CUDA required. |
| `remove_bg.py` | `remove_bg`   | rembg background removal. Outputs to `output/bg_removed/` with alpha channel preserved. CUDA required.                   |

Output file naming: `{original_stem}_{upscaled|enhanced|bg_removed}.png`

---

## pipeline-converter/ — Stage Reference (CLI only, not yet in web)

| Script             | What it does                                                                            |
| ------------------ | --------------------------------------------------------------------------------------- |
| `inspect_file.py`  | Reads a raw `.cad` or `.dxf` file and reports structure, coordinate row samples         |
| `convert_cad.py`   | Extracts coordinate rows from Cockpit3D `.cad` files → exports `.xyz` / `.ply` / `.obj` |
| `convert_dxf.py`   | Parses `.dxf` files → exports point clouds                                              |
| `utils/parsers.py` | Regex-based coordinate row extraction shared across converters                          |
| `utils/writers.py` | XYZ, PLY, OBJ file writers                                                              |

**Next integration step:** expose `pipeline-converter` scripts through the web app (new `/api/convert` route + a Converter tab in the UI) so operators can run CAD/DXF conversion from the browser. This has not been built yet.

---

## Business Goal (SSLE / Crystal Pipeline Direction)

```
PHASE 1 — Image Preparation   (local pipeline — DONE)
PHASE 2 — 3D Conversion       (Cockpit3D — external tool)
PHASE 3 — Crystal Output      (printer handoff via Cockpit3D)
```

Future research goal (lower priority):
```
Image → Depth Map → Textured Point Cloud → SSLE Optimization → Laser Output
```

---

## Development Rules

- **JavaScript only** in `web/` (not TypeScript) unless explicitly changed.
- **CUDA always** in `pipeline/`. RTX 3060 Laptop GPU. No CPU fallback.
- `pipeline-converter/` must stay **lightweight** — no PyTorch, no CUDA, no AI models.
- Do not push to GitHub unless the user explicitly says to push.
- Do not overwrite original customer images.
- Env secrets (`NEXTAUTH_SECRET`, `DATABASE_URL`, passwords) never in code.
- Read `web/AGENTS.md` before writing Next.js code — v5 breaking changes apply.
