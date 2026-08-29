/*
 * ═══════════════════════════════════════════════════════════════
 * Image Run Route
 * ═══════════════════════════════════════════════════════════════
 * Path: src/app/api/image/run/route.js
 * Purpose: Clean one or more photos and stream the stages as they run.
 */

import path from "node:path";

import { runImageChain } from "@/lib/image/chain";
import { IMAGE_INPUT_DIR, IMAGE_OUTPUT_DIR, resolveInside } from "@/lib/paths";
import { sseResponse } from "@/lib/sse";

export const runtime = "nodejs";
export const maxDuration = 3600;

export async function POST(request) {
  const { photos = [], values = {} } = await request.json();

  return sseResponse(request, async (emit, signal) => {
    if (!photos.length) throw new Error("Pick at least one photo.");

    for (const relative of photos) {
      // Fence every photo inside input/ before anything touches it.
      const source = resolveInside(IMAGE_INPUT_DIR, relative);
      if (!source) throw new Error(`Photo escapes the input folder: ${relative}`);

      emit({ type: "step", line: `── ${path.basename(source)}` });
      const { finalPath, produced } = await runImageChain({
        source,
        destinationDir: IMAGE_OUTPUT_DIR,
        values,
        emit,
        signal,
      });

      emit({
        type: "result",
        source: relative,
        final: path.basename(finalPath),
        produced: produced.map((file) => path.basename(file)),
      });
    }
  });
}
