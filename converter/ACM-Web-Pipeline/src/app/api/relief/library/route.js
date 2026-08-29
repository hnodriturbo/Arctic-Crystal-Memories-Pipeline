/*
 * ═══════════════════════════════════════════════════════════════
 * Relief Source Library Route
 * ═══════════════════════════════════════════════════════════════
 * Path: src/app/api/relief/library/route.js
 * Purpose: List the durable photo library in R2, and pull one back onto local
 *          disk when a run wants it.
 *
 * GET lists; POST imports. Local disk is a workspace, so importing is how a
 * library photograph becomes runnable again after the VPS was swept.
 */

import { importSource, listSources } from "@/lib/relief/library";
import { r2Configured } from "@/lib/storage/r2";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  try {
    return Response.json(await listSources());
  } catch (error) {
    return Response.json(
      { configured: r2Configured(), sources: [], error: `Could not read the library: ${error.message}` },
      { status: 502 },
    );
  }
}

export async function POST(request) {
  const { key } = await request.json();
  if (!key) return Response.json({ error: "Need a key" }, { status: 400 });

  try {
    return Response.json(await importSource(key));
  } catch (error) {
    return Response.json({ error: error.message }, { status: 400 });
  }
}
