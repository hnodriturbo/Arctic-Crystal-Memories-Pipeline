/*
 * ═══════════════════════════════════════════════════════════════
 * Meshy Run Route
 * ═══════════════════════════════════════════════════════════════
 * Path: src/app/api/meshy/run/route.js
 * Purpose: Run one photo-to-3D job and stream its progress.
 */

import { runMeshyJob } from "@/lib/meshy/run-job";
import { sseResponse } from "@/lib/sse";

export const runtime = "nodejs";
export const maxDuration = 3600;

export async function POST(request) {
  const { mode, photos, values } = await request.json();

  return sseResponse(request, (emit, signal) =>
    runMeshyJob({ mode, photos, values, emit, signal }),
  );
}
