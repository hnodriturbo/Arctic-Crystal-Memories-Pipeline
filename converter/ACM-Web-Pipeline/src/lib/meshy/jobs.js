/*
 * ═══════════════════════════════════════════════════════════════
 * Meshy Job Store
 * ═══════════════════════════════════════════════════════════════
 * Path: src/lib/meshy/jobs.js
 * Purpose: One folder per generation, with a manifest beside the models.
 *
 * The manifest is the only record that survives a restart, so it carries
 * everything needed to re-open a job later: the settings used, what Meshy
 * charged, and which files came back.
 */

import { mkdir, readdir, readFile, stat, writeFile } from "node:fs/promises";
import path from "node:path";

import { MESHY_OUTPUT_DIR, resolveInside } from "@/lib/paths";

const MANIFEST = "job.json";

/** Timestamped id with a readable tail, so output/ sorts chronologically by itself. */
export function newJobId(label = "job") {
  const now = new Date();
  const stamp = [
    now.getFullYear(),
    String(now.getMonth() + 1).padStart(2, "0"),
    String(now.getDate()).padStart(2, "0"),
    "-",
    String(now.getHours()).padStart(2, "0"),
    String(now.getMinutes()).padStart(2, "0"),
    String(now.getSeconds()).padStart(2, "0"),
  ].join("");

  const slug =
    String(label)
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 40) || "job";

  return `${stamp}-${slug}`;
}

/** Absolute folder for one job, refusing any id that would escape output/. */
export function jobDir(jobId) {
  const target = resolveInside(MESHY_OUTPUT_DIR, jobId);
  if (!target) throw new Error("Invalid job id.");
  return target;
}

/** Create the folder and drop the first manifest in it. */
export async function createJob(job) {
  const directory = jobDir(job.id);
  await mkdir(directory, { recursive: true });
  await saveJob(job);
  return directory;
}

export async function saveJob(job) {
  const target = path.join(jobDir(job.id), MANIFEST);
  await writeFile(target, JSON.stringify(job, null, 2), "utf8");
  return job;
}

export async function readJob(jobId) {
  try {
    const text = await readFile(path.join(jobDir(jobId), MANIFEST), "utf8");
    return JSON.parse(text);
  } catch {
    return null;
  }
}

/** Every job, newest first. A folder without a manifest is ignored, not an error. */
export async function listJobs() {
  let entries;
  try {
    entries = await readdir(MESHY_OUTPUT_DIR, { withFileTypes: true });
  } catch {
    return [];
  }

  const jobs = [];
  for (const entry of entries) {
    if (!entry.isDirectory() || entry.name.startsWith(".")) continue;
    const job = await readJob(entry.name);
    if (job) jobs.push(job);
  }
  return jobs.sort((a, b) => (b.createdAt || 0) - (a.createdAt || 0));
}

/** Re-read the folder so the manifest's file list matches what is actually on disk. */
export async function indexJobFiles(jobId) {
  const directory = jobDir(jobId);
  let entries;
  try {
    entries = await readdir(directory, { withFileTypes: true });
  } catch {
    return [];
  }

  const files = [];
  for (const entry of entries) {
    if (!entry.isFile() || entry.name === MANIFEST) continue;
    const info = await stat(path.join(directory, entry.name));
    files.push({
      name: entry.name,
      extension: path.extname(entry.name).toLowerCase(),
      bytes: info.size,
      path: `${jobId}/${entry.name}`,
    });
  }
  return files.sort((a, b) => a.name.localeCompare(b.name));
}
