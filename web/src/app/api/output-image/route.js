// =============================================================
// GET /api/output-image
// =============================================================
// PURPOSE:
//   Serves a pipeline output image as binary so the OutputViewer
//   component can display it in an <img> tag without exposing the
//   raw filesystem path to the browser.
//
// QUERY PARAMS:
//   pipeline  — e.g. "pipeline-01"
//   path      — relative path inside the pipeline folder,
//               e.g. "output/upscaled/my_session/image_01_upscaled.png"
//
// RESPONSE:
//   Binary image with correct Content-Type header (image/png, image/jpeg, etc.)
//   Cache-Control: public, max-age=3600 (images don't change after creation)
//
// IMPLEMENTATION NOTES:
//   - Resolve full path: PIPELINE_ROOT / pipeline / path param
//   - Security: validate resolved path stays inside PIPELINE_ROOT/pipeline/output/
//   - Determine Content-Type from file extension (.png → image/png, etc.)
//   - Read file as Buffer and return as Response with appropriate headers.
//   - Return 404 if file does not exist.
//   - 16-bit PNG depth maps are valid PNG — serve them the same way.
//     The browser will display them (they look mostly black; that's expected).
// =============================================================
