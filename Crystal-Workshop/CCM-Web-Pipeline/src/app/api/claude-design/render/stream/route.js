/*
 * ═══════════════════════════════════════════════════════════════
 * Claude Design Render Stream
 * ═══════════════════════════════════════════════════════════════
 * Path: src/app/api/claude-design/render/stream/route.js
 * Purpose: Live progress and console output for the render queue.
 *
 * Server-Sent Events rather than polling: a render runs for tens of minutes
 * and produces a line a second. One open connection carries all of it, and the
 * browser reconnects by itself when `next dev` restarts underneath it.
 *
 * The first thing sent is a snapshot, so a tab opened halfway through a render
 * is never blank while it waits for the next line.
 */

import { auth } from "@/auth";
import { listJobs, subscribe } from "@/lib/claude-design/render-jobs";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// nginx and Cloudflare will close a connection that says nothing for long
// enough, and a slow frame can take a while. A comment line keeps it open and
// is ignored by the EventSource parser.
const HEARTBEAT_MS = 20000;

export async function GET() {
  if (!(await auth())?.user) return new Response(null, { status: 401 });

  const encoder = new TextEncoder();

  // Declared out here because start() runs before the variable would be assigned.
  let cleanup = () => {};

  const stream = new ReadableStream({
    start(controller) {
      const send = (payload) => {
        try {
          controller.enqueue(encoder.encode(`data: ${JSON.stringify(payload)}\n\n`));
        } catch {
          cleanup();
        }
      };

      send({ type: "snapshot", jobs: listJobs() });
      const unsubscribe = subscribe(send);

      const heartbeat = setInterval(() => {
        try {
          controller.enqueue(encoder.encode(": keep-alive\n\n"));
        } catch {
          cleanup();
        }
      }, HEARTBEAT_MS);

      cleanup = () => {
        clearInterval(heartbeat);
        unsubscribe();
      };
    },
    cancel() {
      cleanup();
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      // nginx buffers proxied responses by default, which holds every progress
      // line back until the render ends. This turns that off for the stream.
      "X-Accel-Buffering": "no",
    },
  });
}
