/*
 * ═══════════════════════════════════════════════════════════════
 * Relief Source Library
 * ═══════════════════════════════════════════════════════════════
 * Path: src/lib/relief/library.js
 * Purpose: Keep every photograph that has ever been relief-built in R2, and
 *          keep the VPS disk empty.
 *
 * The rule this file exists to enforce: the VPS holds working files only for
 * as long as a job needs them. R2 is where anything durable lives. So a
 * source photo is uploaded the moment it is used, the finished job is
 * mirrored, and old job folders are swept off local disk afterwards.
 *
 * Sources are keyed by content hash, so re-running the same photograph a
 * month later reuses its existing object instead of piling up near-duplicates
 * under slightly different filenames.
 */

import { createHash } from "node:crypto";
import { createReadStream } from "node:fs";
import { readdir, rm } from "node:fs/promises";
import path from "node:path";

import { RELIEF_OUTPUT_DIR, availableFileName, RELIEF_INPUT_DIR, safeFileName } from "@/lib/paths";
import {
  downloadObject,
  listObjects,
  presignDownload,
  r2Configured,
  uploadFile,
} from "@/lib/storage/r2";

export const SOURCE_PREFIX = "relief-sources/";
export const JOB_PREFIX = "relief-jobs/";

/*
 * How many finished job folders stay on disk after mirroring. Enough to click
 * through the newest few previews without a round trip to R2, few enough that
 * a 6 GB VPS never fills with GLBs.
 *
 * 0 means never prune, which is what local development wants: comparing six
 * settings of --relief-depth against each other is impossible if the oldest
 * quietly disappears. 0 deliberately does NOT mean "keep zero and delete
 * everything" - that reading would be a foot-gun, so it is the off switch.
 */
const KEEP_LOCAL_JOBS = Number(process.env.RELIEF_KEEP_JOBS ?? 5);

/** Short content hash, so the same photograph always lands on the same key. */
async function contentHash(localPath) {
  const hash = createHash("sha256");
  for await (const chunk of createReadStream(localPath)) hash.update(chunk);
  return hash.digest("hex").slice(0, 12);
}

/**
 * Put a source photograph in the durable library.
 *
 * Never throws. A relief that is already built on disk must not be reported
 * as failed because a bucket was briefly unreachable - the caller logs what
 * came back and carries on, the same contract mirrorJob() uses.
 */
export async function rememberSource(localPath, onLine) {
  const report = onLine || (() => {});
  if (!r2Configured()) return { key: null, skipped: "R2 is not configured" };

  try {
    const digest = await contentHash(localPath);
    const key = `${SOURCE_PREFIX}${digest}-${safeFileName(path.basename(localPath))}`;
    await uploadFile(localPath, key);
    report({ type: "stdout", line: `[r2] source ${key}` });
    return { key };
  } catch (error) {
    report({ type: "stderr", line: `[r2] source upload failed: ${error.message}` });
    return { key: null, error: error.message };
  }
}

/** Mirror one finished job folder. Never throws, for the same reason. */
export async function mirrorReliefJob(jobId, fileNames, onLine) {
  const report = onLine || (() => {});
  if (!r2Configured()) return { mirrored: [], skipped: "R2 is not configured" };

  const mirrored = [];
  for (const name of fileNames) {
    try {
      await uploadFile(path.join(RELIEF_OUTPUT_DIR, jobId, name), `${JOB_PREFIX}${jobId}/${name}`);
      mirrored.push(name);
    } catch (error) {
      report({ type: "stderr", line: `[r2] ${name} failed: ${error.message}` });
    }
  }
  if (mirrored.length) report({ type: "stdout", line: `[r2] mirrored ${mirrored.length} job files` });
  return { mirrored };
}

/**
 * Sweep old job folders off local disk.
 *
 * Only ever removes folders that are already in R2 - a job that failed to
 * mirror stays local, because deleting the only copy of something is not a
 * cleanup, it is data loss.
 */
export async function pruneLocalJobs(onLine) {
  const report = onLine || (() => {});
  if (!r2Configured()) return { removed: [] };

  if (!(KEEP_LOCAL_JOBS > 0)) {
    report({ type: "stdout", line: "[r2] pruning disabled (RELIEF_KEEP_JOBS=0) - every job stays local" });
    return { removed: [] };
  }

  let folders;
  try {
    const entries = await readdir(RELIEF_OUTPUT_DIR, { withFileTypes: true });
    folders = entries
      .filter((entry) => entry.isDirectory() && !entry.name.startsWith("."))
      .map((entry) => entry.name)
      .sort((a, b) => b.localeCompare(a));
  } catch {
    return { removed: [] };
  }

  const stale = folders.slice(KEEP_LOCAL_JOBS);
  const removed = [];

  for (const jobId of stale) {
    try {
      const inBucket = await listObjects(`${JOB_PREFIX}${jobId}/`);
      if (!inBucket.length) continue;
      await rm(path.join(RELIEF_OUTPUT_DIR, jobId), { recursive: true, force: true });
      removed.push(jobId);
    } catch (error) {
      report({ type: "stderr", line: `[r2] could not prune ${jobId}: ${error.message}` });
    }
  }

  if (removed.length) report({ type: "stdout", line: `[r2] pruned ${removed.length} local job folders` });
  return { removed };
}

/** Every photograph in the durable library, newest first. */
export async function listSources() {
  if (!r2Configured()) return { configured: false, sources: [] };

  const objects = await listObjects(SOURCE_PREFIX);
  const sources = objects
    .map((object) => ({
      ...object,
      // Strip the hash prefix back off for display; the key stays authoritative.
      label: object.name.replace(/^[0-9a-f]{12}-/, ""),
    }))
    .sort((a, b) => (b.modified ?? 0) - (a.modified ?? 0));

  return { configured: true, sources };
}

/** A short-lived URL for previewing one library photograph in the browser. */
export async function sourceUrl(key) {
  if (!key.startsWith(SOURCE_PREFIX)) throw new Error("That key is not in the source library.");
  return presignDownload(key);
}

/** Pull one library photograph back onto local disk so a run can use it. */
export async function importSource(key) {
  if (!key.startsWith(SOURCE_PREFIX)) throw new Error("That key is not in the source library.");

  const label = path.posix.basename(key).replace(/^[0-9a-f]{12}-/, "");
  const fileName = await availableFileName(RELIEF_INPUT_DIR, label);
  const destination = path.join(RELIEF_INPUT_DIR, fileName);

  await downloadObject(key, destination);
  return { path: fileName, name: fileName };
}
