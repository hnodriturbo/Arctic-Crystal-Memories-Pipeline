# K9 Crystal Pipeline — Web Frontend Spec

> **Purpose:** Shared contract between the developer and Claude Code, Codex and Github Copilot for the `web/` Next.js application. Describes what has been built, how it connects to the Python pipeline backend, and how to run it.

---

## What This App Is

A local operator UI for the K9 Crystal Pipeline. It wraps the Python CLI scripts in `pipeline/` so that:

- You can browse all pipeline images (input + all output folders) without touching the filesystem
- You can trigger upscale, enhance, or background removal from a button with live log streaming
- You can preview images in a modal before and after processing
- You can approve or deny each result — denied outputs are deleted automatically
- You never need to type a terminal command to process a photo

This is a **single-user local dev tool**, not a hosted web app. It runs via `npm run dev` on `localhost:3000`.
Login is required — admin credentials are set up via `prisma/seed.js`.

---

## Tech Stack

| Layer         | Technology                                           |
| ------------- | ---------------------------------------------------- |
| Framework     | Next.js 16 (App Router)                              |
| UI            | React 19, Tailwind CSS 4                             |
| Backend       | Next.js Route Handlers (Node.js)                     |
| Python bridge | `child_process.spawn()` in Route Handlers            |
| Streaming     | Server-Sent Events (SSE) for live terminal output    |
| Auth          | NextAuth v5 (credentials, JWT sessions)              |
| Database      | PostgreSQL via Prisma 7 + `@prisma/adapter-pg`       |
| State         | React context (`AppContext`) — no external state lib |
| Font          | Inter (UI) + JetBrains Mono (terminal)               |

---

## How Python Gets Triggered

```
Browser clicks Run
  → POST /api/process  { operation, file, engine, ... }
  → Node.js spawns: pipeline/.venv/Scripts/python.exe code/upscale.py --file X --engine Y
  → stdout/stderr lines streamed back as SSE
  → Terminal component renders each line live
  → On exit code 0: output image preview loads
  → Approve → keep file | Deny → DELETE /api/run removes the output file
```

Python is called with its existing CLI interface. No Python server, no FastAPI, no message queue. One spawn per button press.

---

## Directory Layout

```
web/
├── prisma/
│   ├── schema.prisma        ← User + ProcessRun tables
│   ├── seed.js              ← Creates admin user (node prisma/seed.js)
│   └── prisma.md            ← Setup guide (database creation + push steps)
├── prisma.config.ts         ← Prisma 7 config (requires .ts — Prisma 7 does not support .js config)
├── src/
│   ├── auth.js              ← NextAuth v5 config (credentials + JWT)
│   ├── core/
│   │   └── prisma.js        ← Singleton Prisma client (@prisma/adapter-pg)
│   └── app/
│       ├── layout.js        ← Root layout (Inter + JetBrains Mono fonts, dark class default)
│       ├── globals.css      ← Tailwind 4, dark/light vars, scrollbar, checkerboard bg
│       ├── page.jsx         ← Main dashboard (server component → ClientShell)
│       ├── login/
│       │   └── page.jsx     ← Login form (NextAuth credentials)
│       ├── process/
│       │   └── page.jsx     ← Processing page: preview → run → terminal → approve/deny
│       ├── context/
│       │   └── AppContext.jsx ← Global state: images, modal, theme, sort, selectedImage
│       ├── components/
│       │   ├── ClientShell.jsx     ← Wraps AppProvider, Navbar, Sidebar, ImageGrid, ImageModal
│       │   ├── Navbar.jsx          ← Top bar: logo, theme toggle, sign-out
│       │   ├── Sidebar.jsx         ← Folder filter (desktop: sidebar, mobile: pills)
│       │   ├── ImageGrid.jsx       ← Thumbnail grid with sort, select, double-click modal
│       │   ├── ImageModal.jsx      ← Responsive modal viewer (Esc / backdrop to close)
│       │   ├── ProcessingPanel.jsx ← Operation tabs: Upscale / Enhance / Remove BG + options
│       │   ├── Terminal.jsx        ← SSE terminal output (stdout white, stderr amber)
│       │   └── ThemeToggle.jsx     ← Light/dark toggle button
│       └── api/
│           ├── auth/[...nextauth]/route.js  ← NextAuth handler
│           ├── images/route.js              ← GET: list all pipeline images
│           ├── image/[...imgpath]/route.js  ← GET: serve image binary from disk
│           ├── process/route.js             ← POST: spawn Python script, SSE stream
│           └── run/route.js                 ← DELETE: remove a denied output file
├── middleware.js            ← Redirects unauthenticated requests to /login
├── .env.local               ← DATABASE_URL, AUTH_SECRET, PIPELINE_ROOT (not committed)
├── .env.example             ← Template for .env.local
├── PROJECT_CONTEXT.md          ← This file
├── AGENTS.md                ← Next.js 16 agent rules (read before editing)
└── package.json
```

