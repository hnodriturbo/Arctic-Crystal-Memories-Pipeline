/*
 * ═══════════════════════════════════════════════════════════════
 * Claude Design Library Route
 * ═══════════════════════════════════════════════════════════════
 * Path: src/app/api/claude-design/library/route.js
 * Purpose: Everything the animations page needs, in one request.
 *
 * One call rather than four, because the filesystem scan is cheap and the page
 * cannot draw anything useful until it knows all of it: which collections
 * exist locally, which videos are already in R2, and whether this machine can
 * render at all. Three separate loading states for one screen is worse.
 */

import { spawnSync } from "node:child_process";

import { auth } from "@/auth";
import { listCollections, listExported, rootPresent } from "@/lib/claude-design/scan";
import { DESIGN_ROOT, R2_VIDEO_PREFIX } from "@/lib/claude-design/paths";
import { listObjects, workshopR2Configured } from "@/lib/storage/workshop-r2";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/**
 * Whether a render could actually start here.
 *
 * Checked rather than assumed, so a missing ffmpeg is a sentence on the page
 * before anything is queued instead of a job that fails a minute later. The
 * probe is cheap and the answer can change without a redeploy, which is why it
 * is not cached.
 */
async function renderCapability() {
  const probe = spawnSync("ffmpeg", ["-version"], {
    stdio: "ignore",
    shell: process.platform === "win32",
  });
  const ffmpeg = !probe.error && probe.status === 0;

  let chromium = false;
  try {
    // Asking for the path is enough: puppeteer throws here when no browser was
    // ever downloaded for it, which is exactly the case worth reporting.
    const puppeteer = await import("puppeteer");
    chromium = Boolean((puppeteer.default || puppeteer).executablePath());
  } catch {
    chromium = false;
  }

  return { ffmpeg, chromium, ready: ffmpeg && chromium };
}

/** Group rendered objects into one entry per video, pairing each with its poster. */
function groupVideos(objects) {
  const videos = new Map();

  for (const object of objects) {
    const rest = object.key.slice(R2_VIDEO_PREFIX.length);
    const slash = rest.indexOf("/");
    if (slash < 0) continue;

    const collection = rest.slice(0, slash);
    const fileName = rest.slice(slash + 1);
    const stem = fileName.replace(/\.(mp4|jpg)$/i, "");
    const id = `${collection}/${stem}`;
    const entry = videos.get(id) || { id, collection, name: stem, key: null, posterKey: null, bytes: 0, modified: 0 };

    if (object.extension === ".mp4") {
      entry.key = object.key;
      entry.bytes = object.bytes;
      entry.modified = object.modified || 0;
    } else if (object.extension === ".jpg") {
      entry.posterKey = object.key;
    }
    videos.set(id, entry);
  }

  return [...videos.values()]
    .filter((video) => video.key)
    .sort((a, b) => b.modified - a.modified);
}

export async function GET() {
  if (!(await auth())?.user) return new Response(null, { status: 401 });

  const local = rootPresent();
  let videos = [];
  let r2Error = null;

  if (workshopR2Configured()) {
    try {
      videos = groupVideos(await listObjects(R2_VIDEO_PREFIX));
    } catch (error) {
      r2Error = error.message;
    }
  }

  return Response.json(
    {
      root: DESIGN_ROOT,
      rootPresent: local,
      collections: local ? listCollections() : [],
      exported: local ? listExported() : [],
      videos,
      r2Configured: workshopR2Configured(),
      r2Error,
      capability: await renderCapability(),
    },
    { headers: { "Cache-Control": "private, no-store" } },
  );
}
