/*
 * ═══════════════════════════════════════════════════════════════
 * R2 Storage
 * ═══════════════════════════════════════════════════════════════
 * Path: src/lib/storage/r2.js
 * Purpose: Store finished work in the pipeline's durable private R2 archive.
 *
 * The workspace folders on disk stay the source of truth while a job runs -
 * they are what the Python scripts read and write. R2 is the durable source
 * archive that outlives the server: rebuild the VPS, and the models remain.
 *
 * Bucket: acm-pipeline-eu, EU jurisdiction, private. Nothing here is public,
 * so downloads go out as short-lived presigned URLs rather than a custom
 * domain the way product images do.
 */

import { createReadStream, createWriteStream } from "node:fs";
import { mkdir, rm, stat } from "node:fs/promises";
import path from "node:path";
import { pipeline } from "node:stream/promises";

import {
  DeleteObjectCommand,
  GetObjectCommand,
  ListObjectsV2Command,
  PutObjectCommand,
  S3Client,
} from "@aws-sdk/client-s3";
import { getSignedUrl } from "@aws-sdk/s3-request-presigner";

const BUCKET = process.env.R2_PIPELINE_BUCKET_NAME;

// Content types matter here for the same reason they do on /api/file: a GLB
// served as octet-stream will not open in the viewer.
const CONTENT_TYPES = {
  ".glb": "model/gltf-binary",
  ".gltf": "model/gltf+json",
  ".obj": "text/plain; charset=utf-8",
  ".mtl": "text/plain; charset=utf-8",
  ".dxf": "application/dxf",
  ".ply": "application/octet-stream",
  ".stl": "model/stl",
  ".dae": "model/vnd.collada+xml",
  ".usd": "application/octet-stream",
  ".usda": "text/plain; charset=utf-8",
  ".usdc": "application/octet-stream",
  ".usdz": "model/vnd.usdz+zip",
  ".fbx": "application/octet-stream",
  ".3mf": "model/3mf",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".webp": "image/webp",
  ".json": "application/json; charset=utf-8",
  ".md": "text/markdown; charset=utf-8",
  ".zip": "application/zip",
};

let client = null;

/** Optional feature: without credentials the app simply keeps everything local. */
export function r2Configured() {
  return Boolean(
    process.env.R2_PIPELINE_ENDPOINT &&
      process.env.R2_PIPELINE_ACCESS_KEY_ID &&
      process.env.R2_PIPELINE_SECRET_ACCESS_KEY &&
      BUCKET,
  );
}

function getClient() {
  if (!r2Configured()) {
    throw new Error("R2 is not configured. Add the R2_PIPELINE_* keys to the environment.");
  }
  client ||= new S3Client({
    region: "auto",
    endpoint: process.env.R2_PIPELINE_ENDPOINT,
    credentials: {
      accessKeyId: process.env.R2_PIPELINE_ACCESS_KEY_ID,
      secretAccessKey: process.env.R2_PIPELINE_SECRET_ACCESS_KEY,
    },
  });
  return client;
}

/** Upload one file. Returns the key it was stored under. */
export async function uploadFile(localPath, key) {
  const info = await stat(localPath);
  const extension = path.extname(localPath).toLowerCase();

  await getClient().send(
    new PutObjectCommand({
      Bucket: BUCKET,
      Key: key,
      Body: createReadStream(localPath),
      ContentLength: info.size,
      ContentType: CONTENT_TYPES[extension] || "application/octet-stream",
    }),
  );
  return key;
}

/**
 * Mirror a whole job folder.
 *
 * Never throws: a job whose models are safely on disk must not be marked
 * failed because a bucket was unreachable. The caller reports what came back
 * and carries on.
 */
export async function mirrorJob(jobId, files, localDir, onLine) {
  const report = onLine || (() => {});

  if (!r2Configured()) {
    return { mirrored: [], skipped: "R2 is not configured" };
  }

  const mirrored = [];
  const failed = [];
  for (const file of files) {
    const key = `jobs/${jobId}/${file.name}`;
    try {
      await uploadFile(path.join(localDir, file.name), key);
      mirrored.push({ name: file.name, key });
      report({ type: "stdout", line: `  r2: ${key}` });
    } catch (error) {
      report({ type: "stderr", line: `  r2 upload failed for ${file.name}: ${error.message}` });
      failed.push({ name: file.name, error: error.message });
    }
  }
  return {
    mirrored,
    failed,
    skipped: failed.length
      ? `${failed.length} of ${files.length} files failed to mirror: ${failed.map((item) => item.name).join(", ")}`
      : null,
  };
}

/** Mirror one converter result tree under its own durable R2 namespace. */
export async function mirrorConverterJob(jobId, files, localDir, onLine) {
  const report = onLine || (() => {});
  if (!r2Configured()) return { mirrored: [], skipped: "R2 is not configured" };

  const mirrored = [];
  const failed = [];
  for (const file of files) {
    const relative = String(file.path || file.name).replace(/\\/g, "/");
    const key = `converter-jobs/${jobId}/${relative}`;
    try {
      await uploadFile(path.join(localDir, ...relative.split("/")), key);
      mirrored.push({ ...file, key });
      report({ type: "stdout", line: `  r2: ${key}` });
    } catch (error) {
      report({ type: "stderr", line: `  r2 upload failed for ${relative}: ${error.message}` });
      failed.push({ name: relative, error: error.message });
    }
  }
  return {
    mirrored,
    failed,
    skipped: failed.length
      ? `${failed.length} of ${files.length} converter files failed to mirror.`
      : null,
  };
}

