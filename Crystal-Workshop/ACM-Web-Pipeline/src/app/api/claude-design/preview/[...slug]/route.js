/*
 * ═══════════════════════════════════════════════════════════════
 * Claude Design Preview Route
 * ═══════════════════════════════════════════════════════════════
 * Path: src/app/api/claude-design/preview/[...slug]/route.js
 * Purpose: Serve the design tree over http so it can actually run.
 *
 * Why this exists at all: a `.dc.html` fetches its `.jsx` scenes at runtime,
 * and a browser refuses that from `file://`. Served from here, a design runs
 * properly inside the preview frame instead of being something that can only
 * be read as source.
 *
 * Range requests are supported because Chrome will not seek inside an mp4
 * without them, and the preview frame offers a scrub bar.
 *
 * This serves the operator's browser only. The renderer does not come here:
 * it has no session, and an unauthenticated request is redirected by the auth
 * middleware to the public sign-in URL, where a headless browser meets
 * Cloudflare's bot check. It serves the tree itself on loopback instead.
 */

import fs from "node:fs";
import path from "node:path";
import { Readable } from "node:stream";

import { auth } from "@/auth";
import { DESIGN_ROOT, safeJoin } from "@/lib/claude-design/paths";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".mjs": "text/javascript; charset=utf-8",
  ".jsx": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".gif": "image/gif",
  ".webp": "image/webp",
  ".avif": "image/avif",
  ".mp4": "video/mp4",
  ".webm": "video/webm",
  ".mp3": "audio/mpeg",
  ".wav": "audio/wav",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
  ".ttf": "font/ttf",
  ".otf": "font/otf",
};

export async function GET(request, { params }) {
  if (!(await auth())?.user) return new Response(null, { status: 401 });

  const { slug } = await params;
  // Each segment arrives percent-encoded, and these folder names have spaces.
  const relative = (slug || []).map(decodeURIComponent).join("/");

  const absolute = safeJoin(DESIGN_ROOT, relative);
  if (!absolute || !fs.existsSync(absolute) || !fs.statSync(absolute).isFile()) {
    return new Response("Not found", { status: 404 });
  }

  const type = MIME[path.extname(absolute).toLowerCase()] || "application/octet-stream";
  const size = fs.statSync(absolute).size;
  const range = request.headers.get("range");

  if (range && /^bytes=/.test(range)) {
    const [startRaw, endRaw] = range.replace("bytes=", "").split("-");
    const start = Number(startRaw) || 0;
    const end = endRaw ? Number(endRaw) : size - 1;
    if (start >= size || end >= size || start > end) {
      return new Response(null, { status: 416, headers: { "Content-Range": `bytes */${size}` } });
    }
    return new Response(Readable.toWeb(fs.createReadStream(absolute, { start, end })), {
      status: 206,
      headers: {
        "Content-Type": type,
        "Content-Range": `bytes ${start}-${end}/${size}`,
        "Accept-Ranges": "bytes",
        "Content-Length": String(end - start + 1),
        "Cache-Control": "private, no-store",
      },
    });
  }

  return new Response(Readable.toWeb(fs.createReadStream(absolute)), {
    headers: {
      "Content-Type": type,
      "Content-Length": String(size),
      "Accept-Ranges": "bytes",
      "Cache-Control": "private, no-store",
    },
  });
}
