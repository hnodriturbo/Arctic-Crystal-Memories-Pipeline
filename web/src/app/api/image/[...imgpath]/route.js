// src/app/api/image/[...imgpath]/route.js
// GET /api/image/<folder>/<filename> — serves a pipeline image file from disk.
// folder is one of: input, upscaled, enhanced, bg_removed

import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { auth } from "@/auth";

const PIPELINE_ROOT = process.env.PIPELINE_ROOT;

const FOLDER_MAP = {
  input: "input",
  upscaled: path.join("output", "upscaled"),
  enhanced: path.join("output", "enhanced"),
  bg_removed: path.join("output", "bg_removed"),
};

const MIME = {
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".webp": "image/webp",
  ".tiff": "image/tiff",
  ".bmp": "image/bmp",
};

export async function GET(req, { params }) {
  const session = await auth();
  if (!session) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const { imgpath } = await params;
  const parts = imgpath;
  if (!parts || parts.length < 2) {
    return NextResponse.json({ error: "Invalid path" }, { status: 400 });
  }

  const [folder, ...rest] = parts;
  const filename = rest.join("/");
  const relDir = FOLDER_MAP[folder];

  if (!relDir) {
    return NextResponse.json({ error: "Unknown folder" }, { status: 400 });
  }

  const absPath = path.resolve(path.join(PIPELINE_ROOT, relDir, filename));
  // Security: must stay inside PIPELINE_ROOT
  if (!absPath.startsWith(path.resolve(PIPELINE_ROOT))) {
    return NextResponse.json({ error: "Forbidden" }, { status: 403 });
  }

  if (!fs.existsSync(absPath)) {
    return NextResponse.json({ error: "Not found" }, { status: 404 });
  }

  const ext = path.extname(absPath).toLowerCase();
  const mime = MIME[ext] || "application/octet-stream";
  const buffer = fs.readFileSync(absPath);

  return new Response(buffer, {
    headers: {
      "Content-Type": mime,
      "Cache-Control": "no-cache",
    },
  });
}
