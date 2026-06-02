// =============================================================
// DELETE /api/delete-run
// =============================================================
// PURPOSE:
//   Removes a specific output run folder when the user clicks
//   "↺ Recreate" in the OutputViewer, freeing the run name so
//   the stage can be re-run and produce a fresh result.
//
// REQUEST BODY (JSON):
//   {
//     pipeline:  "pipeline-01",
//     stageDir:  "upscaled",          // STAGE_OUTPUT_DIRS key
//     run:       "my_session"         // run folder name to delete
//   }
//
// RESPONSE (success):
//   { deleted: true, path: "output/upscaled/my_session" }
//
// RESPONSE (error):
//   { error: "message" }  with HTTP 400 or 404
//
// IMPLEMENTATION NOTES:
//   - Resolved delete target: PIPELINE_ROOT / pipeline / output / stageDir / run
//   - Security: validate the resolved path stays inside PIPELINE_ROOT/pipeline/output/
//     (prevent deleting arbitrary filesystem paths).
//   - Use fs.rm(path, { recursive: true }) — Node 18+.
//   - If the folder does not exist, return { deleted: false } with 200
//     (idempotent — the UI may have already deleted it).
//   - Valid stageDir values: "upscaled", "bg_removed", "depth_maps",
//     "point_clouds", "meshes", "exports" — reject others with 400.
// =============================================================
