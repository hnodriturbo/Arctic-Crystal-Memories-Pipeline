// =============================================================
// InputBrowser — Left panel: source files + mid-pipeline files
// =============================================================
// PURPOSE:
//   Two-section left panel that lets the user select a starting
//   image for the pipeline, either from the raw input/ folder or
//   from a partially-processed output folder (to resume mid-pipeline).
//
// PROPS:
//   pipeline         — string, e.g. "pipeline-01"
//   onSelectSource   — function({ file, stage, run }) called when user
//                      clicks any file; stage is "input" for source files,
//                      or "upscaled"/"nobg"/"depth" for mid-pipeline files
//
// SECTION 1 — Source Input (input/ folder):
//   - Lists files from GET /api/files?pipeline=X&dir=input
//   - Thumbnail preview if browser can render the format
//   - Upload button: opens file picker, POSTs to /api/upload,
//     then refreshes the list
//   - Clicking a file calls onSelectSource({ file, stage: "input" })
//
// SECTION 2 — Mid-Pipeline Files:
//   - Reads output/upscaled/, output/bg_removed/, output/depth_maps/
//     via GET /api/files for each, grouped by stage label
//   - Shows run folder name and file name
//   - Clicking a file calls onSelectSource({ file, stage, run })
//     so the parent can pre-fill the appropriate StagePanel's fromRun
//
// IMPLEMENTATION NOTES:
//   - Mark as 'use client'.
//   - Poll or re-fetch file lists after upload and after a stage completes
//     (parent should pass a refreshKey prop that increments on completion).
//   - Highlight the currently selected file.
//   - Both sections are scrollable independently if content overflows.
//   - Use a divider/separator between the two sections with a label
//     "Mid-Pipeline Files" as a section heading.
// =============================================================