/**
 * A time-limited URL the browser can PUT straight to.
 *
 * Direct upload rather than through this server: a 300 MB model would
 * otherwise be streamed twice, once into Node and once out again, and tie up
 * the process for the whole transfer. The signature covers the exact key and
 * content type, so a leaked URL can only write that one object, only with
 * that type, and only until it expires.
 *
 * This is the one path where the browser talks to R2 directly, and therefore
 * the only reason the bucket needs a CORS policy at all.
 */
export async function presignUpload(key, contentType, { expiresIn = 900 } = {}) {
  return getSignedUrl(
    getClient(),
    new PutObjectCommand({ Bucket: BUCKET, Key: key, ContentType: contentType }),
    { expiresIn },
  );
}

/**
 * A time-limited URL for one object.
 *
 * The bucket is private, so this is the only way a browser reaches an object
 * that is no longer on the server's disk.
 */
export async function presignDownload(key, { expiresIn = 900, fileName } = {}) {
  return getSignedUrl(
    getClient(),
    new GetObjectCommand({
      Bucket: BUCKET,
      Key: key,
      ...(fileName
        ? { ResponseContentDisposition: `attachment; filename="${path.basename(fileName)}"` }
        : {}),
    }),
    { expiresIn },
  );
}

/** Everything stored for one job, for reconciling a manifest against the bucket. */
export async function listJobObjects(jobId) {
  return listObjects(`jobs/${jobId}/`);
}

/** List every object under one safe prefix, following R2 continuation tokens. */
export async function listObjects(prefix) {
  const objects = [];
  let continuationToken;

  do {
    const out = await getClient().send(
      new ListObjectsV2Command({
        Bucket: BUCKET,
        Prefix: prefix,
        ContinuationToken: continuationToken,
      }),
    );
    objects.push(...(out.Contents || []));
    continuationToken = out.IsTruncated ? out.NextContinuationToken : undefined;
  } while (continuationToken);

  return objects.map((item) => ({
    key: item.Key,
    name: path.posix.basename(item.Key),
    extension: path.posix.extname(item.Key).toLowerCase(),
    bytes: item.Size,
    modified: item.LastModified?.getTime?.() ?? null,
  }));
}

/** Group durable Meshy job objects for the converter's R2 project library. */
export async function listMeshyRuns() {
  const objects = await listObjects("jobs/");
  const grouped = new Map();

  for (const object of objects) {
    const parts = object.key.split("/");
    if (parts.length < 3 || parts[0] !== "jobs" || !parts[1]) continue;

    const jobId = parts[1];
    const run = grouped.get(jobId) || { id: jobId, modified: 0, files: [] };
    run.modified = Math.max(run.modified, object.modified || 0);
    run.files.push(object);
    grouped.set(jobId, run);
  }

  return [...grouped.values()]
    .map((run) => ({
      ...run,
      files: run.files.sort((a, b) => a.name.localeCompare(b.name)),
    }))
    .sort((a, b) => b.id.localeCompare(a.id));
}

/** Group durable converter artifacts into newest-first jobs for the result panel. */
export async function listConverterRuns() {
  const objects = await listObjects("converter-jobs/");
  const grouped = new Map();

  for (const object of objects) {
    const parts = object.key.split("/");
    if (parts.length < 3 || parts[0] !== "converter-jobs" || !parts[1]) continue;
    const jobId = parts[1];
    const run = grouped.get(jobId) || { id: jobId, modified: 0, files: [] };
    run.modified = Math.max(run.modified, object.modified || 0);
    run.files.push({ ...object, path: parts.slice(2).join("/") });
    grouped.set(jobId, run);
  }

  return [...grouped.values()]
    .map((run) => ({ ...run, files: run.files.sort((a, b) => a.path.localeCompare(b.path)) }))
    .sort((a, b) => b.modified - a.modified);
}

/** Stream one private R2 object into a local workspace file. */
export async function downloadObject(key, destinationPath) {
  const response = await getClient().send(new GetObjectCommand({ Bucket: BUCKET, Key: key }));
  if (!response.Body) throw new Error("R2 returned an empty object body.");

  await mkdir(path.dirname(destinationPath), { recursive: true });
  try {
    await pipeline(response.Body, createWriteStream(destinationPath, { flags: "wx" }));
  } catch (error) {
    await rm(destinationPath, { force: true }).catch(() => {});
    throw error;
  }

  const info = await stat(destinationPath);
  return { bytes: info.size, contentType: response.ContentType || null };
}

/** Remove one object. Used only when a job is deleted deliberately. */
export async function deleteObject(key) {
  await getClient().send(new DeleteObjectCommand({ Bucket: BUCKET, Key: key }));
}
