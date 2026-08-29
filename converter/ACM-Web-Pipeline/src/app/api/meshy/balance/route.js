/*
 * ═══════════════════════════════════════════════════════════════
 * Meshy Balance Route
 * ═══════════════════════════════════════════════════════════════
 * Path: src/app/api/meshy/balance/route.js
 * Purpose: Keep the external credit lookup off the local job-listing path.
 */

import { readMeshyBalance } from "@/lib/meshy/state";

export const dynamic = "force-dynamic";

export async function GET() {
  return Response.json(await readMeshyBalance());
}
