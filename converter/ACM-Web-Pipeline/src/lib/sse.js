/*
 * ═══════════════════════════════════════════════════════════════
 * Server-Sent Events
 * ═══════════════════════════════════════════════════════════════
 * Path: src/lib/sse.js
 * Purpose: Wrap a long-running job in an event stream the browser can watch.
 *
 * Both pipelines run for minutes - a Python sampler over a large mesh, a
 * Meshy generation queue - so both report progress as it happens rather than
 * leaving the tab on one pending fetch.
 */

const HEADERS = {
  "Content-Type": "text/event-stream",
  "Cache-Control": "no-cache, no-transform",
  Connection: "keep-alive",
  // nginx buffers proxied responses by default, which holds every progress
  // line back until the job ends. This turns that off for the stream only.
  "X-Accel-Buffering": "no",
};

// A Meshy generation can sit at 99% for a minute or more, and a point-cloud
// sampler can run for several without printing. Idle that long and Cloudflare
// or nginx will close the connection, so a comment line goes out on a timer -
// it is ignored by the EventSource parser but keeps the socket alive.
const HEARTBEAT_MS = 15000;

/**
 * Run `work` inside an SSE response.
 *
 * `work` receives `emit` for progress and an AbortSignal that fires when the
 * browser tab goes away, so nothing keeps burning CPU or credits unwatched.
 * A thrown error is delivered as one final error event rather than tearing
 * the connection down without explanation.
 */
export function sseResponse(request, work) {
  const stream = new ReadableStream({
    async start(controller) {
      const encoder = new TextEncoder();
      let closed = false;

      const emit = (payload) => {
        if (closed) return;
        try {
          controller.enqueue(encoder.encode(`data: ${JSON.stringify(payload)}\n\n`));
        } catch {
          closed = true;
        }
      };

      const abort = new AbortController();
      const onAbort = () => abort.abort();
      request.signal?.addEventListener("abort", onAbort);

      const heartbeat = setInterval(() => {
        if (closed) return;
        try {
          controller.enqueue(encoder.encode(": keep-alive\n\n"));
        } catch {
          closed = true;
        }
      }, HEARTBEAT_MS);

      let code = 0;
      try {
        await work(emit, abort.signal);
      } catch (error) {
        code = 1;
        emit({ type: "error", message: error?.message || String(error) });
      } finally {
        clearInterval(heartbeat);
        request.signal?.removeEventListener("abort", onAbort);
        emit({ type: "done", code });
        closed = true;
        try {
          controller.close();
        } catch {
          // Already closed by the client disconnecting; nothing to do.
        }
      }
    },
  });

  return new Response(stream, { headers: HEADERS });
}
