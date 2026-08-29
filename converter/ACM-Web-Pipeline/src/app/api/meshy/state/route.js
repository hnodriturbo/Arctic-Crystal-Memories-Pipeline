/*
 * ══════════════════════════════════════════════════════════════
 * Meshy State Route
 * ══════════════════════════════════════════════════════════════
 * Path: src/app/api/meshy/state/route.js
 * Purpose: Refresh the Meshy panel - config flags, balance, photos, jobs.
 */

import { readMeshyState } from "@/lib/meshy/state";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  return Response.json(await readMeshyState());
}
