/*
 * ═══════════════════════════════════════════════════════════════
 * Claude Design Videos Route
 * ═══════════════════════════════════════════════════════════════
 * Path: src/app/api/claude-design/videos/route.js
 * Purpose: Play and download finished videos straight out of ccm-workshop.
 *
 * GET    ?key=… &download=1  -> a short-lived URL for that object
 * DELETE                     -> remove one video and its poster
 *
 * A redirect to a presigned URL rather than streaming the file through this
 * server: the VPS has no reason to carry a hundred megabytes twice, and
 * Cloudflare is closer to whoever is watching. The bucket stays private -
 * the URL is good for that one object and expires within the hour.
 */

import path from "node:path";

import { auth } from "@/auth";
import { allowedDesignKey } from "@/lib/claude-design/paths";
import { headObject, presignRead, removeObject, workshopR2Configured } from "@/lib/storage/workshop-r2";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(request) {
  if (!(await auth())?.user) return new Response(null, { status: 401 });
  if (!workshopR2Configured()) {
    return Response.json({ error: "ccm-workshop is not configured here." }, { status: 503 });
  }

  const params = new URL(request.url).searchParams;
  const key = params.get("key");
  if (!allowedDesignKey(key) || key.endsWith("/")) {
    return Response.json({ error: "That is not a Claude Design object." }, { status: 400 });
  }

  const download = params.get("download") === "1";

  try {
    // `redirect` is what lets a <video> element point straight at this route:
    // the browser follows it to R2 and does its own range requests from there.
    const url = await presignRead(key, { download, fileName: path.posix.basename(key) });
    return Response.redirect(url, 302);
  } catch {
    return Response.json({ error: "Could not reach R2. Try again." }, { status: 502 });
  }
}

export async function DELETE(request) {
  if (!(await auth())?.user) return new Response(null, { status: 401 });
  if (!workshopR2Configured()) {
    return Response.json({ error: "ccm-workshop is not configured here." }, { status: 503 });
  }

  const { key } = await request.json();
  if (!allowedDesignKey(key) || !/\.mp4$/i.test(key)) {
    return Response.json({ error: "Only a rendered video can be deleted here." }, { status: 400 });
  }

  try {
    await removeObject(key);

    // The poster is derived from the video, so it goes with it rather than
    // being left behind as an orphan thumbnail of something that is gone.
    const posterKey = key.replace(/\.mp4$/i, ".jpg");
    if (await headObject(posterKey)) await removeObject(posterKey);

    return Response.json({ ok: true });
  } catch (error) {
    return Response.json({ error: error.message }, { status: 502 });
  }
}
