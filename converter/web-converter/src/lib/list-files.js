/*
 * ═══════════════════════════════════════════════════════════════
 * File Listing
 * ═══════════════════════════════════════════════════════════════
 * Path: src/lib/list-files.js
 * Purpose: Walk the converter's input and output trees.
 *
 * Shared by the page (for its first render) and the API route (for
 * refreshes), so both always agree on what counts as a listable file.
 */

import { readdir, stat } from "node:fs/promises";
import path from "node:path";

import { INPUT_DIR, OUTPUT_DIR } from "@/lib/paths";

const SKIP_DIRECTORIES = new Set([".venv", "__pycache__", "node_modules", ".git"]);

/** Walk a tree and return every file as a root-relative record. */
async function walk(root, current = root, collected = []) {
  let entries;
  try {
    entries = await readdir(current, { withFileTypes: true });
  } catch {
    return collected;
  }

  for (const entry of entries) {
    if (entry.name.startsWith(".") || SKIP_DIRECTORIES.has(entry.name)) continue;
    const full = path.join(current, entry.name);

    if (entry.isDirectory()) {
      await walk(root, full, collected);
      continue;
    }
    const info = await stat(full);
    collected.push({
      path: path.relative(root, full).split(path.sep).join("/"),
      name: entry.name,
      extension: path.extname(entry.name).toLowerCase(),
      bytes: info.size,
      modified: info.mtimeMs,
    });
  }
  return collected;
}

/** Both trees, newest first, because the wanted file is nearly always the newest. */
export async function listConverterFiles() {
  const [inputs, outputs] = await Promise.all([walk(INPUT_DIR), walk(OUTPUT_DIR)]);
  const byNewest = (a, b) => b.modified - a.modified;
  return { inputs: inputs.sort(byNewest), outputs: outputs.sort(byNewest) };
}
