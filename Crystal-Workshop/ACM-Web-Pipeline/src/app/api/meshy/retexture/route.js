/*
 * ═══════════════════════════════════════════════════════════════
 * Meshy Retexture Route
 * ═══════════════════════════════════════════════════════════════
 * Path: src/app/api/meshy/retexture/route.js
 * Purpose: Stream one review-time texture pass over an existing Meshy mesh.
 */

import { runMeshyRetexture } from "@/lib/meshy/retexture-job";
import { sseResponse } from "@/lib/sse";

export const runtime = "nodejs";
export const maxDuration = 3600;

export async function POST(request) {
  const { jobId, values } = await request.json();
  if (!jobId) return Response.json({ error: "Need a Meshy project id." }, { status: 400 });

  // Once Meshy has accepted a paid task, finish and persist it even if the
  // browser closes. Reopening review will then show the completed variant.
  return sseResponse(request, (emit) => runMeshyRetexture({ jobId, values, emit }));
}
