/*
 * ═══════════════════════════════════════════════════════════════
 * R2 Pipeline Library Route
 * ═══════════════════════════════════════════════════════════════
 * Path: src/app/api/r2/library/route.js
 * Purpose: List durable Meshy sources and converter outputs stored in private R2.
 */

import { listConverterRuns, listMeshyRuns, r2Configured } from "@/lib/storage/r2";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  if (!r2Configured()) {
    return Response.json({ configured: false, jobs: [], converterJobs: [] });
  }

  try {
    const [jobs, converterJobs] = await Promise.all([listMeshyRuns(), listConverterRuns()]);
    return Response.json({ configured: true, jobs, converterJobs });
  } catch (error) {
    return Response.json(
      { configured: true, jobs: [], converterJobs: [], error: `Could not read the R2 library: ${error.message}` },
      { status: 502 },
    );
  }
}
