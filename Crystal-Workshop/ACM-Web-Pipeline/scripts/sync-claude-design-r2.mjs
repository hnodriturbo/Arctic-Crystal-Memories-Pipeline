/*
 * ═══════════════════════════════════════════════════════════════
 * Sync Claude Design to R2
 * ═══════════════════════════════════════════════════════════════
 * Path: scripts/sync-claude-design-r2.mjs
 * Purpose: Back the local Claude Design tree up to acm-workshop.
 *
 * Run by the daily R2 job and by the "ACM - Update R2" desktop shortcut:
 *   node --env-file=.env.local scripts/sync-claude-design-r2.mjs [--dry-run]
 *
 * Never deletes. A file that has gone locally stays in the bucket, because a
 * file disappearing is far more often a mistake than a decision, and R2 is
 * cheap enough that the recoverable answer wins.
 *
 * Never overwrites in place either. Before an object is replaced, the copy
 * that is there is moved aside to claude-design/history/<sha256>/, so an
 * earlier version of a design is always recoverable. R2 has no object
 * versioning - GetBucketVersioning and PutBucketVersioning are unimplemented -
 * so this is not belt and braces, it is the only version history the design
 * tree has. sync-scene-files.mjs keeps Cockpit scenes the same way.
 *
 * Its own S3 client rather than importing src/lib - this runs under bare Node
 * with no bundler, so the @/ aliases do not resolve. Same shape as
 * sync-scene-files.mjs, which exists for exactly the same reason.
 */

import { createHash } from "node:crypto";
import { createReadStream } from "node:fs";
import { readdir, stat } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import {
  CopyObjectCommand,
  HeadObjectCommand,
  PutObjectCommand,
  S3Client,
} from "@aws-sdk/client-s3";

// ========================================
// Configuration
// ========================================

const app = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const root = process.env.CLAUDE_DESIGN_ROOT
  ? path.resolve(process.env.CLAUDE_DESIGN_ROOT)
  : path.resolve(app, "../../../Claude-Design-Stuff");

const bucket = process.env.R2_WORKSHOP_BUCKET_NAME;
const prefix = "claude-design/sources/";
const historyPrefix = "claude-design/history/";
const dryRun = process.argv.includes("--dry-run");

// Products, tooling and git plumbing. The videos have their own prefix and are
// put there by the render itself, so they are not mirrored from here.
const SKIP_DIRS = new Set([
  "node_modules",
  ".git",
  ".markdown",
  ".next",
  "exported-videos",
  "zip-files",
]);

// Above this is a video or an archive that wandered in, not a design asset.
const MAX_BYTES = 200 * 1024 * 1024;

const CONTENT_TYPES = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".mjs": "text/javascript; charset=utf-8",
  ".jsx": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".md": "text/markdown; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".webp": "image/webp",
  ".gif": "image/gif",
  ".avif": "image/avif",
  ".mp3": "audio/mpeg",
  ".wav": "audio/wav",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
  ".ttf": "font/ttf",
  ".otf": "font/otf",
};

if (!dryRun && (!bucket || !process.env.R2_WORKSHOP_SECRET_ACCESS_KEY)) {
  throw new Error("The acm-workshop R2 configuration is missing. Check R2_WORKSHOP_* in the env file.");
}

const client = new S3Client({
  region: "auto",
  endpoint: process.env.R2_WORKSHOP_ENDPOINT,
  credentials: {
    accessKeyId: process.env.R2_WORKSHOP_ACCESS_KEY_ID,
    secretAccessKey: process.env.R2_WORKSHOP_SECRET_ACCESS_KEY,
  },
});

// ========================================
// Walking the tree
// ========================================

/** Every real file under the design root, as forward-slash relative paths. */
async function inventory(directory, relative = "") {
  const found = [];
  let entries;
  try {
    entries = await readdir(directory, { withFileTypes: true });
  } catch {
    return found;
  }

  for (const entry of entries) {
    // A symlink could point anywhere on the disk, so it is skipped, not followed.
    if (entry.isSymbolicLink()) continue;
    const name = relative ? `${relative}/${entry.name}` : entry.name;

    if (entry.isDirectory()) {
      if (SKIP_DIRS.has(entry.name) || entry.name.startsWith(".")) continue;
      found.push(...(await inventory(path.join(directory, entry.name), name)));
    } else if (entry.isFile()) {
      found.push(name);
    }
  }
  return found;
}

/** SHA-256 of a file, streamed so a large asset is never held in memory. */
async function hashFile(file) {
  const digest = createHash("sha256");
  for await (const chunk of createReadStream(file)) digest.update(chunk);
  return digest.digest("hex");
}

/** Null rather than a throw for an object that is simply not there yet. */
async function head(key) {
  try {
    return await client.send(new HeadObjectCommand({ Bucket: bucket, Key: key }));
  } catch (error) {
    if (error.$metadata?.httpStatusCode === 404) return null;
    throw error;
  }
}

// ========================================
// Run
// ========================================

const files = await inventory(root);

if (dryRun) {
  for (const file of files) console.log(prefix + file);
  console.log(`DRY_RUN root=${root} entries=${files.length}`);
} else {
  let uploaded = 0;
  let archived = 0;
  let unchanged = 0;
  let skipped = 0;

  for (const relative of files) {
    const source = path.join(root, ...relative.split("/"));
    const key = prefix + relative;
    const info = await stat(source);

    if (info.size > MAX_BYTES) {
      console.log(`SKIPPED ${relative} size=${info.size}`);
      skipped++;
      continue;
    }

    const existing = await head(key);
    const mtime = String(Math.round(info.mtimeMs));

    /*
     * Cheap check first, hash only when it is inconclusive. Same size and same
     * modification time means untouched, and that covers almost every file on
     * almost every run without reading a byte. Same size but a newer mtime is
     * the case that matters: an edit that happens to keep the byte count would
     * otherwise never be noticed, and the copy in R2 would stay wrong forever.
     */
    if (existing && existing.ContentLength === info.size) {
      if (existing.Metadata?.mtime === mtime) {
        unchanged++;
        continue;
      }
      const digest = await hashFile(source);
      if (existing.Metadata?.sha256 === digest) {
        unchanged++;
        continue;
      }
    }

    // Move the copy that is there aside before replacing it. IfMatch on the
    // source means a file changing underneath this run fails the archive
    // rather than silently losing the version it was meant to preserve.
    if (existing) {
      const revision = existing.Metadata?.sha256 || existing.ETag.replaceAll('"', "");
      await client.send(
        new CopyObjectCommand({
          Bucket: bucket,
          Key: `${historyPrefix}${revision}/${relative}`,
          CopySource: [bucket, ...key.split("/")].map(encodeURIComponent).join("/"),
          CopySourceIfMatch: existing.ETag,
        }),
      );
      console.log(`ARCHIVED ${relative} revision=${revision.slice(0, 12)}`);
      archived++;
    }

    await client.send(
      new PutObjectCommand({
        Bucket: bucket,
        Key: key,
        Body: createReadStream(source),
        ContentLength: info.size,
        ContentType: CONTENT_TYPES[path.extname(source).toLowerCase()] || "application/octet-stream",
        // The hash is what makes the next run able to tell an edit from a
        // touched timestamp, and names the folder this copy is archived into.
        Metadata: { mtime, sha256: await hashFile(source) },
      }),
    );
    console.log(`UPLOADED ${relative} bytes=${info.size}`);
    uploaded++;
  }

  console.log(
    `CLAUDE_DESIGN_SYNC_OK uploaded=${uploaded} archived=${archived} unchanged=${unchanged} skipped=${skipped}`,
  );
}
