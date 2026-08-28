/*
 * ═══════════════════════════════════════════════════════════════
 * Python Runner
 * ═══════════════════════════════════════════════════════════════
 * Path: src/lib/python.js
 * Purpose: Spawn one of the pipelines' Python scripts and relay its output
 *          line by line.
 *
 * Shared by the image pipeline and by the Meshy pipeline's inline clean-up,
 * so both handle chunk boundaries and cancellation the same way.
 */

import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";

/** A venv that was never created is the single most common setup mistake here. */
export function interpreterReady(executable) {
  return Boolean(executable) && existsSync(executable);
}

/**
 * Build a line-at-a-time reader.
 *
 * Python writes in chunks that do not respect newlines, so the tail of a chunk
 * is held back until its newline arrives rather than being emitted as a
 * half-line.
 */
function lineReader(type, onLine) {
  let pending = "";
  const handler = (chunk) => {
    pending += chunk.toString();
    const parts = pending.split(/\r?\n/);
    pending = parts.pop() ?? "";
    for (const line of parts) if (line.trim()) onLine({ type, line });
  };
  handler.flush = () => {
    if (pending.trim()) onLine({ type, line: pending });
    pending = "";
  };
  return handler;
}

/** Run one script to completion, rejecting on any non-zero exit. */
export function runPython(executable, argv, { cwd, onLine, signal } = {}) {
  return new Promise((resolve, reject) => {
    if (!interpreterReady(executable)) {
      reject(
        new Error(
          `No Python interpreter at ${executable}. Create the venv and install requirements.txt.`,
        ),
      );
      return;
    }

    const emit = onLine || (() => {});
    const quote = (part) => (part.includes(" ") ? `"${part}"` : part);
    emit({ type: "cmd", line: [executable, ...argv].map(quote).join(" ") });

    // rich and tqdm wrap to 80 columns off a TTY, which mangles long paths.
    const child = spawn(executable, argv, {
      cwd,
      env: { ...process.env, COLUMNS: "200", PYTHONUNBUFFERED: "1" },
    });

    const onStdout = lineReader("stdout", emit);
    const onStderr = lineReader("stderr", emit);
    child.stdout.on("data", onStdout);
    child.stderr.on("data", onStderr);

    // Kill the script if the browser tab goes away, so no orphan keeps burning CPU.
    const onAbort = () => child.kill();
    signal?.addEventListener("abort", onAbort);

    child.on("error", (error) => {
      signal?.removeEventListener("abort", onAbort);
      reject(error);
    });

    child.on("close", (code) => {
      signal?.removeEventListener("abort", onAbort);
      onStdout.flush();
      onStderr.flush();
      if (code === 0) resolve();
      else reject(new Error(`${path.basename(argv[0])} exited with code ${code}`));
    });
  });
}
