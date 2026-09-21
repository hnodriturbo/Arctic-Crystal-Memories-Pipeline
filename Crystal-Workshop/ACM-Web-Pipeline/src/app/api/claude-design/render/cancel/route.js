/*
 * ═══════════════════════════════════════════════════════════════
 * Claude Design Render Cancel
 * ═══════════════════════════════════════════════════════════════
 * Path: src/app/api/claude-design/render/cancel/route.js
 * Purpose: Stop one render, queued or already running.
 *
 * Worth having as a real button rather than leaving the operator to wait: a
 * wrong resolution is obvious within the first few seconds, and the rest of an
 * hour-long render is then pure waste on a machine that also serves the shop.
 */

import { auth } from "@/auth";
import { cancel } from "@/lib/claude-design/render-jobs";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(request) {
  if (!(await auth())?.user) return new Response(null, { status: 401 });

  const { id } = await request.json();
  if (!id) return Response.json({ error: "Which job?" }, { status: 400 });

  // False means the job had already finished - not an error worth a banner.
  return Response.json({ stopped: cancel(id) });
}
