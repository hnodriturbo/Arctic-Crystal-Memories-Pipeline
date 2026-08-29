/*
 * ═══════════════════════════════════════════════════════════════
 * Relief Chain
 * ═══════════════════════════════════════════════════════════════
 * Path: src/lib/relief/chain.js
 * Purpose: Run one photograph through depth estimation and mesh building into
 *          a single job folder.
 *
 * Modelled on lib/meshy/ rather than lib/image/: a relief run produces a set
 * of related files that only make sense together - the depth map, the GLB the
 * browser previews, the OBJ the sampler consumes - so it gets a job folder
 * and a manifest, not numbered files in a shared output directory.
 */

import { copyFile, mkdir, readFile, readdir, writeFile } from "node:fs/promises";
import path from "node:path";

import {
  CODE_DIR,
  PYTHON_EXE,
  RELIEF_CODE_DIR,
  RELIEF_OUTPUT_DIR,
  RELIEF_PYTHON_EXE,
  RELIEF_ROOT,
} from "@/lib/paths";
import { interpreterReady, runPython } from "@/lib/python";
import {
  automaticPointBudget,
  buildDepthArgs,
  buildMeshArgs,
  buildPointCloudArgs,
} from "@/lib/relief/catalog";
import { mirrorReliefJob, pruneLocalJobs, rememberSource } from "@/lib/relief/library";

// Depth Anything Large holds well over 1 GB while it runs, and the image
// pipeline's own queue cannot see this one. Two relief jobs at once would put
// the 6 GB VPS straight into swap.
let reliefQueue = Promise.resolve();

// Local work is the safe default. Remote library writes must be deliberately
// enabled on a deployment; simply having R2 credentials is not permission.
const REMOTE_LIBRARY_ENABLED = process.env.RELIEF_REMOTE_LIBRARY_ENABLED === "true";

async function withReliefSlot(task) {
  const previous = reliefQueue;
  let release;
  reliefQueue = new Promise((resolve) => {
    release = resolve;
  });
  await previous;
  try {
    return await task();
  } finally {
    release();
  }
}

/** Whether this machine can build reliefs at all. */
export function reliefPipelineReady() {
  return interpreterReady(RELIEF_PYTHON_EXE);
}

/**
 * Job ids sort chronologically on their own, matching meshy-pipeline's
 * YYYYMMDD-HHMMSS-subject convention so both output trees read the same way.
 */
