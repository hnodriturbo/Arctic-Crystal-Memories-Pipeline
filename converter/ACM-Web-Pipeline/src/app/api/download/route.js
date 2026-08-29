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

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const ROOTS = { output: OUTPUT_DIR, input: INPUT_DIR };

export async function GET(request) {
  const { searchParams } = new URL(request.url);
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
