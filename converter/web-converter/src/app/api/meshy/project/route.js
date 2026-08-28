/*
 * ═══════════════════════════════════════════════════════════════
 * Meshy Project Decision Route
 * ═══════════════════════════════════════════════════════════════
 * Path: src/app/api/meshy/project/route.js
 * Purpose: Apply the operator's explicit archive-or-discard review decision.
 */

import {
  archiveMeshyProject,
  discardMeshyProject,
} from "@/lib/meshy/project-storage";

export const runtime = "nodejs";
export const maxDuration = 3600;

export async function POST(request) {
  const { action, jobId } = await request.json();
  if (!jobId || !["archive", "discard"].includes(action)) {
    return Response.json({ error: "Need a valid jobId and action." }, { status: 400 });
  }

  try {
    const result =
      action === "archive"
        ? await archiveMeshyProject(jobId)
        : await discardMeshyProject(jobId);
    return Response.json({ action, job: action === "archive" ? result : null, result });
  } catch (error) {
    return Response.json({ error: error.message }, { status: 409 });
  }
}
