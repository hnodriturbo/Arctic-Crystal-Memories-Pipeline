// =============================================================
// LogStream — Live stdout display via Server-Sent Events
// =============================================================
// PURPOSE:
//   Connects to the SSE stream from /api/run-stage and renders
//   each stdout/stderr line from the Python subprocess in a
//   fixed-height scrolling terminal-style log box.
//
// PROPS:
//   streamUrl     — string | null. When non-null, opens an EventSource
//                   to this URL. When null, shows idle state.
//   onDone        — function({ exitCode }) called when the SSE stream
//                   emits a "done" event
//   onError       — function({ message }) called on SSE error event
//
// SSE EVENT HANDLING:
//   event data shapes (JSON):
//     { type: "stdout", line: "..." }  → render in white
//     { type: "stderr", line: "..." }  → render in yellow/amber
//     { type: "done",   code: 0 }      → show green "Completed" banner, call onDone
//     { type: "done",   code: N }      → show red "Failed (exit N)" banner, call onDone
//     { type: "error",  message: "..." }→ show red error, call onError
//
// LAYOUT:
//   - Dark background (#0d1117 or similar) monospace font log area
//   - Fixed height, overflow-y: auto, auto-scrolls to bottom on new lines
//   - Each line prefixed with a ">" prompt character
//   - Status badge at the top: "Running..." / "Completed" / "Failed" / "Idle"
//   - Clear button to wipe the log lines without stopping the stream
//
// IMPLEMENTATION NOTES:
//   - Mark as 'use client'.
//   - Use EventSource API (built into browsers, no npm package needed).
//   - Close the EventSource when streamUrl changes to null or on unmount.
//   - Keep max 500 log lines in state — truncate oldest to avoid memory growth
//     on very long runs (Marigold depth can take several minutes).
//   - Auto-scroll uses a ref on the last log line element with scrollIntoView.
// =============================================================
