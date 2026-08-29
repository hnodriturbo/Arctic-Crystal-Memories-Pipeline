/*
 * ═══════════════════════════════════════════════════════════════
 * Relief Library URL Route
 * ═══════════════════════════════════════════════════════════════
 * Path: src/app/api/relief/library/url/route.js
 * Purpose: Hand the browser a short-lived presigned URL for one library
 *          photograph, so the viewer reads it straight from R2.
 *
 * A presigned URL rather than a proxy: the object goes from R2 to the browser
 * instead of through this box twice, and nothing lands on VPS disk to be
 * cleaned up afterwards.
 */

import { sourceUrl } from "@/lib/relief/library";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(request) {
  const key = new URL(request.url).searchParams.get("key");
  if (!key) return Response.json({ error: "Need a key" }, { status: 400 });

  try {
    return Response.json({ url: await sourceUrl(key) });
  } catch (error) {
    return Response.json({ error: error.message }, { status: 400 });
  }
}
