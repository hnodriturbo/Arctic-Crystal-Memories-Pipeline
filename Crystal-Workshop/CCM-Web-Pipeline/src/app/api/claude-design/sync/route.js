/*
 * ═══════════════════════════════════════════════════════════════
 * Claude Design Sync Route
 * ═══════════════════════════════════════════════════════════════
 * Path: src/app/api/claude-design/sync/route.js
 * Purpose: Move one collection between this machine's disk and ccm-workshop.
 *
 * GET  -> the collections held in the bucket
 * POST -> push one up, or pull one down
 *
 * The same endpoint serves both machines because the direction, not the code,
 * is what differs: the operator's box pushes what it authored, the VPS pulls
 * what it is about to render.
 */

import { validCollection } from "@/lib/claude-design/sync-engine.mjs";
import { designStore } from "@/lib/claude-design/sync-store.mjs";
import { auth } from "@/auth";
import { listRemoteCollections, syncCollection } from "@/lib/claude-design/mirror";
import { workshopR2Configured } from "@/lib/storage/workshop-r2";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// A large collection is a few hundred files over a home connection. The default
// serverless-style timeout would abandon it half way, leaving a partial tree.
export const maxDuration = 900;

export async function GET() {
  if (!(await auth())?.user) return new Response(null, { status: 401 });
  if (!workshopR2Configured()) return Response.json({ collections: [], configured: false });

  try {
    return Response.json({ collections: await listRemoteCollections(), configured: true });
  } catch (error) {
    return Response.json({ error: error.message, collections: [], configured: true }, { status: 502 });
  }
}

export async function POST(request) {
  if (!(await auth())?.user) return new Response(null, { status: 401 });
  if (!workshopR2Configured()) {
    return Response.json({ error: "ccm-workshop is not configured here." }, { status: 503 });
  }

  let body;
  try { body = await request.json(); } catch { return Response.json({ error: "Invalid JSON" }, { status: 400 }); }
  const { direction, collection } = body;
  if (!["sync", "push", "pull", "create"].includes(direction)) return Response.json({ error: "Invalid direction" }, { status: 400 });
  if (!validCollection(collection)) {
    return Response.json({ error: "Which collection?" }, { status: 400 });
  }

  // Collected rather than streamed: the lines are the report, and a sync is
  // one action the operator waits on rather than watches line by line.
  const lines = [];
  const record = (line) => lines.push(line);

  try {
    if (direction === "create") {
      await designStore().createCollection(collection);
      return Response.json({ ok: true, collection });
    }
    const summary = await syncCollection(collection, record);
    return Response.json({ ok: true, direction: "sync", summary, lines });
  } catch (error) {
    return Response.json({ error: error.message, lines }, { status: error.$metadata?.httpStatusCode === 412 ? 409 : 502 });
  }
}
