/*
 * ═══════════════════════════════════════════════════════════════
 * Upload Route
 * ═══════════════════════════════════════════════════════════════
 * Path: src/app/api/upload/route.js
 * Purpose: Stream an uploaded file straight to whichever pipeline asked for it.
 *
 * The request body is piped rather than parsed as form data because a
 * Meshy DXF export runs to several hundred megabytes and buffering one
 * in memory would take the dev server down.
 */

import { createWriteStream } from "node:fs";
import { mkdir, rm, stat } from "node:fs/promises";
import { pipeline } from "node:stream/promises";
import { Readable } from "node:stream";
import path from "node:path";

import {
  IMAGE_INPUT_DIR,
  MESHY_INPUT_DIR,
  UPLOAD_DIR,
  availableFileName,
  safeFileName,
} from "@/lib/paths";

export const runtime = "nodejs";
export const maxDuration = 3600;

// One target per pipeline: models to the converter, photos to whichever of
// the two image-side workspaces asked for them.
const TARGETS = {
  converter: {
    directory: UPLOAD_DIR,
    extensions: [".obj", ".dxf", ".cad", ".xyz", ".ply", ".stl", ".cockpit"],
  },
  meshy: { directory: MESHY_INPUT_DIR, extensions: [".jpg", ".jpeg", ".png"] },
  image: {
    directory: IMAGE_INPUT_DIR,
    extensions: [".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"],
  },
};

const MAX_UPLOAD_BYTES = 100 * 1024 * 1024;

export async function POST(request) {
  const rawName = request.headers.get("x-filename");
  if (!rawName) {
    return Response.json({ error: "Missing x-filename header" }, { status: 400 });
  }
  if (!request.body) {
    return Response.json({ error: "Empty request body" }, { status: 400 });
  }

  const targetKey = request.headers.get("x-target") || "converter";
  const targetConfig = TARGETS[targetKey];
  if (!targetConfig) {
    return Response.json({ error: `Unknown upload target: ${targetKey}` }, { status: 400 });
  }

  // The client percent-encodes, because header values cannot carry non-ASCII.
  let decodedName = rawName;
  try {
    decodedName = decodeURIComponent(rawName);
  } catch {
    decodedName = rawName;
  }
  const safeName = safeFileName(decodedName);
  const extension = path.extname(safeName).toLowerCase();
  if (!targetConfig.extensions.includes(extension)) {
    return Response.json(
      { error: `${targetKey} accepts ${targetConfig.extensions.join(", ")} - not ${extension || "that file"}.` },
      { status: 400 },
    );
  }

  const announcedBytes = Number(request.headers.get("content-length") || 0);
  if (announcedBytes > MAX_UPLOAD_BYTES) {
    return Response.json(
      { error: "Uploads through the website are limited to 100 MB. Use R2 or SSH/SFTP for larger files." },
      { status: 413 },
    );
  }

  const directory = targetConfig.directory;
  await mkdir(directory, { recursive: true });
  const fileName = await availableFileName(directory, safeName);
  const target = path.join(directory, fileName);

  try {
    await pipeline(Readable.fromWeb(request.body), createWriteStream(target, { flags: "wx" }));
  } catch (error) {
    await rm(target, { force: true }).catch(() => {});
    return Response.json({ error: `Upload failed: ${error.message}` }, { status: 500 });
  }

  const written = await stat(target);
  if (written.size > MAX_UPLOAD_BYTES) {
    await rm(target, { force: true });
    return Response.json({ error: "Upload exceeded the 100 MB website limit." }, { status: 413 });
  }
  return Response.json({
    name: fileName,
    bytes: written.size,
    extension,
    // Relative to the target pipeline's own root, which is what each client stores.
    path: targetKey === "converter" ? `uploads/${fileName}` : fileName,
  });
}
