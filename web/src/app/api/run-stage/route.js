// =============================================================
// POST /api/run-stage
// =============================================================
// PURPOSE:
//   Spawns a Python pipeline script as a subprocess and streams
//   its stdout/stderr back to the browser as a Server-Sent Events
//   (SSE) stream so the LogStream component can render live output.
//
// REQUEST BODY (JSON):
//   {
//     pipeline: "pipeline-01",
//     stage:    "01_upscale",           // script name without .py
//     args: {
//       file:   "image_01.jpg",         // --file
//       run:    "my_session",           // --run (optional, omit for auto)
//       factor: "4",                    // --factor (stage 01)
//       model:  "RealESRGAN_x4plus",    // --model
//       tile:   "400",                  // --tile (stage 01)
//       size:   "Large",               // --size  (stage 03)
//       "from-run": "my_session",       // --from-run (stages 02, 03)
//     }
//   }
//
// RESPONSE:
//   Content-Type: text/event-stream
//   Events:
//     data: { type: "stdout", line: "..." }
//     data: { type: "stderr", line: "..." }
//     data: { type: "done",   code: 0 }
//     data: { type: "error",  message: "..." }
//
// IMPLEMENTATION NOTES:
//   - Build CLI args array from the args object: each key → "--key", value → value.
//     Skip undefined/null values.
//   - Python executable: PIPELINE_ROOT / pipeline / .venv / Scripts / python.exe
//     (Windows path; use process.platform check if cross-platform support ever needed)
//   - cwd for spawn: PIPELINE_ROOT / pipeline
//   - Script path: just the filename e.g. "01_upscale.py" — cwd handles resolution.
//   - Set response headers: Cache-Control: no-cache, Connection: keep-alive,
//     Content-Type: text/event-stream
//   - Use a ReadableStream + controller to push SSE lines from spawn stdout/stderr.
//   - On process exit: send done event with exit code, then close the stream.
//   - On spawn error (e.g. python not found): send error event immediately.
//   - Allowed stages whitelist: ["01_upscale", "02_remove_bg", "03_depth_estimate",
//     "04_mesh_generate", "05_export"] — reject anything else with 400.
// =============================================================
