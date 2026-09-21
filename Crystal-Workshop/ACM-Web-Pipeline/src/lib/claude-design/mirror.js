/*
 * ═══════════════════════════════════════════════════════════════
 * Claude Design Mirror
 * ═══════════════════════════════════════════════════════════════
 * Path: src/lib/claude-design/mirror.js
 * Purpose: Move one collection between the local design tree and acm-workshop.
 *
 * Two machines, opposite directions. The Windows box pushes: the designs are
 * authored there and the repository stays the original. The VPS pulls: it has
 * no design repository, so a collection is fetched into a scratch workspace
 * just before it is rendered.
 *
 * Push never deletes. A file that has gone locally stays in the bucket, because
 * the far more likely cause of a file disappearing is a mistake than a
 * deliberate removal, and R2 is cheap enough that the safe answer wins.
 */

import fs from "node:fs";
import { mkdir, stat } from "node:fs/promises";
import path from "node:path";

import { DESIGN_ROOT, IGNORED_DIRS, R2_SOURCE_PREFIX, safeJoin, toPosix } from "./paths";
import { fetchObject, headObject, listObjects, putFile } from "@/lib/storage/workshop-r2";

// Anything above this is a video, an archive or a mistake - the design trees
// themselves are HTML, JSX and artwork.
const MAX_FILE_BYTES = 200 * 1024 * 1024;

/** Every file under one local folder, as paths relative to it. */
function inventory(directoryAbsolute, relative = "") {
  const files = [];
  let entries;
  try {
    entries = fs.readdirSync(directoryAbsolute, { withFileTypes: true });
  } catch {
    return files;
  }

  for (const entry of entries) {
    // A symlink could point anywhere, so it is skipped rather than followed.
    if (entry.isSymbolicLink()) continue;
    const name = relative ? `${relative}/${entry.name}` : entry.name;

    if (entry.isDirectory()) {
      if (IGNORED_DIRS.has(entry.name) || entry.name.startsWith(".")) continue;
      files.push(...inventory(path.join(directoryAbsolute, entry.name), name));
    } else if (entry.isFile()) {
      files.push(name);
    }
  }
  return files;
}

/**
 * Upload one collection.
 *
 * Size and modification time decide what to skip, rather than hashing every
 * file: a collection is a few hundred assets that rarely change, and reading
 * all of them to prove they are identical costs more than the upload saved.
 */
export async function pushCollection(collection, onLine = () => {}) {
  const localRoot = safeJoin(DESIGN_ROOT, collection);
  if (!localRoot || !fs.existsSync(localRoot)) {
    throw new Error(`No such collection: ${collection}`);
  }

  const files = inventory(localRoot);
  let uploaded = 0;
  let unchanged = 0;
  let skipped = 0;

  for (const relative of files) {
    const localPath = path.join(localRoot, ...relative.split("/"));
    const key = `${R2_SOURCE_PREFIX}${collection}/${relative}`;
    const info = await stat(localPath);

    if (info.size > MAX_FILE_BYTES) {
      onLine(`  skipped ${relative} - ${(info.size / 1048576).toFixed(0)} MB is too large`);
      skipped++;
      continue;
    }

    const existing = await headObject(key);
    if (existing && existing.ContentLength === info.size) {
      unchanged++;
      continue;
    }

    await putFile(localPath, key, { mtime: String(Math.round(info.mtimeMs)) });
    onLine(`  uploaded ${relative}`);
    uploaded++;
  }

  return { collection, files: files.length, uploaded, unchanged, skipped };
}

/**
 * Download one collection into the local design root.
 *
 * This is what makes a VPS render possible at all: Chromium has to open real
 * files on disk, so the tree exists locally for as long as the render needs it.
 */
export async function pullCollection(collection, onLine = () => {}) {
  const prefix = `${R2_SOURCE_PREFIX}${collection}/`;
  const objects = await listObjects(prefix);
  if (!objects.length) throw new Error(`Nothing stored under ${collection}`);

  const localRoot = safeJoin(DESIGN_ROOT, collection);
  if (!localRoot) throw new Error("Invalid collection name");
  await mkdir(localRoot, { recursive: true });

  let fetched = 0;
  let unchanged = 0;

  for (const object of objects) {
    const relative = object.key.slice(prefix.length);
    if (!relative || relative.endsWith("/")) continue;

    const destination = safeJoin(localRoot, relative);
    if (!destination) continue;

    try {
      const existing = await stat(destination);
      if (existing.size === object.bytes) {
        unchanged++;
        continue;
      }
    } catch {
      // Not there yet, which is the normal case on a fresh workspace.
    }

    await fetchObject(object.key, destination);
    onLine(`  fetched ${relative}`);
    fetched++;
  }

  return { collection, objects: objects.length, fetched, unchanged };
}

/** Which collections exist in the bucket, for a machine with nothing local. */
export async function listRemoteCollections() {
  const objects = await listObjects(R2_SOURCE_PREFIX);
  const collections = new Map();

  for (const object of objects) {
    const rest = object.key.slice(R2_SOURCE_PREFIX.length);
    const slash = rest.indexOf("/");
    if (slash < 0) continue;

    const name = rest.slice(0, slash);
    const entry = collections.get(name) || { name, files: 0, bytes: 0, modified: 0 };
    entry.files++;
    entry.bytes += object.bytes || 0;
    entry.modified = Math.max(entry.modified, object.modified || 0);
    collections.set(name, entry);
  }

  return [...collections.values()].sort((a, b) => a.name.localeCompare(b.name, "is"));
}

/** A local path as the browser addresses it, for building preview URLs. */
export function previewPathFor(collection, relative) {
  return toPosix(path.join(collection, relative));
}
