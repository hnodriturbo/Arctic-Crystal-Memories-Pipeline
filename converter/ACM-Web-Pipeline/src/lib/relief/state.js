/*
 * ═══════════════════════════════════════════════════════════════
 * Relief Panel State
 * ═══════════════════════════════════════════════════════════════
 * Path: src/lib/relief/state.js
 * Purpose: What the 2.5D tab needs in one read - whether the venv is there,
 *          the photographs waiting, and every relief already built.
 */

import { readFile, readdir, stat } from "node:fs/promises";
import path from "node:path";

import { RELIEF_INPUT_DIR, RELIEF_OUTPUT_DIR, RELIEF_PYTHON_EXE } from "@/lib/paths";
import { PHOTO_TYPES } from "@/lib/relief/catalog";
import { reliefPipelineReady } from "@/lib/relief/chain";

/** Photographs waiting in input/, newest first. */
async function listPhotos(root) {
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

/**
 * Finished relief jobs, newest first.
 *
 * A folder with no readable job.json is skipped rather than reported as
 * broken: an interrupted run leaves exactly that, and it is not something the
 * operator needs a red banner about.
 */
async function listJobs() {
  let entries;
  try {
    entries = await readdir(RELIEF_OUTPUT_DIR, { withFileTypes: true });
  } catch {
    return [];
  }

  const jobs = [];
  for (const entry of entries) {
    if (!entry.isDirectory() || entry.name.startsWith(".")) continue;
    try {
      const manifest = JSON.parse(
        await readFile(path.join(RELIEF_OUTPUT_DIR, entry.name, "job.json"), "utf-8"),
      );
      jobs.push({ ...manifest, jobId: manifest.jobId || entry.name });
    } catch {
      continue;
    }
  }
  return jobs.sort((a, b) => String(b.jobId).localeCompare(String(a.jobId)));
}

export async function readReliefState() {
  const [photos, jobs] = await Promise.all([listPhotos(RELIEF_INPUT_DIR), listJobs()]);

  return {
    ready: reliefPipelineReady(),
    interpreter: RELIEF_PYTHON_EXE,
    photos,
    jobs,
  };
}
