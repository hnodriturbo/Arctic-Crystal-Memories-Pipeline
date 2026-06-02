// =============================================================
// page.js — Landing page (root orchestrator)
// =============================================================
// PURPOSE:
//   The single page of the web UI. Composes all components and
//   manages the shared state that flows between them.
//
// STATE:
//   selectedPipeline  — string, e.g. "pipeline-01" (from TopNav dropdown)
//   selectedFile      — { name, stage, run } | null
//                       Set when user clicks a file in InputBrowser.
//                       stage is "input" for source files, or
//                       "upscaled"/"nobg"/"depth" for mid-pipeline files.
//   stagePanelState   — object keyed by stage number (1–5):
//                       { fromRun, runName, status: "idle"|"running"|"done"|"error" }
//   activeOutput      — { stage, run, outputFiles } | null
//                       Set by onRunComplete, cleared by onRecreate.
//   streamUrl         — string | null, SSE URL passed to LogStream.
//   refreshKey        — number, incremented after upload/completion to
//                       trigger InputBrowser to re-fetch file lists.
//
// LAYOUT (two-column + full-width log + output viewer):
//   ┌──────────────────────────────────────────────┐
//   │  TopNav                                      │
//   ├────────────────┬─────────────────────────────┤
//   │  InputBrowser  │  StagePanels (01–05)        │
//   │  (left col)    │  (right col, accordion)     │
//   ├────────────────┴─────────────────────────────┤
//   │  LogStream (full width)                      │
//   ├──────────────────────────────────────────────┤
//   │  OutputViewer (full width)                   │
//   └──────────────────────────────────────────────┘
//
// KEY INTERACTIONS:
//   - InputBrowser.onSelectSource → updates selectedFile,
//     pre-fills stagePanelState[N].fromRun for the matching stage
//   - StagePanel.onRunStart → sets streamUrl, sets stage status = "running"
//   - StagePanel.onRunComplete → sets activeOutput, increments refreshKey,
//     pre-fills stagePanelState[N+1].fromRun with the completed run name
//   - OutputViewer.onUseInNext → same as onRunComplete above
//   - OutputViewer.onRecreate → clears activeOutput, resets stage status = "idle"
//
// IMPLEMENTATION NOTES:
//   - Mark as 'use client' (all state is client-side).
//   - TopNav is rendered in layout.js (always visible), so this page
//     only needs to pass selectedPipeline down as a prop OR read it
//     from a context/URL param. Simpler approach: keep selectedPipeline
//     in page.js state and pass it as prop to children.
//   - Default selectedPipeline: first result from /api/pipelines.
// =============================================================
