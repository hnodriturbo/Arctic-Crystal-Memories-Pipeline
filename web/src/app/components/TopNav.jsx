// =============================================================
// TopNav — Top navigation bar
// =============================================================
// PURPOSE:
//   Renders the persistent top bar of the application with the
//   product title and a pipeline selector dropdown.
//
// PROPS:
//   selectedPipeline  — string, currently active pipeline (e.g. "pipeline-01")
//   onPipelineChange  — function(pipelineName) called when dropdown changes
//
// LAYOUT:
//   Left side:  "K9 Crystal Pipeline" — bold title text
//   Right side: Pipeline selector dropdown — options from GET /api/pipelines
//   Below bar:  Breadcrumb placeholder (empty div for now, wired in Phase 2)
//
// IMPLEMENTATION NOTES:
//   - Fetch available pipelines from /api/pipelines on mount.
//   - Dropdown shows human-readable labels (e.g. "Pipeline 01") mapped
//     from the folder name ("pipeline-01").
//   - The selected pipeline propagates up to page.js state so all child
//     components know which pipeline's files to read and which scripts to call.
//   - Use Tailwind for styling: dark background bar, white title text,
//     clean dropdown with rounded border.
//   - Mark as 'use client' (needs useState for pipeline list + fetch on mount).
// =============================================================
