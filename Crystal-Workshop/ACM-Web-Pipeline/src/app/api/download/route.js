/*
 * ═══════════════════════════════════════════════════════════════
 * Download Route
 * ═══════════════════════════════════════════════════════════════
 * Path: src/app/api/download/route.js
 * Purpose: Hand a converted file back to the browser, streamed so a
 *          multi-hundred-megabyte DXF never sits in memory.
 */

import { createReadStream } from "node:fs";
import { stat } from "node:fs/promises";
import { Readable } from "node:stream";
import path from "node:path";

import { INPUT_DIR, OUTPUT_DIR, resolveInside } from "@/lib/paths";
import { presignDownload, r2Configured } from "@/lib/storage/r2";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const ROOTS = { output: OUTPUT_DIR, input: INPUT_DIR };

export async function GET(request) {
  const { searchParams } = new URL(request.url);
  const r2Key = searchParams.get("r2Key");
  if (r2Key) {
    const normalized = path.posix.normalize(r2Key);
    if (
      normalized !== r2Key ||
      normalized.includes("..") ||
      !normalized.startsWith("converter-jobs/") ||
      !r2Configured()
    ) {
      return Response.json({ error: "Invalid or unavailable R2 converter result" }, { status: 400 });
    }
    const url = await presignDownload(normalized, { fileName: path.posix.basename(normalized) });
    return Response.redirect(url, 302);
  }

  const rootKey = searchParams.get("root") || "output";
  const relativePath = searchParams.get("path");

  const root = ROOTS[rootKey];
  if (!root || !relativePath) {
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
    return Response.json({ error: "Not found" }, { status: 404 });
  }
  if (!info.isFile()) {
    return Response.json({ error: "Not a file" }, { status: 400 });
  }

  const fileName = path.basename(target);
  return new Response(Readable.toWeb(createReadStream(target)), {
    headers: {
      "Content-Type": "application/octet-stream",
      "Content-Length": String(info.size),
      "Content-Disposition": `attachment; filename="${fileName}"`,
    },
  });
}
