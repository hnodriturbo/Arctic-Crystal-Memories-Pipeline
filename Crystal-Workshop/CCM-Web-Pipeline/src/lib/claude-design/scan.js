/*
 * ═══════════════════════════════════════════════════════════════
 * Claude Design Scan
 * ═══════════════════════════════════════════════════════════════
 * Path: src/lib/claude-design/scan.js
 * Purpose: Read the design tree into the two lists the page shows - playable
 *          collections, and the zip shelf that has not been unpacked yet.
 *
 * Deliberately two separate readers. A zip is not something you can preview or
 * render, and mixing the two into one list made it impossible to see at a
 * glance which archives still had no folder behind them.
 */

import { discoverLocal } from "./discovery.mjs";
import fs from "node:fs";
import path from "node:path";

import { DESIGN_ROOT, EXPORT_ROOT, ZIP_DIR, toPosix } from "./paths";

/** `.dc.html` fetches its `.jsx` scenes at runtime; plain `.html` is self-contained. */
function kindOf(fileName) {
  return /\.dc\.html$/i.test(fileName) ? "design" : "video";
}

/**
 * Guess the frame size from the file name. Only a starting value - the form
 * lets the operator override it, because a name is not a promise.
 */
export function guessSize(fileName) {
  return /mobile|portrait|story|reel|9x16/i.test(fileName)
    ? { width: 1080, height: 1920 }
    : { width: 1920, height: 1080 };
}

/**
 * Scene length read out of the HTML itself. Claude Design stores the scene list
 * in `OM_SCENES`, so a redesigned animation reports its new length here without
 * anything being edited. Null when the variable is absent.
 */
export function readDuration(absolutePath) {
  try {
    const html = fs.readFileSync(absolutePath, "utf8");
    const match = html.match(/OM_SCENES\s*=\s*'(\[.*?\])'/s);
    if (!match) return null;
    const scenes = JSON.parse(match[1].replace(/\\"/g, '"'));
    const total = scenes.reduce((sum, scene) => sum + Number(scene.dur || 0), 0);
    return total > 0 ? total : null;
  } catch {
    return null;
  }
}

/** Loose match between a zip name and a folder name, ignoring case and punctuation. */
function normalize(name) {
  return name.toLowerCase().replace(/\.zip$/, "").replace(/[^a-z0-9]/g, "");
}

/** Discover local entries and explain dependency-incomplete sources. */
export function listCollections() {
  return discoverLocal(DESIGN_ROOT).map(group => ({
    ...group,
    designs: group.designs.map(design => ({
      ...design,
      kind: kindOf(design.name),
      duration: readDuration(path.join(DESIGN_ROOT, design.rootRel)),
      ...guessSize(design.name),
    })),
  }));
}

/**
 * The zip shelf, read on its own. `unpacked` answers the only question the
 * operator actually has about an archive: is there already a folder for this,
 * or is this one still sealed?
 */
export function listZips() {
  let files;
  try {
    files = fs.readdirSync(ZIP_DIR).filter((file) => /\.zip$/i.test(file));
  } catch {
    return [];
  }

  let directories = [];
  try {
    directories = fs
      .readdirSync(DESIGN_ROOT, { withFileTypes: true })
      .filter((entry) => entry.isDirectory())
      .map((entry) => normalize(entry.name));
  } catch {
    directories = [];
  }

  return files
    .map((file) => {
      const info = fs.statSync(path.join(ZIP_DIR, file));
      const key = normalize(file);
      return {
        name: file,
        bytes: info.size,
        modified: info.mtimeMs,
        unpacked: directories.some((directory) => directory.includes(key) || key.includes(directory)),
      };
    })
    .sort((a, b) => a.name.localeCompare(b.name, "is"));
}

/** Videos already rendered on this machine, used to warn before overwriting one. */
export function listExported() {
  const exported = [];

  let directories;
  try {
    directories = fs.readdirSync(EXPORT_ROOT, { withFileTypes: true });
  } catch {
    return exported;
  }

  for (const directory of directories) {
    if (!directory.isDirectory()) continue;
    for (const file of fs.readdirSync(path.join(EXPORT_ROOT, directory.name))) {
      if (!/\.mp4$/i.test(file)) continue;
      const info = fs.statSync(path.join(EXPORT_ROOT, directory.name, file));
      exported.push({
        collection: directory.name,
        name: file,
        bytes: info.size,
        modified: info.mtimeMs,
        rootRel: toPosix(path.join("exported-videos", directory.name, file)),
      });
    }
  }

  return exported.sort((a, b) => b.modified - a.modified);
}

/** Whether the root exists at all - false on a VPS that has pulled nothing yet. */
export function rootPresent() {
  try {
    return fs.statSync(DESIGN_ROOT).isDirectory();
  } catch {
    return false;
  }
}
