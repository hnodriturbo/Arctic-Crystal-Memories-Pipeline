/*
 * ═══════════════════════════════════════════════════════════════
 * R2 Presign Route
 * ═══════════════════════════════════════════════════════════════
 * Path: src/app/api/r2/presign/route.js
 * Purpose: Mint a short-lived URL the browser can upload straight to.
 *
 * The signing happens here, behind the sign-in, so the R2 credentials never
 * reach the browser - only a URL that is good for one key, one content type,
 * and fifteen minutes.
 */

import path from "node:path";

import { presignUpload, r2Configured } from "@/lib/storage/r2";
import { safeFileName } from "@/lib/paths";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// Only what this pipeline actually deals in. An open-ended list would make
// the bucket a general file drop, which it is not.
const ALLOWED = {
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".webp": "image/webp",
  ".glb": "model/gltf-binary",
  ".obj": "text/plain",
  ".stl": "model/stl",
  ".fbx": "application/octet-stream",
  ".dxf": "application/octet-stream",
  ".zip": "application/zip",
};

// Folders the browser is allowed to write into, so a crafted prefix cannot
// scribble over a job manifest.
const PREFIXES = { uploads: "uploads", archive: "archive" };

export async function POST(request) {
  if (!r2Configured()) {
    return Response.json({ error: "R2 is not configured on this server." }, { status: 503 });
  }

  const { fileName, prefix = "uploads" } = await request.json();
  if (!fileName) {
    return Response.json({ error: "Need a fileName" }, { status: 400 });
  }

  const folder = PREFIXES[prefix];
  if (!folder) {
    return Response.json({ error: `Unknown prefix: ${prefix}` }, { status: 400 });
  }

  const safe = safeFileName(fileName);
  const extension = path.extname(safe).toLowerCase();
  const contentType = ALLOWED[extension];
  if (!contentType) {
    return Response.json(
      { error: `${extension || "That file type"} cannot be uploaded here.` },
      { status: 400 },
    );
  }

  // Date-partitioned and timestamped, so two uploads of "photo.jpg" on the
  // same day do not overwrite one another.
  const day = new Date().toISOString().slice(0, 10);
  const key = `${folder}/${day}/${Date.now()}-${safe}`;

  try {
    const url = await presignUpload(key, contentType);
    return Response.json({ key, url, contentType, expiresIn: 900 });
  } catch (error) {
    return Response.json({ error: error.message }, { status: 502 });
  }
}
