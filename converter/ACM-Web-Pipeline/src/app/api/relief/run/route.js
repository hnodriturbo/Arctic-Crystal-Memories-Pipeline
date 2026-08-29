/*
 * ═══════════════════════════════════════════════════════════════
 * Relief Run Route
 * ═══════════════════════════════════════════════════════════════
 * Path: src/app/api/relief/run/route.js
 * Purpose: Build a 2.5D relief from one or more photographs, streaming each
 *          stage as it runs.
 */

import path from "node:path";

import { RELIEF_INPUT_DIR, resolveInside } from "@/lib/paths";
import { runReliefChain } from "@/lib/relief/chain";
import { sseResponse } from "@/lib/sse";

export const runtime = "nodejs";
// Marigold on CPU with a large ensemble is genuinely slow, and the reference
// service takes minutes per subject too. An hour is the same ceiling the
// image and Meshy routes use.
export const maxDuration = 3600;

export async function POST(request) {
  const { photos = [], values = {} } = await request.json();

  return sseResponse(request, async (emit, signal) => {
    if (!photos.length) throw new Error("Pick at least one photo.");

    for (const relative of photos) {
      // Fence every photo inside input/ before anything touches it.
      const source = resolveInside(RELIEF_INPUT_DIR, relative);
      if (!source) throw new Error(`Photo escapes the input folder: ${relative}`);

      emit({ type: "step", line: `── ${path.basename(source)}` });
      const manifest = await runReliefChain({ source, values, emit, signal });

      emit({ type: "result", source: relative, job: manifest });
    }
  });
}
