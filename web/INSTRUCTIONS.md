# K9 Crystal Pipeline — Web Frontend Spec

> **Purpose:** This file is the shared contract between the developer and Claude Code for the `web/` Next.js application. It describes what has been built, what is planned, and how the frontend connects to the Python pipeline backend.

---

## What This App Is

A local operator UI for the K9 Crystal Pipeline. It wraps the Python CLI scripts in `pipeline-01/` so that:

- You can browse and upload source photos without touching the filesystem
- You can trigger each pipeline stage from a button, with live log output streaming to the browser
- You can review output images and decide "use this in the next step" or "recreate"
- You never need to type a terminal command to process a photo

This is a **single-user local dev tool**, not a hosted web app. It runs via `npm run dev` on `localhost:3000`.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | Next.js 16 (App Router) |
| UI | React 19, Tailwind CSS 4 |
| Backend | Next.js Route Handlers (Node.js) |
| Python bridge | `child_process.spawn()` in Route Handlers |
| Streaming | Server-Sent Events (SSE) for live log output |
| State | React `useState` / `useReducer` — no external state lib |

---

## How Python Gets Triggered

Next.js Route Handlers in `src/app/api/` use Node.js `child_process.spawn()` to run Python scripts:

```
Browser button click
  → POST /api/run-stage  { pipeline, stage, args }
  → Node.js spawns: python 01_upscale.py --file X --run my_session
  → stdout/stderr lines streamed back as SSE
  → Browser LogStream component renders each line live
  → On exit code 0: OutputViewer fetches the result images
```

The Python scripts are called with their existing CLI interface. No Python server, no FastAPI, no message queue. One spawn per button press.

---

## Directory Layout

```
web/
├── src/
│   ├── app/
│   │   ├── page.js                  ← Landing page (orchestrator)
│   │   ├── layout.js                ← Root layout (TopNav lives here)
│   │   ├── globals.css
│   │   ├── api/
│   │   │   ├── pipelines/route.js   ← GET: list available pipelines
│   │   │   ├── files/route.js       ← GET: list files in a dir
│   │   │   ├── upload/route.js      ← POST: save file to input/
│   │   │   ├── run-stage/route.js   ← POST: spawn Python, stream SSE
│   │   │   ├── delete-run/route.js  ← DELETE: remove output run folder
│   │   │   └── output-image/route.js← GET: serve output image as binary
│   │   └── components/
│   │       ├── TopNav.jsx           ← Title bar + pipeline selector
│   │       ├── InputBrowser.jsx     ← Source input + mid-pipeline file browser
│   │       ├── StagePanel.jsx       ← Per-stage controls + Run button
│   │       ├── OutputViewer.jsx     ← Image canvas + Use/Recreate actions
│   │       └── LogStream.jsx        ← Live stdout display via SSE
├── INSTRUCTIONS.md                  ← This file
├── AGENTS.md
└── package.json
```

---

## API Routes

| Route | Method | Query / Body | Returns |
|-------|--------|-------------|---------|
| `/api/pipelines` | GET | — | `{ pipelines: ["pipeline-01"] }` |
| `/api/files` | GET | `?pipeline=pipeline-01&dir=input` | `{ files: [{name, size, mtime}] }` |
| `/api/upload` | POST | `FormData` with `file`, `pipeline` | `{ saved: "filename.jpg" }` |
| `/api/run-stage` | POST | `{ pipeline, stage, args }` | SSE stream of stdout lines |
| `/api/delete-run` | DELETE | `{ pipeline, stage, run }` | `{ deleted: true }` |
| `/api/output-image` | GET | `?pipeline=pipeline-01&path=output/upscaled/my_run/img.png` | image binary |

---

## Page Layout (Phase 1)

```
┌──────────────────────────────────────────────────────────────┐
│  K9 Crystal Pipeline                       [Pipeline: ▼]     │  TopNav
├──────────────────┬───────────────────────────────────────────┤
│  SOURCE INPUT    │  STAGE PANELS (accordion)                 │
│  [input/ files]  │                                           │
│  □ image_01.jpg  │  ▼ Stage 01 — Upscale                     │
│  [+ Upload]      │    Model ▼  Factor ▼  Tile  Run name      │
│                  │    [▶ Run Stage 01]                        │
│  MID-PIPELINE    │                                           │
│  upscaled/       │  ▼ Stage 02 — Remove BG                   │
│  □ my_run/…      │    Model ▼  From run ▼                    │
│  bg_removed/     │    [▶ Run Stage 02]                        │
│  □ my_run/…      │                                           │
│  depth_maps/     │  ▼ Stage 03 — Depth Estimation            │
│  □ my_run/…      │    Model ▼  Size ▼  From run ▼            │
│                  │    [▶ Run Stage 03]                        │
└──────────────────┴───────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  LOG                                                         │
│  > Loading model...                                          │
│  > Processing image_01_upscaled.png                          │
│  > Done. Saved to output/depth_maps/my_run/                  │
└──────────────────┬───────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  OUTPUT VIEWER                                               │
│  [image canvas — full display of result]                     │
│  [✓ Use in Next Step]          [↺ Recreate]                  │
└──────────────────────────────────────────────────────────────┘
```

