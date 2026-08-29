/*
 * ═══════════════════════════════════════════════════════════════
 * Image Panel State
 * ═══════════════════════════════════════════════════════════════
 * Path: src/lib/image/state.js
 * Purpose: What the image pipeline's tab needs in one read - whether the
 *          venv is there, the photos waiting, and the results produced.
 */

import { readdir, stat } from "node:fs/promises";
import path from "node:path";

import { imagePipelineReady } from "@/lib/image/chain";
import { PHOTO_TYPES } from "@/lib/image/catalog";
import { IMAGE_INPUT_DIR, IMAGE_OUTPUT_DIR, IMAGE_PYTHON_EXE } from "@/lib/paths";

/** Images in one folder, newest first - the wanted file is nearly always newest. */
async function listImages(root) {
  let entries;
  try {
    entries = await readdir(root, { withFileTypes: true });
  } catch {
    return [];
  }

  const found = [];
  for (const entry of entries) {
    if (!entry.isFile() || entry.name.startsWith(".")) continue;
    const extension = path.extname(entry.name).toLowerCase();
    if (!PHOTO_TYPES.includes(extension)) continue;

    const info = await stat(path.join(root, entry.name));
    found.push({
      path: entry.name,
      name: entry.name,
      extension,
      bytes: info.size,
      modified: info.mtimeMs,
    });
  }
  return found.sort((a, b) => b.modified - a.modified);
}

export async function readImageState() {
  const [photos, results] = await Promise.all([
    listImages(IMAGE_INPUT_DIR),
    listImages(IMAGE_OUTPUT_DIR),
  ]);

  return {
    ready: imagePipelineReady(),
    interpreter: IMAGE_PYTHON_EXE,
    photos,
    results,
  };
}
