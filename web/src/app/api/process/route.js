// src/app/api/process/route.js
// POST /api/process — spawns a pipeline Python script and streams
// stdout/stderr back as Server-Sent Events (SSE).
//
// Request JSON:
//   { operation, file, engine, model, target, fidelity, brightness,
//     contrast, sharpness, color }
//
// SSE events:
//   data: {"type":"stdout","line":"..."}
//   data: {"type":"stderr","line":"..."}
//   data: {"type":"done","code":0}
//   data: {"type":"error","message":"..."}

import { spawn } from "child_process";
import path from "path";
import { auth } from "@/auth";

const PIPELINE_ROOT = process.env.PIPELINE_ROOT;

const SCRIPT_MAP = {
  upscale: "upscale.py",
  enhance: "enhance.py",
  remove_bg: "remove_bg.py",
};

const ALLOWED_OPERATIONS = new Set(Object.keys(SCRIPT_MAP));

export async function POST(req) {
  const session = await auth();
  if (!session) return new Response("Unauthorized", { status: 401 });

  const body = await req.json();
  const { operation, file, engine, model, target, fidelity,
          brightness, contrast, sharpness, color } = body;

  if (!ALLOWED_OPERATIONS.has(operation)) {
    return new Response("Invalid operation", { status: 400 });
  }

  const scriptName = SCRIPT_MAP[operation];
  const scriptPath = path.join(PIPELINE_ROOT, "code", scriptName);
  const pythonExe = path.join(PIPELINE_ROOT, ".venv", "Scripts", "python.exe");
  const inputDir = path.join(PIPELINE_ROOT, "input");

  const args = [scriptPath];

  if (file) {
    args.push("--file", path.join(inputDir, file));
  }
  if (engine) args.push("--engine", engine);
  if (model) args.push("--model", model);
  if (target) args.push("--target", String(target));
  if (fidelity != null) args.push("--fidelity", String(fidelity));
  if (brightness != null) args.push("--brightness", String(brightness));
  if (contrast != null) args.push("--contrast", String(contrast));
  if (sharpness != null) args.push("--sharpness", String(sharpness));
  if (color != null) args.push("--color", String(color));

  const stream = new ReadableStream({
    start(controller) {
      const enc = (obj) => `data: ${JSON.stringify(obj)}\n\n`;
      const push = (obj) => controller.enqueue(new TextEncoder().encode(enc(obj)));

      // Emit the exact command so the terminal shows what was run
      push({ type: "cmd", line: [pythonExe, ...args].map((a) => a.includes(" ") ? `"${a}"` : a).join(" ") });

      let proc;
      try {
        proc = spawn(pythonExe, args, { cwd: PIPELINE_ROOT });
      } catch (err) {
        push({ type: "error", message: String(err) });
        controller.close();
        return;
      }

      proc.stdout.on("data", (chunk) => {
        const lines = chunk.toString().split(/\r?\n/).filter(Boolean);
        for (const line of lines) push({ type: "stdout", line });
      });

      proc.stderr.on("data", (chunk) => {
        const lines = chunk.toString().split(/\r?\n/).filter(Boolean);
        for (const line of lines) push({ type: "stderr", line });
      });

      proc.on("error", (err) => {
        push({ type: "error", message: String(err) });
        controller.close();
      });

      proc.on("close", (code) => {
        push({ type: "done", code });
        controller.close();
      });
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      "Connection": "keep-alive",
    },
  });
}