---

## Component Details

### TopNav
- "K9 Crystal Pipeline" title on the left
- Pipeline selector dropdown on the right — populated by `GET /api/pipelines`
- Breadcrumbs placeholder (Phase 2 — not wired in Phase 1)

### InputBrowser
Two sections stacked vertically:

**Section 1 — Source Input (`input/`)**
- Lists files in `pipeline-01/input/` via `GET /api/files?dir=input`
- Click to select a file → sets `selectedFile` in page state
- Upload button → `POST /api/upload` → file appears in list

**Section 2 — Mid-Pipeline Files**
- Lists run folders under `output/upscaled/`, `output/bg_removed/`, `output/depth_maps/`
- Grouped by stage, then by run folder
- Click a file → pre-fills the matching StagePanel's `fromRun` field and scrolls to it
- Lets you jump back in at any stage without re-running earlier steps

### StagePanel
One accordion panel per stage (01–05). Fields:

| Stage | Fields |
|-------|--------|
| 01 Upscale | model (RealESRGAN_x4plus / _x2plus / _anime_6B), factor (2/4), tile size, run name |
| 02 Remove BG | model (isnet-general-use / u2net / u2netp / sam), from-run |
| 03 Depth | model (depth_anything_v2 / depth_pro / marigold / patchfusion), size (Small/Base/Large), from-run |
| 04 Mesh | placeholder — "not yet implemented" |
| 05 Export | placeholder — "not yet implemented" |

Run button → `POST /api/run-stage` → opens SSE stream → LogStream renders lines live.

### OutputViewer
- Appears after a stage completes successfully
- Displays output image(s) via `GET /api/output-image?path=...`
- Stage 02 shows `_nobg.png` and `_mask.png` side by side
- **"✓ Use in Next Step"** → sets the next StagePanel's `fromRun` to the just-completed run, scrolls down
- **"↺ Recreate"** → `DELETE /api/delete-run` removes the output folder, resets that StagePanel to idle

### LogStream
- Subscribes to SSE stream from `/api/run-stage`
- Renders each stdout line in a fixed-height scrolling log box
- On `event: done` → marks stage complete, triggers OutputViewer refresh
- On `event: error` → marks stage failed in red

---

## Pipeline-to-Web Folder Path

All API routes resolve the pipeline folder relative to the Next.js project root:

```js
// In every route handler:
const PIPELINE_ROOT = path.resolve(process.cwd(), '..', 'pipeline-01')
```

This assumes `web/` and `pipeline-01/` are siblings under the repo root. Do not hardcode absolute paths.

---

## Python Script Interface (what the web calls)

```bash
# Stage 01
python 01_upscale.py --file image_01.jpg --run my_session [--factor 4] [--model RealESRGAN_x4plus] [--tile 400]

# Stage 02
python 02_remove_bg.py --from-run my_session --run my_session [--model isnet-general-use]

# Stage 03
python 03_depth_estimate.py --from-run my_session --run my_session [--model depth_anything_v2] [--size Large]
```

The `--run` argument accepts a user-supplied name (e.g. `my_session`) OR omit it for auto-increment (`try_01`, `try_02`, ...). This required a small change to `utils/file_utils.py` — see Python Modifications section in the plan.

---

## Depth Models Available (Stage 03)

| Model key | Description | Speed |
|-----------|------------|-------|
| `depth_anything_v2` | Default. Best speed/quality for portraits. | ~3s on RTX 3060 |
| `depth_pro` | Apple Depth Pro. Sharper boundaries. | Medium |
| `marigold` | Diffusion-based. Best surface detail. | Slow (minutes) |
| `patchfusion` | High-res tile fusion. Complex setup. | Slow |

All four are in `MODEL_REGISTRY` in `03_depth_estimate.py`. Models auto-download on first use.

---

## Phase Status

| Phase | Description | Status |
|-------|------------|--------|
| Phase 1 | Landing page: InputBrowser, StagePanels 01–03, OutputViewer, LogStream, all API routes | **In progress** |
| Phase 2 | Breadcrumb navigation, multi-session management, run history | Planned |
| Phase 3 | Stage 04 mesh viewer (3D canvas), Stage 05 export | Planned |

---

## Running the Dev Server

```powershell
cd web
npm run dev
# Opens on http://localhost:3000
```

Python venv must be activated for the API routes to spawn scripts correctly:
```powershell
cd ..\pipeline-01
.\.venv\Scripts\Activate.ps1
```

Then keep the venv active in the same terminal session before starting `npm run dev`, or configure the Route Handlers to call the venv Python path explicitly (preferred for reliability):

```js
// Preferred: explicit venv python path
const PYTHON = path.resolve(PIPELINE_ROOT, '.venv', 'Scripts', 'python.exe')
spawn(PYTHON, ['01_upscale.py', '--file', ...], { cwd: PIPELINE_ROOT })
```
