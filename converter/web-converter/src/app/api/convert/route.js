/*
 * ═══════════════════════════════════════════════════════════════
 * Convert Route
 * ═══════════════════════════════════════════════════════════════
 * Path: src/app/api/convert/route.js
 * Purpose: Spawn a pipeline-converter script and stream its console
 *          output back to the browser as Server-Sent Events.
 *
 * Conversions run for minutes on large meshes, so the client watches
 * progress live rather than waiting on a single response.
 */

import { spawn } from "node:child_process";

import { buildArguments, OPERATIONS } from "@/lib/operations";
import { CODE_DIR, CONVERTER_ROOT, INPUT_DIR, PYTHON_EXE, resolveInside } from "@/lib/paths";
import path from "node:path";

export const runtime = "nodejs";
export const maxDuration = 3600;

export async function POST(request) {
  const { operation, file, values } = await request.json();

  const definition = OPERATIONS[operation];
  if (!definition) {
    return Response.json({ error: "Unknown operation" }, { status: 400 });
  }

  // The file must live under input/, so a crafted path cannot reach the rest of the disk.
  const inputPath = file ? resolveInside(INPUT_DIR, file) : null;
  if (!inputPath) {
    return Response.json({ error: "File must sit inside the converter input folder" }, { status: 400 });
  }

  const extension = path.extname(inputPath).toLowerCase();
  if (definition.accepts.length && !definition.accepts.includes(extension)) {
    return Response.json(
      { error: `${definition.label} does not accept ${extension || "that file"}` },
      { status: 400 },
    );
  }

  // File-typed options (the texture image) arrive relative to input/ too, and
  // get the same escape check as the main source file.
  const resolveFile = (relative) => resolveInside(INPUT_DIR, relative);

  const scriptPath = path.join(CODE_DIR, definition.script);
  const args = [scriptPath, ...buildArguments(operation, values, inputPath, resolveFile)];

  const stream = new ReadableStream({
    start(controller) {
      const encoder = new TextEncoder();
      const send = (payload) =>
        controller.enqueue(encoder.encode(`data: ${JSON.stringify(payload)}\n\n`));

      const quote = (part) => (part.includes(" ") ? `"${part}"` : part);
      send({ type: "cmd", line: [PYTHON_EXE, ...args].map(quote).join(" ") });

      let child;
      try {
        // rich wraps to 80 columns off a TTY, which mangles long paths in the log.
        child = spawn(PYTHON_EXE, args, {
          cwd: CONVERTER_ROOT,
          env: { ...process.env, COLUMNS: "200" },
        });
      } catch (error) {
        send({ type: "error", message: String(error) });
        controller.close();
        return;
      }

      // A chunk boundary can land mid-line, so hold the tail back until its newline arrives.
      const makeLineReader = (type) => {
        let pending = "";
        const onData = (chunk) => {
          pending += chunk.toString();
          const parts = pending.split(/\r?\n/);
          pending = parts.pop() ?? "";
          for (const line of parts) {
            if (line.trim()) send({ type, line });
          }
        };
        onData.flush = () => {
          if (pending.trim()) send({ type, line: pending });
          pending = "";
        };
        return onData;
      };

      const onStdout = makeLineReader("stdout");
      const onStderr = makeLineReader("stderr");
      child.stdout.on("data", onStdout);
      child.stderr.on("data", onStderr);

      child.on("error", (error) => {
        send({ type: "error", message: String(error) });
        controller.close();
      });

      child.on("close", (code) => {
        onStdout.flush();
        onStderr.flush();
        send({ type: "done", code });
        controller.close();
      });

      // Kill the script if the browser tab goes away, so no orphan keeps burning CPU.
      request.signal?.addEventListener("abort", () => child.kill());
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
    },
  });
}
