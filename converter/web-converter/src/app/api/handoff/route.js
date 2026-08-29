/*
 * ═══════════════════════════════════════════════════════════════
 * Handoff Route
 * ═══════════════════════════════════════════════════════════════
 * Path: src/app/api/handoff/route.js
 * Purpose: Move one file from the pipeline that produced it into the one
 *          that consumes it next.
 *
 * The pipelines chain in one direction - clean a photo, turn it into geometry
 * (Meshy for a full 3D subject, the 2.5D pipeline for a relief), sample it
 * into a point cloud - and this is the only door between them. A copy rather
 * than a link, because each pipeline lists its own input folder and clearing
 * one must never quietly empty another.
 */

import { copyFile, mkdir, readFile, stat } from "node:fs/promises";
import path from "node:path";

import { readJob } from "@/lib/meshy/jobs";
import { downloadObject, r2Configured } from "@/lib/storage/r2";
import {
  IMAGE_INPUT_DIR,
  IMAGE_OUTPUT_DIR,
  MESHY_INPUT_DIR,
  MESHY_OUTPUT_DIR,
  RELIEF_INPUT_DIR,
  RELIEF_OUTPUT_DIR,
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
  "relief-output": RELIEF_OUTPUT_DIR,
  "relief-input": RELIEF_INPUT_DIR,
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
  "relief-input": {
    dir: RELIEF_INPUT_DIR,
    // A cut-out PNG is what this pipeline actually wants, but a bare
    // photograph still works - it just gets no silhouette to mask against.
    accepts: [".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"],
    label: "the 2.5D pipeline",
    prefix: "",
  },
  "converter-input": {
    dir: UPLOAD_DIR,
    accepts: [".obj", ".dxf"],
    label: "the converter",
    prefix: "uploads/",
  },
};

/**
 * The blank a relief was fitted to, read back out of its job manifest.
 *
 * Without this the converter opens on its default blank and silently refits
 * a mesh that was already scaled to a different one, which is the kind of
 * mistake that only shows up as a wrongly sized engraving.
 */
async function reliefJobTemplate(relativePath) {
  const jobFolder = relativePath.replace(/\\/g, "/").split("/")[0];
  const manifest = resolveInside(RELIEF_OUTPUT_DIR, path.join(jobFolder, "job.json"));
  if (!manifest) return null;

  try {
    return JSON.parse(await readFile(manifest, "utf-8"));
  } catch {
    // An older job folder with no manifest is not an error worth failing on.
    return null;
  }
}

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
  // already pointed at the crystal this model was made for. A relief carries
  // it in its own job.json instead of Meshy's.
  const relief = from === "relief-output" ? await reliefJobTemplate(relativePath) : null;
  const job = !relief && jobId ? await readJob(jobId) : null;

  return Response.json({
    file: {
      path: `${destination.prefix}${fileName}`,
      name: fileName,
      bytes: info.size ?? info.bytes,
      extension,
    },
    template: relief?.template || job?.crystalTemplate || null,
    customSize: job?.customSize || null,
    margin: relief?.values?.border || job?.crystalMargin || job?.values?.crystal_margin || null,
  });
}
