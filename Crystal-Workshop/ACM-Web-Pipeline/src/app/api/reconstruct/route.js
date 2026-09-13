/**
 * Purpose: Validate a local reconstruction job and stream the shared Python runner.
 * Finished files remain local until a separate storage handoff is requested.
 */
import path from "node:path";
import { realpath, stat, readFile, writeFile } from "node:fs/promises";
import { auth } from '@/auth';
import { createTemporaryWorkspace } from '@/lib/temporary-workspace';
import { RECONSTRUCT } from "@/lib/operations";
import { CODE_DIR, CONVERTER_ROOT, INPUT_DIR, OUTPUT_DIR, PYTHON_EXE, resolveInside } from "@/lib/paths";
import { runPython, interpreterReady } from "@/lib/python";

export const runtime = "nodejs";
export const maxDuration = 3600;

// Keep memory-heavy local reconstruction jobs serial within this Node process.
const reconstructionSlot = globalThis.__acmReconstructionSlot ??= { busy: false };

async function inputFile(relative, extensions) {
  if (typeof relative !== "string") throw new Error("Choose an input file.");
  const candidate = resolveInside(INPUT_DIR, relative);
  if (!candidate || !extensions.includes(path.extname(candidate).toLowerCase())) throw new Error("Unsupported input file.");
  const [root, actual] = await Promise.all([realpath(INPUT_DIR), realpath(candidate)]);
  if (!resolveInside(root, path.relative(root, actual)) || !(await stat(actual)).isFile()) throw new Error("File must be inside input/.");
  return actual;
}

export async function POST(request) {
  if (!(await auth())?.user) return new Response(null, {status:401});
  const origin = request.headers.get('origin');
  if (!origin || new URL(origin).host !== (request.headers.get('x-forwarded-host') || request.headers.get('host'))) return new Response(null, {status:403});
  let args;
  let sourceMetadata = {};
  try {
    const { file, values = {} } = await request.json();
    args = [path.join(CODE_DIR, RECONSTRUCT.script), "--file", await inputFile(file, RECONSTRUCT.accepts)];
    if (file.startsWith('tmp/')) sourceMetadata = JSON.parse(await readFile(path.join(path.dirname(args[2]), '.workshop-temp.json'), 'utf8'));
    if (values.pose_override && (values.stl_method !== 'smooth' || values.color_mode !== 'texture' || values.texture_plane !== 'xy')) throw new Error('Pose overrides require the recommended smooth surface, photo texture and XY projection.');
    for (const field of RECONSTRUCT.fields) {
      const value = values[field.name] ?? field.default;
      if (field.type === "boolean") {
        if (typeof value !== "boolean") throw new Error(`Invalid ${field.label}.`);
        if (value) args.push(field.flag);
      } else if (field.type === "file") {
        if (value) args.push(field.flag, await inputFile(value, field.accepts));
      } else {
        if (field.type === "number" && (!Number.isFinite(value) || (field.step >= 1 && !Number.isInteger(value)) || value < field.min || value > field.max)) throw new Error(`Invalid ${field.label}.`);
        if (field.type === "select" && !field.options.some((option) => (option.value ?? option) === value)) throw new Error(`Invalid ${field.label}.`);
        args.push(field.flag, String(value));
      }
    }
  } catch (error) {
    return Response.json({ error: error.message }, { status: 400 });
  }
  if (!interpreterReady(PYTHON_EXE)) return Response.json({ error: "Converter Python environment is unavailable." }, { status: 503 });
  if (reconstructionSlot.busy) return Response.json({ error: "Another surface is being reconstructed. Wait for it to finish or stop it first." }, { status: 409 });
  reconstructionSlot.busy = true;
  try {
    const temporary = await createTemporaryWorkspace(OUTPUT_DIR, { sourceKeys: sourceMetadata.sourceKeys, sceneFolder: sourceMetadata.sceneFolder });
    args.push('--output-subdir', temporary.relative);
  } catch {
    reconstructionSlot.busy = false;
    return Response.json({error:'Could not create temporary output.'},{status:500});
  }
  const abort = new AbortController();
  const onAbort = () => abort.abort();
  request.signal.addEventListener("abort", onAbort, { once: true });
  if (request.signal.aborted) abort.abort();
  let open = true;
  const stream = new ReadableStream({
    async start(controller) {
      const encoder = new TextEncoder();
      const send = (event) => { if (open) controller.enqueue(encoder.encode(`data: ${JSON.stringify(event)}\n\n`)); };
      try {
        if (abort.signal.aborted) throw new Error("Job cancelled.");
        let completedJob;
        await runPython(PYTHON_EXE, args, {
          cwd: CONVERTER_ROOT, signal: abort.signal,
          onLine(event) {
            if (event.line?.startsWith("ACM_RECONSTRUCT_JOB=")) completedJob = JSON.parse(event.line.slice(20));
            else send(event);
          },
        });
        if (completedJob) {
          completedJob.sourceKeys = sourceMetadata.sourceKeys;
          completedJob.sceneFolder = sourceMetadata.sceneFolder;
          const report = resolveInside(OUTPUT_DIR, completedJob.files.report);
          if (!report) throw new Error('Invalid job report path.');
          await writeFile(report, JSON.stringify(completedJob, null, 2));
          send({type:'result',job:completedJob});
        }
        send({ type: "done", code: 0 });
      } catch (error) {
        send({ type: "error", message: error.message });
        send({ type: "done", code: 1 });
      } finally {
        reconstructionSlot.busy = false;
        request.signal.removeEventListener("abort", onAbort);
        if (open) { open = false; controller.close(); }
      }
    },
    cancel() { open = false; abort.abort(); },
  });
  return new Response(stream, { headers: { "Content-Type": "text/event-stream", "Cache-Control": "no-cache, no-transform" } });
}
