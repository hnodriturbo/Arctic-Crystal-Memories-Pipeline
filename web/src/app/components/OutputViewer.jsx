// =============================================================
// OutputViewer — Output image display with Use/Recreate actions
// =============================================================
// PURPOSE:
//   Displays the output file(s) produced by the last completed
//   stage, and provides two actions: advance to the next stage
//   or delete and redo the current stage.
//
// PROPS:
//   pipeline      — string, e.g. "pipeline-01"
//   stage         — number, 1–5 (the stage that just completed)
//   run           — string, run folder name of the output
//   outputFiles   — array of relative paths to display
//                   e.g. ["output/upscaled/my_run/image_01_upscaled.png"]
//                   Stage 02 passes both _nobg.png and _mask.png
//   onUseInNext   — function({ stage, run }) called when user clicks
//                   "✓ Use in Next Step"
//   onRecreate    — function({ stage, run }) called when user clicks
//                   "↺ Recreate" — parent should DELETE the run folder
//                   and reset the stage panel
//
// LAYOUT:
//   - Title bar: "Output — Stage 0N — [run name]"
//   - Image display area:
//       Single image: centred, max width filling the container
//       Stage 02: two images side by side (_nobg and _mask)
//   - Image served via /api/output-image?pipeline=X&path=Y
//   - Action buttons below the image(s):
//       [✓ Use in Next Step]  [↺ Recreate]
//
// IMPLEMENTATION NOTES:
//   - Mark as 'use client'.
//   - Images are large (3840×3840 for upscaled). Use CSS max-width: 100%
//     and natural aspect ratio so they fit the panel without overflow.
//   - "Recreate" should show a confirmation modal/popover before calling
//     DELETE /api/delete-run (destructive operation).
//   - Stage 03 depth map: show the _preview_depth.png (inferno colormap),
//     not the raw 16-bit _depth.png (which looks black in browser).
//   - Fade-in animation when outputFiles changes (new result appeared).
// =============================================================
