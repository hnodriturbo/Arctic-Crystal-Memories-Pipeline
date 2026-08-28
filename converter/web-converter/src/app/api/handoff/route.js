/*
 * ═══════════════════════════════════════════════════════════════
 * Handoff Route
 * ═══════════════════════════════════════════════════════════════
 * Path: src/app/api/handoff/route.js
 * Purpose: Move one file from the pipeline that produced it into the one
 *          that consumes it next.
 *
 * The three pipelines chain in one direction - clean a photo, generate a
 * model, sample it into a point cloud - and this is the only door between
 * them. A copy rather than a link, because each pipeline lists its own input
 * folder and clearing one must never quietly empty another.
 */

import { copyFile, mkdir, stat } from "node:fs/promises";
import path from "node:path";

import { readJob } from "@/lib/meshy/jobs";
import { downloadObject, r2Configured } from "@/lib/storage/r2";
import {
  IMAGE_INPUT_DIR,
  IMAGE_OUTPUT_DIR,
  MESHY_INPUT_DIR,
  MESHY_OUTPUT_DIR,
  UPLOAD_DIR,
  availableFileName,
  resolveInside,
} from "@/lib/paths";

export const runtime = "nodejs";
export const maxDuration = 600;

const SOURCES = {
  "image-output": IMAGE_OUTPUT_DIR,
  "image-input": IMAGE_INPUT_DIR,
  "meshy-output": MESHY_OUTPUT_DIR,
  "meshy-input": MESHY_INPUT_DIR,
};

// Each destination only accepts what the pipeline behind it can actually read.
const DESTINATIONS = {
  "image-input": {
    dir: IMAGE_INPUT_DIR,
    accepts: [".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"],
    label: "the image pipeline",
    prefix: "",
  },
  "meshy-input": {
    dir: MESHY_INPUT_DIR,
    // Meshy's 3D endpoints read JPEG and PNG only, whatever the 2D ones allow.
    accepts: [".jpg", ".jpeg", ".png"],
    label: "Meshy",
    prefix: "",
  },
  "converter-input": {
    dir: UPLOAD_DIR,
    accepts: [".obj", ".dxf"],
    label: "the converter",
    prefix: "uploads/",
  },
};

export async function POST(request) {
  const { from = "meshy-output", to, path: relativePath, jobId } = await request.json();

  const sourceRoot = SOURCES[from];
  const destination = DESTINATIONS[to];

  if (!sourceRoot || !destination || !relativePath) {
    return Response.json({ error: "Need a valid from, to and path" }, { status: 400 });
  }

  const source = resolveInside(sourceRoot, relativePath);
  if (!source) {
    return Response.json({ error: "Path escapes its root" }, { status: 403 });
  }

  const extension = path.extname(source).toLowerCase();
  if (!destination.accepts.includes(extension)) {
    return Response.json(
      {
        error: `${destination.label} reads ${destination.accepts.join(", ")} - not ${extension || "that file"}.`,
      },
      { status: 400 },
    );
  }

  await mkdir(destination.dir, { recursive: true });
  const fileName = await availableFileName(destination.dir, path.basename(source));
  const destinationPath = path.join(destination.dir, fileName);

  let info;
  try {
    info = await stat(source);
  } catch (error) {
    if (error?.code !== "ENOENT" || from !== "meshy-output" || !r2Configured()) {
      return Response.json({ error: "That file is no longer on disk or R2" }, { status: 404 });
    }

    try {
      info = await downloadObject(`jobs/${relativePath}`, destinationPath);
    } catch {
      return Response.json({ error: "That file is no longer on disk or R2" }, { status: 404 });
    }
  }
  if (typeof info.isFile === "function" && !info.isFile()) {
    return Response.json({ error: "The handoff source is not a file" }, { status: 400 });
  }

  if (typeof info.isFile === "function") await copyFile(source, destinationPath);

  // The size chosen during generation carries over, so the converter opens
  // already pointed at the crystal this model was made for.
  const job = jobId ? await readJob(jobId) : null;

  return Response.json({
    file: {
      path: `${destination.prefix}${fileName}`,
      name: fileName,
      bytes: info.size ?? info.bytes,
      extension,
    },
    template: job?.crystalTemplate || null,
    customSize: job?.customSize || null,
  });
}
