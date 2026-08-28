/*
 * ══════════════════════════════════════════════════════════════
 * Image State Route
 * ══════════════════════════════════════════════════════════════
 * Path: src/app/api/image/state/route.js
 * Purpose: Refresh the image pipeline's photo and result listings.
 */

import { readImageState } from "@/lib/image/state";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  return Response.json(await readImageState());
}
