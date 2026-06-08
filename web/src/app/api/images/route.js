// src/app/api/images/route.js
// GET /api/images — lists all images in pipeline/input/ and all output folders.
// Returns file metadata including dimensions hint for upscale threshold check.

import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { auth } from "@/auth";

const PIPELINE_ROOT = process.env.PIPELINE_ROOT;
const THRESHOLD = parseInt(process.env.UPSCALE_THRESHOLD || "1800", 10);
const IMAGE_EXTS = new Set([".png", ".jpg", ".jpeg", ".webp", ".tiff", ".bmp"]);

const DIRS = [
  { key: "input", rel: "input" },
  { key: "upscaled", rel: path.join("output", "upscaled") },
  { key: "enhanced", rel: path.join("output", "enhanced") },
  { key: "bg_removed", rel: path.join("output", "bg_removed") },
];

function scanDir(absDir, folderKey) {
  const files = [];
  if (!fs.existsSync(absDir)) return files;

  for (const entry of fs.readdirSync(absDir, { withFileTypes: true })) {
    if (!entry.isFile()) continue;
    const ext = path.extname(entry.name).toLowerCase();
    if (!IMAGE_EXTS.has(ext)) continue;

    const fullPath = path.join(absDir, entry.name);
    const stat = fs.statSync(fullPath);

    files.push({
      name: entry.name,
      folder: folderKey,
      relativePath: path.join(folderKey, entry.name).replace(/\\/g, "/"),
      size: stat.size,
      mtime: stat.mtime.toISOString(),
      needsUpscale: folderKey === "input" ? null : false,
    });
  }

  return files;
}

export async function GET(req) {
  const session = await auth();
  if (!session) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  if (!PIPELINE_ROOT) {
    return NextResponse.json({ error: "PIPELINE_ROOT not configured" }, { status: 500 });
  }

  const allFiles = [];

  for (const { key, rel } of DIRS) {
    const absDir = path.join(PIPELINE_ROOT, rel);
    const files = scanDir(absDir, key);

    if (key === "input") {
      for (const f of files) {
        // Mark as needing upscale if we can read basic file info
        // Actual dimension check happens client-side via Image element
        f.needsUpscale = null;
        f.threshold = THRESHOLD;
      }
    }

    allFiles.push(...files);
  }

  return NextResponse.json({ files: allFiles, threshold: THRESHOLD });
}
