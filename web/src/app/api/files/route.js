// =============================================================
// GET /api/files
// =============================================================
// PURPOSE:
//   Lists files inside any directory within the selected pipeline,
//   used by the InputBrowser to populate both the source input
//   section and the mid-pipeline output sections.
//
// QUERY PARAMS:
//   pipeline  — e.g. "pipeline-01"
//   dir       — relative path inside the pipeline folder,
//               e.g. "input", "output/upscaled", "output/bg_removed"
//
// RESPONSE:
//   {
//     dir: "input",
//     files: [
//       { name: "image_01.jpg", size: 123456, mtime: "2026-05-28T..." },
//       ...
//     ]
//   }
//
// IMPLEMENTATION NOTES:
//   - Resolve the full path as: PIPELINE_ROOT / pipeline / dir
//   - Only return files (not subdirectories) at the top level of dir.
//   - For output stage dirs (output/upscaled, output/bg_removed,
//     output/depth_maps), return run subfolders as groups instead —
//     i.e. recurse one level into try_XX / custom-name folders and
//     return the files inside them tagged with their run folder name.
//   - Filter to image extensions only: .png, .jpg, .jpeg, .webp, .tiff
//   - Sorted by mtime descending (newest first) so latest runs appear
//     at the top of the mid-pipeline section.
//   - Security: validate that the resolved path stays inside PIPELINE_ROOT
//     (no path traversal).
// =============================================================
