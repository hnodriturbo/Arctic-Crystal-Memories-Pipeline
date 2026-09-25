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

import path from "node:path";
import { syncTree } from "./sync-engine.mjs";
import { designStore } from "./sync-store.mjs";

import { DESIGN_ROOT, R2_SOURCE_PREFIX, toPosix } from "./paths";
import { listObjects } from "@/lib/storage/workshop-r2";

// Anything above this is a video, an archive or a mistake - the design trees
// themselves are HTML, JSX and artwork.


/** Both UI actions use the same safe baseline-aware reconciliation as the Windows task. */
export async function syncCollection(collection, onLine = () => {}) {
  return syncTree({ root: DESIGN_ROOT, store: designStore(), collection, onLine });
}
export const pushCollection = syncCollection;
export const pullCollection = syncCollection;

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
