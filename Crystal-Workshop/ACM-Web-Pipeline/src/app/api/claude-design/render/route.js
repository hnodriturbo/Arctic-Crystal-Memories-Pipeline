/*
 * ═══════════════════════════════════════════════════════════════
 * Claude Design Render Route
 * ═══════════════════════════════════════════════════════════════
 * Path: src/app/api/claude-design/render/route.js
 * Purpose: Put designs in the render queue, and report what is in it.
 *
 * GET    -> every job, for a tab that has just been opened
 * POST   -> queue one or more designs in a single run
 * DELETE -> drop finished jobs from the list
 *
 * Several designs per request on purpose: a language pair and a desktop/mobile
 * pair is four renders of the same change, and queueing them one at a time is
 * four chances to get one setting wrong.
 */

import { auth } from "@/auth";
import { clearFinished, enqueue, listJobs } from "@/lib/claude-design/render-jobs";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  if (!(await auth())?.user) return new Response(null, { status: 401 });
  return Response.json({ jobs: listJobs() });
}

export async function POST(request) {
  if (!(await auth())?.user) return new Response(null, { status: 401 });

  const body = await request.json();
  const items = Array.isArray(body.items) ? body.items : [];
  if (!items.length) return Response.json({ error: "Nothing was selected." }, { status: 400 });

  const created = [];
  const failed = [];
  for (const item of items) {
    try {
      created.push(
        enqueue({
          ...item,
          collection: item.collection || body.collection,
          fps: body.fps,
          crf: body.crf,
          seconds: body.seconds,
          siteScale: body.siteScale,
          keepChrome: body.keepChrome,
        }),
      );
    } catch (error) {
      failed.push({ item: item.rootRel, error: String(error.message || error) });
    }
  }

  return Response.json({ jobs: created, failed });
}

export async function DELETE() {
  if (!(await auth())?.user) return new Response(null, { status: 401 });
  clearFinished();
  return Response.json({ ok: true });
}
