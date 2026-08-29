/*
 * ═══════════════════════════════════════════════════════════════
 * File Route
 * ═══════════════════════════════════════════════════════════════
 * Path: src/app/api/file/route.js
 * Purpose: Serve one file out of any pipeline workspace - inline for the
 *          in-page 3D viewer and the thumbnails, as a download when asked.
 *
 * The converter keeps its own /api/download because its trees are walked
 * recursively; everything here is a flat folder addressed by name.
 */

import { createReadStream } from "node:fs";
import { stat } from "node:fs/promises";
import path from "node:path";
import { Readable } from "node:stream";

import {
  IMAGE_INPUT_DIR,
  IMAGE_OUTPUT_DIR,
  MESHY_INPUT_DIR,
  MESHY_OUTPUT_DIR,
  MESHY_WORK_DIR,
  RELIEF_BLANKS_DIR,
  RELIEF_INPUT_DIR,
  RELIEF_OUTPUT_DIR,
  resolveInside,
} from "@/lib/paths";
import { presignDownload, r2Configured } from "@/lib/storage/r2";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const ROOTS = {
  "image-input": IMAGE_INPUT_DIR,
  "image-output": IMAGE_OUTPUT_DIR,
  "meshy-input": MESHY_INPUT_DIR,
  "meshy-work": MESHY_WORK_DIR,
  "meshy-output": MESHY_OUTPUT_DIR,
  "relief-input": RELIEF_INPUT_DIR,
  // Relief output is one folder per job, so paths here are nested
  // (<job-id>/relief.glb) rather than flat like the roots above.
  "relief-output": RELIEF_OUTPUT_DIR,
  "relief-blanks": RELIEF_BLANKS_DIR,
};

// model-viewer refuses a GLB served as octet-stream, and the browser would
// download the thumbnails instead of drawing them.
const CONTENT_TYPES = {
  ".glb": "model/gltf-binary",
  ".gltf": "model/gltf+json",
  ".obj": "text/plain; charset=utf-8",
  ".mtl": "text/plain; charset=utf-8",
  ".stl": "model/stl",
  ".usdz": "model/vnd.usdz+zip",
  ".fbx": "application/octet-stream",
  ".3mf": "model/3mf",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".webp": "image/webp",
  ".json": "application/json; charset=utf-8",
};

export async function GET(request) {
  const { searchParams } = new URL(request.url);
  const relativePath = searchParams.get("path");
  const asDownload = searchParams.get("download") === "1";
  const root = ROOTS[searchParams.get("root")];

  if (!relativePath || !root) {
    return Response.json({ error: "Need a valid root and path" }, { status: 400 });
  }

  const target = resolveInside(root, relativePath);
  if (!target) {
    return Response.json({ error: "Path escapes its root" }, { status: 403 });
  }

  let info;
  try {
    info = await stat(target);
  } catch {
    /*
     * Gone from disk, but a finished job was mirrored to R2 - so an old
     * download link keeps working after the workspace has been cleared out.
     * A redirect rather than a proxy: the object goes straight from R2 to the
     * browser instead of through this box twice.
     */
    const bucketPrefix = { "meshy-output": "jobs/", "relief-output": "relief-jobs/" }[
      searchParams.get("root")
    ];

    if (bucketPrefix && r2Configured()) {
      try {
        const url = await presignDownload(`${bucketPrefix}${relativePath.replace(/\\/g, "/")}`, {
          fileName: asDownload ? path.basename(relativePath) : undefined,
        });
        return Response.redirect(url, 302);
      } catch {
        // Fall through to the 404 below; the object is not there either.
      }
    }
    return Response.json({ error: "Not found" }, { status: 404 });
  }
  if (!info.isFile()) {
    return Response.json({ error: "Not a file" }, { status: 400 });
  }

  const extension = path.extname(target).toLowerCase();
  const fileName = path.basename(target);

  return new Response(Readable.toWeb(createReadStream(target)), {
    headers: {
      "Content-Type": asDownload
        ? "application/octet-stream"
        : CONTENT_TYPES[extension] || "application/octet-stream",
      "Content-Length": String(info.size),
      "Content-Disposition": `${asDownload ? "attachment" : "inline"}; filename="${fileName}"`,
    },
  });
}
