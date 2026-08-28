/*
 * ═══════════════════════════════════════════════════════════════
 * R2 Meshy Library Route
 * ═══════════════════════════════════════════════════════════════
 * Path: src/app/api/r2/library/route.js
 * Purpose: List durable Meshy project runs stored in the private R2 bucket.
 */

import { listMeshyRuns, r2Configured } from "@/lib/storage/r2";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  if (!r2Configured()) {
    return Response.json({ configured: false, jobs: [] });
  }

  try {
    return Response.json({ configured: true, jobs: await listMeshyRuns() });
  } catch (error) {
    return Response.json(
      { configured: true, jobs: [], error: `Could not read the R2 library: ${error.message}` },
      { status: 502 },
    );
  }
}
