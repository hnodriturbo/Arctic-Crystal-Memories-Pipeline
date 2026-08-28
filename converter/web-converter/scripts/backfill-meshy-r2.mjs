/**
 * File: scripts/backfill-meshy-r2.mjs
 * Purpose:
 *  - Copy existing Meshy job folders into the private R2 source archive.
 *  - Skip objects that are already present with the same byte size.
 */

import { createReadStream } from "node:fs";
import { readFile, readdir, rm, stat, writeFile } from "node:fs/promises";
import path from "node:path";

import { ListObjectsV2Command, PutObjectCommand, S3Client } from "@aws-sdk/client-s3";

const bucket = process.env.R2_PIPELINE_BUCKET_NAME;
const endpoint = process.env.R2_PIPELINE_ENDPOINT;
const accessKeyId = process.env.R2_PIPELINE_ACCESS_KEY_ID;
const secretAccessKey = process.env.R2_PIPELINE_SECRET_ACCESS_KEY;
const meshyRoot = path.resolve(process.env.MESHY_ROOT || path.join(process.cwd(), "..", "meshy-pipeline"));
const outputRoot = path.join(meshyRoot, "output");
const pruneLocal = process.argv.includes("--prune-local");

const contentTypes = {
  ".json": "application/json; charset=utf-8",
  ".glb": "model/gltf-binary",
  ".gltf": "model/gltf+json",
  ".obj": "text/plain; charset=utf-8",
  ".mtl": "text/plain; charset=utf-8",
  ".stl": "model/stl",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".webp": "image/webp",
};

if (!bucket || !endpoint || !accessKeyId || !secretAccessKey) {
  throw new Error("R2_PIPELINE_* environment settings are incomplete.");
}

const client = new S3Client({
  region: "auto",
  endpoint,
  credentials: { accessKeyId, secretAccessKey },
});

async function listExistingObjects() {
  const existing = new Map();
  let continuationToken;
  do {
    const page = await client.send(
      new ListObjectsV2Command({
        Bucket: bucket,
        Prefix: "jobs/",
        ContinuationToken: continuationToken,
      }),
    );
    for (const object of page.Contents || []) existing.set(object.Key, object.Size);
    continuationToken = page.IsTruncated ? page.NextContinuationToken : undefined;
  } while (continuationToken);
  return existing;
}

async function listLocalFiles() {
  const jobs = await readdir(outputRoot, { withFileTypes: true }).catch(() => []);
  const files = [];
  for (const job of jobs) {
    if (!job.isDirectory() || job.name.startsWith(".")) continue;
    const jobDirectory = path.join(outputRoot, job.name);
    const entries = await readdir(jobDirectory, { withFileTypes: true });
    for (const entry of entries) {
      if (!entry.isFile() || entry.name.startsWith(".")) continue;
      const localPath = path.join(jobDirectory, entry.name);
      const info = await stat(localPath);
      files.push({
        jobId: job.name,
        name: entry.name,
        key: `jobs/${job.name}/${entry.name}`,
        localPath,
        bytes: info.size,
        extension: path.extname(entry.name).toLowerCase(),
      });
    }
  }
  return files.sort((a, b) => a.key.localeCompare(b.key));
}

const [existing, localFiles] = await Promise.all([listExistingObjects(), listLocalFiles()]);
let uploaded = 0;
let skipped = 0;
const failures = [];
const confirmed = new Set();

console.log(`Backfilling ${localFiles.length} Meshy file(s) from ${outputRoot}`);

for (const file of localFiles) {
  if (existing.get(file.key) === file.bytes) {
    skipped += 1;
    confirmed.add(file.key);
    continue;
  }

  try {
    await client.send(
      new PutObjectCommand({
        Bucket: bucket,
        Key: file.key,
        Body: createReadStream(file.localPath),
        ContentLength: file.bytes,
        ContentType: contentTypes[file.extension] || "application/octet-stream",
      }),
    );
    uploaded += 1;
    confirmed.add(file.key);
    console.log(`  uploaded ${file.key}`);
  } catch (error) {
    failures.push({ key: file.key, message: error.message });
    console.error(`  failed ${file.key}: ${error.message}`);
  }
}

console.log(
  `MESHY_R2_BACKFILL_COMPLETE uploaded=${uploaded} skipped=${skipped} failed=${failures.length}`,
);

if (pruneLocal) {
  const jobs = new Map();
  for (const file of localFiles) {
    const jobFiles = jobs.get(file.jobId) || [];
    jobFiles.push(file);
    jobs.set(file.jobId, jobFiles);
  }

  let pruned = 0;
  for (const [jobId, files] of jobs) {
    if (!files.every((file) => confirmed.has(file.key))) {
      console.error(`  kept local files for ${jobId}: at least one R2 object is unconfirmed`);
      continue;
    }

    const manifest = files.find((file) => file.name === "job.json");
    if (!manifest) {
      console.error(`  kept local files for ${jobId}: job.json is missing`);
      continue;
    }

    try {
      const job = JSON.parse(await readFile(manifest.localPath, "utf8"));
      job.retentionStatus = "archived";
      job.storage = "r2";
      job.localFilesPruned = true;
      job.archivedAt ||= Date.now();
      job.r2 = {
        bucket,
        error: null,
        objects: files.map((file) => ({ name: file.name, key: file.key, bytes: file.bytes })),
      };
      await writeFile(manifest.localPath, JSON.stringify(job, null, 2), "utf8");
      const manifestInfo = await stat(manifest.localPath);
      await client.send(
        new PutObjectCommand({
          Bucket: bucket,
          Key: manifest.key,
          Body: createReadStream(manifest.localPath),
          ContentLength: manifestInfo.size,
          ContentType: contentTypes[".json"],
        }),
      );
    } catch (error) {
      console.error(`  kept local files for ${jobId}: manifest update failed: ${error.message}`);
      continue;
    }

    for (const file of files) {
      if (file.name === "job.json") continue;
      await rm(file.localPath, { force: true });
      pruned += 1;
    }
  }
  console.log(`MESHY_LOCAL_PRUNE_COMPLETE files=${pruned} manifests_kept=${jobs.size}`);
}

if (failures.length) process.exitCode = 1;
