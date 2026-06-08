// src/app/api/run/route.js
// DELETE /api/run — deletes a specific output file (denied run cleanup).
// Does NOT delete the core output folders (upscaled/, enhanced/, bg_removed/).

import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { auth } from "@/auth";

const PIPELINE_ROOT = process.env.PIPELINE_ROOT;

const SAFE_DIRS = [
  path.join(PIPELINE_ROOT || "", "output", "upscaled"),
  path.join(PIPELINE_ROOT || "", "output", "enhanced"),
  path.join(PIPELINE_ROOT || "", "output", "bg_removed"),
];

export async function DELETE(req) {
  const session = await auth();
  if (!session) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const { filePath } = await req.json();
  if (!filePath) return NextResponse.json({ error: "filePath required" }, { status: 400 });

  const absPath = path.resolve(path.join(PIPELINE_ROOT, filePath));

  // Security: must be inside one of the safe output dirs, not the dir root itself
  const isInSafeDir = SAFE_DIRS.some(
    (d) => absPath.startsWith(d + path.sep) || absPath.startsWith(d + "/")
  );
  const isSafeDirItself = SAFE_DIRS.some((d) => absPath === path.resolve(d));

  if (!isInSafeDir || isSafeDirItself) {
    return NextResponse.json({ error: "Forbidden" }, { status: 403 });
  }

  if (!fs.existsSync(absPath)) {
    return NextResponse.json({ error: "Not found" }, { status: 404 });
  }

  fs.unlinkSync(absPath);
  return NextResponse.json({ ok: true });
}