---

## API Routes

| Route                        | Method   | Body / Query                              | Returns                       |
| ---------------------------- | -------- | ----------------------------------------- | ----------------------------- |
| `/api/images`                | GET      | —                                         | `{ files: [...], threshold }` |
| `/api/image/[folder]/[file]` | GET      | —                                         | Image binary                  |
| `/api/process`               | POST     | `{ operation, file, engine, model, ... }` | SSE stream of stdout/stderr   |
| `/api/run`                   | DELETE   | `{ filePath }`                            | `{ ok: true }`                |
| `/api/auth/[...nextauth]`    | GET/POST | —                                         | NextAuth session handlers     |

---

## Operations (Python Scripts)

| Operation   | Script              | Output folder        | Output filename pattern |
| ----------- | ------------------- | -------------------- | ----------------------- |
| `upscale`   | `code/upscale.py`   | `output/upscaled/`   | `<stem>_upscaled.png`   |
| `enhance`   | `code/enhance.py`   | `output/enhanced/`   | `<stem>_enhanced.png`   |
| `remove_bg` | `code/remove_bg.py` | `output/bg_removed/` | `<stem>_bg_removed.png` |

All three are independent — no ordering required.

---

## Image Folders Exposed in UI

| Folder key   | Pipeline path                 | Description                    |
| ------------ | ----------------------------- | ------------------------------ |
| `input`      | `pipeline/input/`             | Source images                  |
| `upscaled`   | `pipeline/output/upscaled/`   | AI-upscaled outputs            |
| `enhanced`   | `pipeline/output/enhanced/`   | Face-restored/enhanced outputs |
| `bg_removed` | `pipeline/output/bg_removed/` | Transparent-background outputs |

---

## Environment Variables (.env.local)

| Variable            | Description                                                | Example                                                            |
| ------------------- | ---------------------------------------------------------- | ------------------------------------------------------------------ |
| `DATABASE_URL`      | PostgreSQL connection string (URL-encoded password)        | `postgresql://postgres:pass%21@localhost:5432/k9-crystal-pipeline` |
| `AUTH_SECRET`       | NextAuth JWT signing secret                                | random 32-char string                                              |
| `PIPELINE_ROOT`     | Absolute path to `pipeline/` folder                        | `D:\\Hnodri\\Repos\\K9-Crystal-Pipeline\\pipeline`                 |
| `UPSCALE_THRESHOLD` | Long-edge px below which "upscale recommended" badge shows | `1800`                                                             |

---

## Page Flow

```
/login
  → credentials form → NextAuth JWT → redirect to /

/ (dashboard)
  → Sidebar folder filter + ImageGrid thumbnails
  → Single click = select image
  → Double click (or click selected again) = ImageModal preview
  → "Process" button → /process?file=X&folder=Y

/process?file=X&folder=Y
  → Input image preview (click to open modal)
  → ProcessingPanel: Upscale / Enhance / Remove BG tabs + engine options
  → Run button → POST /api/process → SSE terminal stream
  → On success: output image preview appears
  → Approve: keep file as-is
  → Deny: DELETE /api/run removes the output file
```

---

## Dark / Light Mode

Default is dark (`.dark` class on `<html>`). ThemeToggle in the navbar switches via `AppContext.theme`. The class is applied by `ClientShell` and `ProcessPageInner` via a `useEffect`.

---

## Running the Dev Server

```powershell
# 1. Set up database (first time only — see prisma/prisma.md)
psql -U postgres -c 'CREATE DATABASE "k9-crystal-pipeline";'
cd web
npx prisma db push
node prisma/seed.js

# 2. Start the app
npm run dev
# Opens on http://localhost:3000
```

The Python venv at `pipeline/.venv/` must exist and have dependencies installed. The web app calls it via the absolute path in `PIPELINE_ROOT` — no manual activation needed.

---

## Prisma Notes

- Prisma 7 requires `prisma.config.ts` (`.js` is not supported by Prisma 7's config parser)
- `prisma.config.ts` loads `.env.local` via `dotenv/config` for CLI commands
- `src/core/prisma.js` uses `@prisma/adapter-pg` in the Next.js runtime
- After schema changes: `npx prisma db push && npx prisma generate`
- To inspect data: `npx prisma studio` (opens at http://localhost:5555)
