/*
 * ═══════════════════════════════════════════════════════════════
 * Meshy Panel State
 * ═══════════════════════════════════════════════════════════════
 * Path: src/lib/meshy/state.js
 * Purpose: Everything the Meshy panel needs in one read - which features
 *          are configured, the credit balance, the photos, the past jobs.
 *
 * Shared by the page (for its first render) and the API route (for
 * refreshes), so both always agree on what the panel is looking at.
 */

import { readdir, stat } from "node:fs/promises";
import path from "node:path";

import { PHOTO_TYPES } from "@/lib/meshy/catalog";
import { getBalance, meshyConfigured } from "@/lib/meshy/client";
import { imagePipelineReady } from "@/lib/image/chain";
import { listJobs } from "@/lib/meshy/jobs";
import { visionConfigured } from "@/lib/meshy/vision";
import { IMAGE_OUTPUT_DIR, MESHY_INPUT_DIR } from "@/lib/paths";

/** Photos waiting in input/, newest first - Meshy only reads .jpg and .png. */
export async function listPhotos() {
  let entries;
  try {
    entries = await readdir(MESHY_INPUT_DIR, { withFileTypes: true });
  } catch {
    return [];
  }

  const photos = [];
  for (const entry of entries) {
    if (!entry.isFile() || entry.name.startsWith(".")) continue;
    const extension = path.extname(entry.name).toLowerCase();
    if (!PHOTO_TYPES.includes(extension)) continue;

    const info = await stat(path.join(MESHY_INPUT_DIR, entry.name));
    photos.push({
      path: entry.name,
      name: entry.name,
      extension,
      bytes: info.size,
      modified: info.mtimeMs,
    });
  }
  return photos.sort((a, b) => b.modified - a.modified);
}

/**
 * What the Image pipeline produced, filtered to what Meshy can actually read.
 *
 * The image pipeline writes PNG at every stage, so this is almost always the
 * whole folder - but a stray .webp there would be rejected by Meshy's 3D
 * endpoints rather than converted, so it is filtered out here.
 */
async function listCleanedPhotos() {
  let entries;
  try {
    entries = await readdir(IMAGE_OUTPUT_DIR, { withFileTypes: true });
  } catch {
    return [];
  }

  const found = [];
  for (const entry of entries) {
    if (!entry.isFile() || entry.name.startsWith(".")) continue;
    const extension = path.extname(entry.name).toLowerCase();
    if (!PHOTO_TYPES.includes(extension)) continue;

    const info = await stat(path.join(IMAGE_OUTPUT_DIR, entry.name));
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

export async function readMeshyState() {
  const configured = {
    meshy: meshyConfigured(),
    openai: visionConfigured(),
    cleanup: imagePipelineReady(),
  };

  // `cleaned` is the image pipeline's output, offered here directly so a photo
  // that was just prepared can be picked without a detour through the library.
  const [photos, cleaned, jobs] = await Promise.all([
    listPhotos(),
    listCleanedPhotos(),
    listJobs(),
  ]);
  return { configured, balance: null, balanceError: null, photos, cleaned, jobs };
}

/** Fetch credits separately so an external Meshy call never delays local job history. */
export async function readMeshyBalance() {
  if (!meshyConfigured()) return { balance: null, balanceError: null };
  try {
    return { balance: await getBalance(), balanceError: null };
  } catch (error) {
    return { balance: null, balanceError: error.message };
  }
}
