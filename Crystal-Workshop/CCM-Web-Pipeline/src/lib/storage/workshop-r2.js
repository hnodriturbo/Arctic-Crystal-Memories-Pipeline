/*
 * ═══════════════════════════════════════════════════════════════
 * Workshop R2 Storage
 * ═══════════════════════════════════════════════════════════════
 * Path: src/lib/storage/workshop-r2.js
 * Purpose: The ccm-workshop bucket - durable storage for design sources
 *          and rendered media under their existing claude-design prefixes.
 *
 * The pipeline and design clients keep their existing environment interfaces,
 * but both now target ccm-workshop. Their disjoint prefixes preserve scene,
 * model and design identities while one bucket owns the complete workshop.
 *
 * Private, EU jurisdiction. Nothing is public, so every read the browser makes
 * goes out as a short-lived presigned URL rather than through a custom domain.
 */

import { createReadStream, createWriteStream } from "node:fs";
import { mkdir, rm, stat } from "node:fs/promises";
import path from "node:path";
import { pipeline } from "node:stream/promises";

import {
  DeleteObjectCommand,
  GetObjectCommand,
  HeadObjectCommand,
  ListObjectsV2Command,
  PutObjectCommand,
  S3Client,
} from "@aws-sdk/client-s3";
import { getSignedUrl } from "@aws-sdk/s3-request-presigner";

const BUCKET = process.env.R2_WORKSHOP_BUCKET_NAME;

// A video served as octet-stream will not play in a browser tab, and a .jsx
// scene served as anything but JavaScript will not be fetched by its .dc.html.
const CONTENT_TYPES = {
  ".mp4": "video/mp4",
  ".webm": "video/webm",
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".mjs": "text/javascript; charset=utf-8",
  ".jsx": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".md": "text/markdown; charset=utf-8",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".webp": "image/webp",
  ".gif": "image/gif",
  ".svg": "image/svg+xml",
  ".avif": "image/avif",
  ".mp3": "audio/mpeg",
  ".wav": "audio/wav",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
  ".ttf": "font/ttf",
  ".otf": "font/otf",
  ".zip": "application/zip",
};

let client = null;

/** Optional feature: without credentials the workshop simply stays local-only. */
export function workshopR2Configured() {
  return Boolean(
    process.env.R2_WORKSHOP_ENDPOINT &&
      process.env.R2_WORKSHOP_ACCESS_KEY_ID &&
      process.env.R2_WORKSHOP_SECRET_ACCESS_KEY &&
      BUCKET,
  );
}

function getClient() {
  if (!workshopR2Configured()) {
    throw new Error("The ccm-workshop bucket is not configured. Add the R2_WORKSHOP_* keys.");
  }
  client ||= new S3Client({
    region: "auto",
    endpoint: process.env.R2_WORKSHOP_ENDPOINT,
    credentials: {
      accessKeyId: process.env.R2_WORKSHOP_ACCESS_KEY_ID,
      secretAccessKey: process.env.R2_WORKSHOP_SECRET_ACCESS_KEY,
    },
  });
  return client;
}

/** The content type this bucket serves a given file name as. */
export function contentTypeFor(fileName) {
  return CONTENT_TYPES[path.extname(fileName).toLowerCase()] || "application/octet-stream";
}

/** Upload one file from disk. Returns the key it landed on. */
export async function putFile(localPath, key, { metadata } = {}) {
  const info = await stat(localPath);
  await getClient().send(
    new PutObjectCommand({
      Bucket: BUCKET,
      Key: key,
      Body: createReadStream(localPath),
      ContentLength: info.size,
      ContentType: contentTypeFor(localPath),
      ...(metadata ? { Metadata: metadata } : {}),
    }),
  );
  return key;
}

/** Whether an object exists, and what it looks like. Null rather than a throw on 404. */
export async function headObject(key) {
  try {
    return await getClient().send(new HeadObjectCommand({ Bucket: BUCKET, Key: key }));
  } catch (error) {
    if (error.$metadata?.httpStatusCode === 404) return null;
    throw error;
  }
}

/** Every object under one prefix, following R2's continuation tokens to the end. */
export async function listObjects(prefix) {
  const objects = [];
  let continuationToken;

  do {
    const page = await getClient().send(
      new ListObjectsV2Command({
        Bucket: BUCKET,
        Prefix: prefix,
        ContinuationToken: continuationToken,
      }),
    );
    objects.push(...(page.Contents || []));
    continuationToken = page.IsTruncated ? page.NextContinuationToken : undefined;
  } while (continuationToken);

  return objects.map((item) => ({
    key: item.Key,
    name: path.posix.basename(item.Key),
    extension: path.posix.extname(item.Key).toLowerCase(),
    bytes: item.Size,
    modified: item.LastModified?.getTime?.() ?? null,
  }));
}

/**
 * A time-limited URL for one object.
 *
 * `inline` is what makes the video player work: without an explicit content
 * disposition R2 is free to offer the file as a download, and the same URL has
 * to serve both the `<video>` element and the Download button.
 */
export async function presignRead(key, { expiresIn = 3600, download = false, fileName } = {}) {
  const name = path.posix.basename(fileName || key);
  return getSignedUrl(
    getClient(),
    new GetObjectCommand({
      Bucket: BUCKET,
      Key: key,
      ResponseContentDisposition: download
        ? `attachment; filename="${name}"`
        : `inline; filename="${name}"`,
    }),
    { expiresIn },
  );
}

/** Stream one object down into a local working file, creating its folder. */
export async function fetchObject(key, destinationPath) {
  const response = await getClient().send(new GetObjectCommand({ Bucket: BUCKET, Key: key }));
  if (!response.Body) throw new Error("R2 returned an empty object body.");

  await mkdir(path.dirname(destinationPath), { recursive: true });
  try {
    await pipeline(response.Body, createWriteStream(destinationPath));
  } catch (error) {
    await rm(destinationPath, { force: true }).catch(() => {});
    throw error;
  }

  const info = await stat(destinationPath);
  return { bytes: info.size, contentType: response.ContentType || null };
}

/** Remove one object. Only ever called for a video the operator chose to delete. */
export async function removeObject(key) {
  await getClient().send(new DeleteObjectCommand({ Bucket: BUCKET, Key: key }));
}
