/*
 * ═══════════════════════════════════════════════════════════════
 * SSE Reader
 * ═══════════════════════════════════════════════════════════════
 * Path: src/lib/read-sse.js
 * Purpose: Consume one of this app's event streams in the browser.
 *
 * fetch is used rather than EventSource because these streams are POSTs with
 * a JSON body, which EventSource cannot send. That means parsing the wire
 * format here - including the keep-alive comment lines, which are not events
 * and must not reach JSON.parse.
 */

/** Read to the end, handing every decoded event to `onEvent`. */
export async function readSse(response, onEvent) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  // Events are separated by a blank line, built here rather than written as a
  // literal so no editor or tool can quietly rewrite the escape.
  const SEPARATOR = String.fromCharCode(10, 10);

  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split(SEPARATOR);
    buffer = chunks.pop() ?? "";

    for (const chunk of chunks) {
      for (const line of chunk.split("\n")) {
        // ": keep-alive" and any other comment line is not an event.
        if (!line.startsWith("data:")) continue;

        const payload = line.slice("data:".length).trim();
        if (!payload) continue;

        try {
          onEvent(JSON.parse(payload));
        } catch {
          // A malformed frame should not abandon the rest of the run.
        }
      }
    }
  }
}
