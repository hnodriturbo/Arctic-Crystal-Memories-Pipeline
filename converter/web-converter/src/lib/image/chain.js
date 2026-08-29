/*
 * ═══════════════════════════════════════════════════════════════
 * Image Chain
 * ═══════════════════════════════════════════════════════════════
 * Path: src/lib/image/chain.js
 * Purpose: Run a photo through the clean-up stages it asked for, keeping
 *          every intermediate.
 *
 * The one place either pipeline goes to clean a photo: the image tab runs it
 * into image-pipeline/output/, the Meshy tab runs it into meshy-pipeline/work/
 * on the way to a generation. Same stages, same order, same results.
 */

import { mkdir } from "node:fs/promises";
import path from "node:path";

import { buildStageArgs, selectedStages } from "@/lib/image/catalog";
import { IMAGE_CODE_DIR, IMAGE_PYTHON_EXE, IMAGE_ROOT } from "@/lib/paths";
import { interpreterReady, runPython } from "@/lib/python";

// Torch/ONNX jobs can each hold more than 1 GB of RAM. One process-wide queue
// protects the 6 GB VPS when two browser tabs request image work together.
let imageQueue = Promise.resolve();

async function withImageSlot(task) {
  const previous = imageQueue;
  let release;
  imageQueue = new Promise((resolve) => {
    release = resolve;
  });
  await previous;
  try {
    return await task();
  } finally {
    release();
  }
}

/** Whether this machine can clean photos at all. */
export function imagePipelineReady() {
  return interpreterReady(IMAGE_PYTHON_EXE);
}

/**
 * Run the chain.
 *
 * Every stage writes a real file rather than piping, so a run that fails
 * halfway still leaves its earlier stages on disk to look at. Returns the
 * final image plus every intermediate, oldest first.
 */
export async function runImageChain({ source, destinationDir, values, emit, signal }) {
  const stages = selectedStages(values);
  const report = emit || (() => {});

  if (!stages.length) {
    return { finalPath: source, produced: [] };
  }
  if (!imagePipelineReady()) {
    throw new Error(
      `No image-pipeline venv at ${IMAGE_PYTHON_EXE}. Run: python -m venv .venv && pip install -r requirements.txt`,
    );
  }

  return withImageSlot(async () => {
    await mkdir(destinationDir, { recursive: true });

    const stem = path.basename(source, path.extname(source));
    const produced = [];
    let current = source;

    for (const [index, stage] of stages.entries()) {
      if (signal?.aborted) throw new Error("Cancelled.");

      // Numbered so the folder reads in running order even when a stage is skipped.
      const output = path.join(destinationDir, `${stem}-${index + 1}-${stage.id}.png`);
      report({ type: "step", line: `${stage.label} (${stage.script})` });

      await runPython(
        IMAGE_PYTHON_EXE,
        [path.join(IMAGE_CODE_DIR, stage.script), ...buildStageArgs(stage.id, values, current, output)],
        { cwd: IMAGE_ROOT, onLine: report, signal },
      );

      produced.push(output);
      current = output;
    }

    return { finalPath: current, produced };
  });
}
