/*
 * ═══════════════════════════════════════════════════════════════
 * Pipeline Paths
 * ═══════════════════════════════════════════════════════════════
 * Path: src/lib/paths.js
 * Purpose: Resolve the four checkouts this app drives and keep every
 *          filesystem access fenced inside one of them.
 *
 * Four roots, because the app spans four isolated pipelines: image
 * preparation, the Meshy workspace, 2.5D relief building, and point-cloud
 * conversion.
 */

import { access } from "node:fs/promises";
import path from "node:path";

// Sibling folders need no configuration in a normal checkout - the whole
// converter/ tree moves to the VPS together, so these stay correct there too.
const DEFAULT_CONVERTER_ROOT = path.resolve(process.cwd(), "..", "pipeline-converter");
const DEFAULT_MESHY_ROOT = path.resolve(process.cwd(), "..", "meshy-pipeline");
const DEFAULT_IMAGE_ROOT = path.resolve(process.cwd(), "..", "image-pipeline");
const DEFAULT_RELIEF_ROOT = path.resolve(process.cwd(), "..", "2.5D-pipeline");

// turbopackIgnore keeps the bundler from tracing the whole converter tree into the build.
export const CONVERTER_ROOT = path.resolve(
  /*turbopackIgnore: true*/ process.env.CONVERTER_ROOT || DEFAULT_CONVERTER_ROOT,
);

export const INPUT_DIR = path.join(CONVERTER_ROOT, "input");
export const UPLOAD_DIR = path.join(INPUT_DIR, "uploads");
export const OUTPUT_DIR = path.join(CONVERTER_ROOT, "output");
export const CODE_DIR = path.join(CONVERTER_ROOT, "code");

export const MESHY_ROOT = path.resolve(
  /*turbopackIgnore: true*/ process.env.MESHY_ROOT || DEFAULT_MESHY_ROOT,
);

// Source photos, cleaned intermediates, and one folder per finished job.
export const MESHY_INPUT_DIR = path.join(MESHY_ROOT, "input");
export const MESHY_WORK_DIR = path.join(MESHY_ROOT, "work");
export const MESHY_OUTPUT_DIR = path.join(MESHY_ROOT, "output");

export const IMAGE_ROOT = path.resolve(
  /*turbopackIgnore: true*/ process.env.IMAGE_PIPELINE_ROOT || DEFAULT_IMAGE_ROOT,
);

export const IMAGE_INPUT_DIR = path.join(IMAGE_ROOT, "input");
export const IMAGE_OUTPUT_DIR = path.join(IMAGE_ROOT, "output");
export const IMAGE_CODE_DIR = path.join(IMAGE_ROOT, "code");

export const RELIEF_ROOT = path.resolve(
  /*turbopackIgnore: true*/ process.env.RELIEF_PIPELINE_ROOT || DEFAULT_RELIEF_ROOT,
);

// One folder per relief job, holding the depth PNG, the GLB the browser
// previews and the OBJ the point sampler consumes.
export const RELIEF_INPUT_DIR = path.join(RELIEF_ROOT, "input");
export const RELIEF_OUTPUT_DIR = path.join(RELIEF_ROOT, "output");
export const RELIEF_CODE_DIR = path.join(RELIEF_ROOT, "code");

// Real crystal blank geometry imported from a local Cockpit 3D install by
// code/import_blanks.py. Internal preview use - see that script's header.
export const RELIEF_BLANKS_DIR = path.join(RELIEF_ROOT, "blanks");

/** Windows venvs keep interpreters in Scripts/, POSIX ones in bin/. */
function venvPython(root) {
  return path.join(
    root,
    ".venv",
    process.platform === "win32" ? "Scripts" : "bin",
    process.platform === "win32" ? "python.exe" : "python",
  );
}

export const PYTHON_EXE = process.env.CONVERTER_PYTHON || venvPython(CONVERTER_ROOT);
export const MESHY_PYTHON_EXE = process.env.MESHY_PYTHON || venvPython(MESHY_ROOT);

// A separate interpreter on purpose: the converter venv is numpy/scipy/ezdxf,
// the image one carries rembg and onnxruntime. Keeping them apart is what lets
// the VPS install the image side CPU-only without touching the converter.
export const IMAGE_PYTHON_EXE = process.env.IMAGE_PIPELINE_PYTHON || venvPython(IMAGE_ROOT);

// A fourth interpreter, for the same reason again: the relief venv carries a
// modern torch plus transformers, while the image one is pinned to torch
// 2.1.2 / numpy 1.26.4 for basicsr. They cannot share an environment.
export const RELIEF_PYTHON_EXE = process.env.RELIEF_PIPELINE_PYTHON || venvPython(RELIEF_ROOT);

/** Reject any path that escapes its allowed root, so a crafted name cannot read the wider disk. */
export function resolveInside(root, relativePath) {
  const target = path.resolve(root, relativePath);
  if (target !== root && !target.startsWith(root + path.sep)) {
    return null;
  }
  return target;
}

/** Strip directory parts and anything awkward, leaving a name safe to write to disk. */
export function safeFileName(name) {
  const base = path.basename(String(name || "").replace(/\\/g, "/"));
  const cleaned = base
    .replace(/[<>:"|?*]/g, "_")
    .split("")
    .filter((character) => character.charCodeAt(0) >= 32)
    .join("")
    .replace(/[ \t]+/g, "_")
    .trim();
  return cleaned || `upload-${Date.now()}`;
}

/** Preserve existing inputs by adding -2, -3, ... before the extension. */
export async function availableFileName(directory, requestedName) {
  const safe = safeFileName(requestedName);
  const extension = path.extname(safe);
  const stem = path.basename(safe, extension);

  for (let index = 1; index <= 9999; index += 1) {
    const candidate = index === 1 ? safe : `${stem}-${index}${extension}`;
    try {
      await access(path.join(directory, candidate));
    } catch (error) {
      if (error?.code === "ENOENT") return candidate;
      throw error;
    }
  }
  throw new Error(`Could not reserve a unique name for ${safe}.`);
}
