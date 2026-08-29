/*
 * ═══════════════════════════════════════════════════════════════
 * Meshy Project Storage Decisions
 * ═══════════════════════════════════════════════════════════════
 * Path: src/lib/meshy/project-storage.js
 * Purpose: Archive one reviewed project to R2 or discard its VPS workspace.
 *          Local files are never removed until every R2 object is verified.
 */

import { rm, stat } from "node:fs/promises";
import path from "node:path";

import { indexJobFiles, jobDir, readJob, saveJob } from "@/lib/meshy/jobs";
import { listJobObjects, r2Configured, uploadFile } from "@/lib/storage/r2";

const MANIFEST_NAME = "job.json";

/** Archive every job file, verify object sizes, then retain only the manifest locally. */
export async function archiveMeshyProject(jobId) {
  if (!r2Configured()) throw new Error("R2 is not configured on this server.");

  const job = await readJob(jobId);
  if (!job) throw new Error("Meshy project not found.");
  if (job.status !== "succeeded") throw new Error("Only a successful project can be archived.");
  if (job.retentionStatus !== "pending") {
    throw new Error("This project is not waiting for an archive decision.");
  }
  if (job.retextureStatus === "running") {
    throw new Error("Wait for the active Retexture task before archiving this project.");
  }

  const directory = jobDir(jobId);
  const files = await indexJobFiles(jobId);
  if (!files.some((file) => file.extension === ".glb")) {
    throw new Error("A reviewed project must contain a GLB before it can be archived.");
  }

  job.retentionStatus = "archiving";
  job.storage = "vps-review";
  await saveJob(job);

  const objects = [];

  try {
    for (const file of files) {
      const key = `jobs/${jobId}/${file.name}`;
      await uploadFile(path.join(directory, file.name), key);
      objects.push({ name: file.name, key, bytes: file.bytes });
    }

    const manifestKey = `jobs/${jobId}/${MANIFEST_NAME}`;
    job.r2 = {
      bucket: process.env.R2_PIPELINE_BUCKET_NAME,
      objects: [...objects, { name: MANIFEST_NAME, key: manifestKey }],
      error: null,
    };
    job.retentionStatus = "archived";
    job.storage = "r2";
    job.localFilesPruned = false;
    job.archivedAt = Date.now();
    await saveJob(job);

    const manifestPath = path.join(directory, MANIFEST_NAME);
    const manifestInfo = await stat(manifestPath);
    await uploadFile(manifestPath, manifestKey);

    const remote = new Map((await listJobObjects(jobId)).map((item) => [item.key, item.bytes]));
    const expected = [...objects, { key: manifestKey, bytes: manifestInfo.size }];
    const mismatch = expected.find((item) => remote.get(item.key) !== item.bytes);
    if (mismatch) throw new Error(`R2 verification failed for ${mismatch.key}.`);
  } catch (error) {
    // A failure before remote verification leaves all model files local and
    // puts the decision back in front of the operator. Partially uploaded R2
    // objects are harmless and will be overwritten on the next attempt.
    job.retentionStatus = "pending";
    job.storage = "vps-review";
    job.localFilesPruned = false;
    job.r2 = { ...(job.r2 || {}), error: error.message };
    await saveJob(job).catch(() => {});
    throw error;
  }

  // Remote verification is the irreversible boundary: from here onward R2 is
  // the source of truth even if a local file cannot be removed immediately.
  const cleanupFailures = [];
  for (const file of files) {
    try {
      await rm(path.join(directory, file.name), { force: true });
    } catch (error) {
      cleanupFailures.push(`${file.name}: ${error.message}`);
    }
  }

  job.localFilesPruned = cleanupFailures.length === 0;
  job.r2 = {
    ...job.r2,
    error:
      cleanupFailures.length === 0
        ? null
        : `R2 is verified, but VPS cleanup needs attention: ${cleanupFailures.join("; ")}`,
  };
  await saveJob(job);

  // Refresh the remote manifest after cleanup so archived projects accurately
  // report whether any large local files remain on the VPS.
  const manifestPath = path.join(directory, MANIFEST_NAME);
  try {
    await uploadFile(manifestPath, `jobs/${jobId}/${MANIFEST_NAME}`);
  } catch (error) {
    job.r2.error = `Project files are safe in R2, but the final manifest refresh failed: ${error.message}`;
    await saveJob(job);
  }
  return job;
}

/** Discard an unarchived project and every file in its fenced job directory. */
export async function discardMeshyProject(jobId) {
  const job = await readJob(jobId);
  if (!job) throw new Error("Meshy project not found.");
  if (job.retentionStatus === "archived" || job.storage === "r2") {
    throw new Error("Archived R2 projects cannot be discarded through the VPS cleanup action.");
  }

  const directory = jobDir(jobId);
  await rm(directory, { recursive: true, force: true });
  return { id: jobId, discarded: true };
}