export function reliefJobId(sourceName) {
  const now = new Date();
  const pad = (value) => String(value).padStart(2, "0");
  const stamp =
    `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}` +
    `-${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;

  const subject = path
    .basename(sourceName, path.extname(sourceName))
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 40);

  return subject ? `${stamp}-${subject}` : stamp;
}

/**
 * Run both stages into one job folder.
 *
 * The photograph is copied in rather than referenced, because the GLB, the
 * OBJ and the point cloud all trace back to one specific image and a job that
 * cannot say which image it came from is not reproducible.
 */
export async function runReliefChain({ source, values, emit, signal }) {
  const report = emit || (() => {});

  if (!reliefPipelineReady()) {
    throw new Error(
      `No 2.5D-pipeline venv at ${RELIEF_PYTHON_EXE}. Run: python -m venv .venv && pip install -r requirements.txt`,
    );
  }
  if (!interpreterReady(PYTHON_EXE)) {
    throw new Error(
      `No pipeline-converter venv at ${PYTHON_EXE}. The 2.5D point-cloud stage needs that local environment.`,
    );
  }

  return withReliefSlot(async () => {
    const jobId = reliefJobId(path.basename(source));
    const jobDir = path.join(RELIEF_OUTPUT_DIR, jobId);
    await mkdir(jobDir, { recursive: true });

    const photo = path.join(jobDir, `source${path.extname(source).toLowerCase()}`);
    await copyFile(source, photo);

    // Into the durable library immediately, before anything can fail. The
    // whole point is that this exact photograph can be re-run months later
    // without the customer sending it again.
    const remembered = REMOTE_LIBRARY_ENABLED
      ? await rememberSource(source, report)
      : { key: null };
    if (!REMOTE_LIBRARY_ENABLED) {
      report({ type: "step", line: "Local-only mode: remote library writes disabled" });
    }

    const depth = path.join(jobDir, "depth.png");
    const glb = path.join(jobDir, "relief.glb");
    const obj = path.join(jobDir, "relief.obj");

    // ── Stage one: the only model in the whole pipeline ─────────────────────
    if (signal?.aborted) throw new Error("Cancelled.");
    report({ type: "step", line: "Depth map (depth_map.py)" });
    await runPython(
      RELIEF_PYTHON_EXE,
      [path.join(RELIEF_CODE_DIR, "depth_map.py"), ...buildDepthArgs(values, photo, depth)],
      { cwd: RELIEF_ROOT, onLine: report, signal },
    );

    // ── Stage three: production point cloud ────────────────────────────────
    if (signal?.aborted) throw new Error("Cancelled.");
    const depthMetadata = JSON.parse(await readFile(path.join(jobDir, "depth.json"), "utf8"));
    const pointBudget = automaticPointBudget(
      depthMetadata.width,
      depthMetadata.height,
      values.maximum_points,
    );
    report({
      type: "step",
      line:
        values.point_budget_mode === "auto" || !values.point_budget_mode
          ? `Point cloud (automatic target ${pointBudget.toLocaleString()})`
          : "Point cloud (configured target)",
    });
    await runPython(
      PYTHON_EXE,
      [
        path.join(CODE_DIR, "mesh_to_pointcloud.py"),
        ...buildPointCloudArgs(values, {
          objPath: obj,
          photoPath: photo,
          outputDir: jobDir,
          pointBudget,
        }),
      ],
      { cwd: path.dirname(CODE_DIR), onLine: report, signal },
    );

    const generatedFiles = await readdir(jobDir);
    const dxfName = generatedFiles.find((name) => name.toLowerCase().endsWith(".dxf"));
    const xyzName = generatedFiles.find((name) => name.toLowerCase().endsWith(".xyz"));
    if (!dxfName) throw new Error("The point-cloud stage completed without writing a DXF.");
    const pointCount = Number(dxfName.match(/-(\d+)points\.dxf$/i)?.[1] || 0);

    // ── Stage two: ordinary geometry ────────────────────────────────────────
    if (signal?.aborted) throw new Error("Cancelled.");
    report({ type: "step", line: "Relief mesh (depth_to_mesh.py)" });
    await runPython(
      RELIEF_PYTHON_EXE,
      [path.join(RELIEF_CODE_DIR, "depth_to_mesh.py"), ...buildMeshArgs(values, depth, photo, glb, obj)],
      { cwd: RELIEF_ROOT, onLine: report, signal },
    );

    /*
     * The manifest is the only record that survives a restart, and it exists
     * mainly to answer one question later: which settings produced the relief
     * the customer approved? The GLB alone cannot say.
     */
    const manifest = {
      jobId,
      created: new Date().toISOString(),
      sourceName: path.basename(source),
      sourceKey: remembered.key,
      template: values.template || "60x80x40",
      values,
      files: {
        photo: path.basename(photo),
        depth: "depth.png",
        depthMeta: "depth.json",
        preview: "relief.glb",
        mesh: "relief.obj",
        pointCloud: dxfName,
        ...(xyzName ? { pointPreview: xyzName } : {}),
      },
      pointCloud: {
        previewDotSizeMm: 0.08,
        automaticBudget: pointBudget,
        finalPoints: pointCount || null,
        axes: "X=width, Y=height, Z=depth",
      },
    };
    await writeFile(path.join(jobDir, "job.json"), JSON.stringify(manifest, null, 2), "utf-8");

    // Durable copy, then sweep. Local disk is a workspace, never storage -
    // pruneLocalJobs only removes folders it has confirmed are in the bucket.
    if (REMOTE_LIBRARY_ENABLED) {
      await mirrorReliefJob(
        jobId,
        [...Object.values(manifest.files), "job.json"],
        report,
      );
      await pruneLocalJobs(report);
    }

    report({ type: "step", line: `Job ${jobId} complete` });
    return manifest;
  });
}
