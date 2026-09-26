/*
 * ═══════════════════════════════════════════════════════════════
 * Prompt Route
 * ═══════════════════════════════════════════════════════════════
 * Path: src/app/api/meshy/prompt/route.js
 * Purpose: Have OpenAI look at a photo and write the Meshy prompt for it.
 */

import { readFile } from "node:fs/promises";
import path from "node:path";

import { describePhoto } from "@/lib/meshy/vision";
import { MESHY_INPUT_DIR, resolveInside } from "@/lib/paths";

export const runtime = "nodejs";
export const maxDuration = 300;

const MIME_TYPES = { ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png" };

export async function POST(request) {
  const { photo, hint } = await request.json();

  const source = photo ? resolveInside(MESHY_INPUT_DIR, photo) : null;
  if (!source) {
    return Response.json({ error: "Pick a photo from the input folder first" }, { status: 400 });
  }

  const extension = path.extname(source).toLowerCase();
  const mime = MIME_TYPES[extension];
  if (!mime) {
    return Response.json({ error: `Cannot read ${extension || "that file"}` }, { status: 400 });
  }

  let bytes;
  try {
    bytes = await readFile(source);
  } catch {
    return Response.json({ error: "That photo is no longer on disk" }, { status: 404 });
  }

  try {
    const description = await describePhoto(
      `data:${mime};base64,${bytes.toString("base64")}`,
      { hint },
    );
    return Response.json(description);
  } catch (error) {
    return Response.json({ error: error.message }, { status: 502 });
  }
}
