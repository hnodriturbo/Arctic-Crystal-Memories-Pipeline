/*
 * ═══════════════════════════════════════════════════════════════
 * Claude Design Paths
 * ═══════════════════════════════════════════════════════════════
 * Path: src/lib/claude-design/paths.js
 * Purpose: The one place that knows where the Claude Design source tree lives.
 *
 * Two very different machines run this code. On the operator's Windows box the
 * root is the real Claude-Design-Stuff repository next to this one, and the
 * designs are already there. On the VPS nothing is there until a collection is
 * pulled out of R2, so the root is a scratch workspace that fills up on demand.
 * CLAUDE_DESIGN_ROOT decides which, and everything downstream just reads files.
 */

import path from "node:path";

// The repository sits beside ACM-Web-Workshop in the shared workspace root, four
// levels above this app. The env var wins whenever it is set, which is how the
// VPS points at its workspace instead.
const FALLBACK_ROOT = path.resolve(process.cwd(), "..", "..", "..", "Claude-Design-Stuff");

export const DESIGN_ROOT = process.env.CLAUDE_DESIGN_ROOT
  ? path.resolve(process.env.CLAUDE_DESIGN_ROOT)
  : FALLBACK_ROOT;

export const EXPORT_ROOT = path.join(DESIGN_ROOT, "exported-videos");
export const ZIP_DIR = path.join(DESIGN_ROOT, "zip-files");

// Folders that are never a design collection: git plumbing, the app's own
// output, and the zip shelf which has its own separate reader.
export const IGNORED_DIRS = new Set([
  "node_modules",
  ".git",
  ".markdown",
  ".next",
  "exported-videos",
  "zip-files",
]);

// R2 prefixes inside the acm-workshop bucket. Sources and videos are kept apart
// so a listing of finished work never has to walk thousands of asset files.
export const R2_SOURCE_PREFIX = "claude-design/sources/";
export const R2_VIDEO_PREFIX = "claude-design/videos/";

/**
 * Reject anything that would escape the root. Every relative path that arrives
 * from the browser goes through this before a single byte is read or written.
 * Returns an absolute path, or null when the result lands outside.
 */
export function safeJoin(root, relative) {
  if (typeof relative !== "string" || relative.includes("\0")) return null;
  const full = path.resolve(root, relative);
  const rootWithSeparator = root.endsWith(path.sep) ? root : root + path.sep;
  if (full !== root && !full.startsWith(rootWithSeparator)) return null;
  return full;
}

/** A path relative to the root, always with forward slashes so it survives a URL. */
export function toPosix(relative) {
  return relative.split(path.sep).join("/");
}

/** The same guard for R2 keys, which are strings rather than filesystem paths. */
export function allowedDesignKey(key) {
  return (
    typeof key === "string" &&
    !key.includes("\\") &&
    !key.split("/").some((part) => part === ".." || part === ".") &&
    (key.startsWith(R2_SOURCE_PREFIX) || key.startsWith(R2_VIDEO_PREFIX))
  );
}
