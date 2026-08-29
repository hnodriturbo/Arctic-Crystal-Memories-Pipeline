/*
 * ══════════════════════════════════════════════════════════════
 * Relief State Route
 * ══════════════════════════════════════════════════════════════
 * Path: src/app/api/relief/state/route.js
 * Purpose: Refresh the 2.5D pipeline's photo listing and finished jobs.
 */

import { readReliefState } from "@/lib/relief/state";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  return Response.json(await readReliefState());
}
