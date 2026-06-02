// =============================================================
// POST /api/upload
// =============================================================
// PURPOSE:
//   Receives a file upload from the InputBrowser and saves it
//   to the pipeline's input/ folder, making it available for
//   Stage 01 processing.
//
// REQUEST:
//   Content-Type: multipart/form-data
//   Fields:
//     pipeline  — e.g. "pipeline-01"
//     file      — the uploaded image file (Blob)
//
// RESPONSE (success):
//   { saved: "my_photo.jpg", path: "input/my_photo.jpg" }
//
// RESPONSE (error):
//   { error: "message" }  with appropriate HTTP status
//
// IMPLEMENTATION NOTES:
//   - Use Next.js built-in request.formData() to parse multipart.
//   - Save destination: PIPELINE_ROOT / pipeline / input / filename
//   - Sanitise the filename (strip path separators, disallow dotfiles).
//   - Allowed extensions: .jpg .jpeg .png .webp .tiff .bmp
//   - If a file with the same name already exists, append _1, _2, etc.
//     rather than overwriting silently.
//   - Max file size check: reject files over 100 MB with 413.
//   - No image processing here — just a raw copy to disk.
// =============================================================
