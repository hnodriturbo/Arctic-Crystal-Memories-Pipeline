// =============================================================
// GET /api/pipelines
// =============================================================
// PURPOSE:
//   Returns the list of available pipeline folders that the web UI
//   can switch between using the top navbar dropdown.
//
// RESPONSE:
//   { pipelines: ["pipeline-01"] }
//
// IMPLEMENTATION NOTES:
//   - Scan the parent of the web/ folder (repo root) for directories
//     named pipeline-NN (e.g. pipeline-01, pipeline-02).
//   - Only include directories that contain a recognisable pipeline
//     marker — e.g. a 01_upscale.py file — to avoid returning
//     unrelated sibling folders.
//   - PIPELINE_ROOT = path.resolve(process.cwd(), '..') from web/
//   - Return sorted alphabetically.
//   - This is a read-only operation; no filesystem writes.
// =============================================================
