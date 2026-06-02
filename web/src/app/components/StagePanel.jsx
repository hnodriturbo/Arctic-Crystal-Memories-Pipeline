// =============================================================
// StagePanel — Per-stage controls accordion panel
// =============================================================
// PURPOSE:
//   Renders the configuration fields and Run button for a single
//   pipeline stage. One instance per stage (01–05) stacked
//   vertically in the right column of the main layout.
//
// PROPS:
//   stage         — number, 1–5
//   pipeline      — string, e.g. "pipeline-01"
//   fromRun       — string, pre-filled from-run value (set by InputBrowser
//                   click or OutputViewer "Use in Next Step" action)
//   onRunComplete — function({ stage, run, outputFiles }) called when
//                   the Python process exits with code 0
//   onRunStart    — function({ stage }) called when Run button is pressed
//
// STAGE CONFIGS:
//   Stage 01 — Upscale:
//     Fields: source file (read-only, from parent state), model dropdown
//             (RealESRGAN_x4plus / _x2plus / _anime_6B), factor (2/4),
//             tile size (number input, default 400), run name (text input)
//
//   Stage 02 — Remove BG:
//     Fields: model dropdown (isnet-general-use / u2net / u2netp / sam),
//             from-run (text input, pre-fillable), run name (text input)
//
//   Stage 03 — Depth Estimation:
//     Fields: model dropdown (depth_anything_v2 / depth_pro / marigold /
//             patchfusion), size dropdown (Small / Base / Large — shown
//             only when model is depth_anything_v2), from-run (text input),
//             run name (text input)
//
//   Stage 04 — Mesh Generation:
//     Placeholder only: "Stage 04 not yet implemented"
//
//   Stage 05 — Export:
//     Placeholder only: "Stage 05 not yet implemented"
//
// IMPLEMENTATION NOTES:
//   - Mark as 'use client'.
//   - Accordion: collapsed by default, expands on header click.
//   - Disabled state: stage 02+ are visually dimmed and Run button is
//     disabled until fromRun is populated (either by selection or typed).
//   - On Run click: POST to /api/run-stage with stage name and all args;
//     open the SSE stream and pass it to the LogStream component.
//   - Show a spinner on the Run button while the stage is running.
//   - On SSE "done" event with code 0: call onRunComplete, collapse panel.
//   - On SSE "done" event with non-zero code: show error state in red.
//   - Run name field: if left empty, the Python script auto-increments (try_01, etc.)
// =============================================================
