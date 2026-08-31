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

import { copyFile, mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";

import { RELIEF_CODE_DIR, RELIEF_OUTPUT_DIR, RELIEF_PYTHON_EXE, RELIEF_ROOT } from "@/lib/paths";
import { interpreterReady, runPython } from "@/lib/python";
import {
  buildAppearanceRefinementArgs,
  buildDepthArgs,
  buildDetailRefinementArgs,
  buildFaceRefinementArgs,
  buildHeadRefinementArgs,
  buildMeshArgs,
  resolvedMeshGrid,
  resolvedReliefDepth,
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
    const refinedDepth = path.join(jobDir, "refined-depth.png");
    const headRefinedDepth = path.join(jobDir, "head-refined-depth.png");
    const finalDepth = path.join(jobDir, "final-depth.png");
    const crystalTone = path.join(jobDir, "crystal-tone.png");
    const geometryDir = path.join(jobDir, "geometry");
    const faceQaDir = path.join(jobDir, "face-refinement");
    const headQaDir = path.join(jobDir, "head-refinement");
    const detailQaDir = path.join(jobDir, "detail-refinement");
    const appearanceQaDir = path.join(jobDir, "appearance-refinement");
    const glb = path.join(jobDir, "relief.glb");
    const crystalGlb = path.join(jobDir, "relief-crystal.glb");
    const obj = path.join(jobDir, "relief.obj");

    // ── Stage one: the only model in the whole pipeline ─────────────────────
    if (signal?.aborted) throw new Error("Cancelled.");
    report({ type: "step", line: "Depth map (depth_map.py)" });
    await runPython(
      RELIEF_PYTHON_EXE,
      [
        path.join(RELIEF_CODE_DIR, "depth_map.py"),
        ...buildDepthArgs(values, photo, depth, geometryDir),
      ],
      { cwd: RELIEF_ROOT, onLine: report, signal },
    );

    // ── Stage two: mandatory face detection and local depth refinement ────
    if (signal?.aborted) throw new Error("Cancelled.");
    report({ type: "step", line: "Face detection and refinement (face_refine.py)" });
    await runPython(
      RELIEF_PYTHON_EXE,
      [
        path.join(RELIEF_CODE_DIR, "face_refine.py"),
        ...buildFaceRefinementArgs(values, photo, depth, refinedDepth, faceQaDir),
      ],
      { cwd: RELIEF_ROOT, onLine: report, signal },
    );
    const faceMetadata = JSON.parse(await readFile(path.join(jobDir, "refined-depth.json"), "utf8"));

    // ── Stage three: real low-frequency skull and facial volume ────────────
    if (signal?.aborted) throw new Error("Cancelled.");
    report({ type: "step", line: "468-point parametric head shape (gnm_head_refine.py)" });
    await runPython(
      RELIEF_PYTHON_EXE,
      [
        path.join(RELIEF_CODE_DIR, "gnm_head_refine.py"),
        ...buildHeadRefinementArgs(
          values,
          photo,
          refinedDepth,
          path.join(jobDir, "refined-depth.json"),
          headRefinedDepth,
          headQaDir,
        ),
      ],
      { cwd: RELIEF_ROOT, onLine: report, signal },
    );
    const headMetadata = JSON.parse(
      await readFile(path.join(jobDir, "head-refined-depth.json"), "utf8"),
    );

    // ── Stage four: bounded micro-depth from MoGe surface normals ──────────
    if (values.engine !== "moge-2") {
      throw new Error("Surface-detail refinement currently requires the MoGe-2 normal output.");
    }
    if (signal?.aborted) throw new Error("Cancelled.");
    report({ type: "step", line: "Surface micro-depth (detail_refine.py)" });
    await runPython(
      RELIEF_PYTHON_EXE,
      [
        path.join(RELIEF_CODE_DIR, "detail_refine.py"),
        ...buildDetailRefinementArgs(
          values,
          headRefinedDepth,
          path.join(geometryDir, "normal.png"),
          path.join(geometryDir, "mask.png"),
          finalDepth,
          detailQaDir,
        ),
      ],
      { cwd: RELIEF_ROOT, onLine: report, signal },
    );
    const detailMetadata = JSON.parse(await readFile(path.join(jobDir, "final-depth.json"), "utf8"));

    // ── Stage five: tonal identity, explicitly separate from geometry ─────
    if (signal?.aborted) throw new Error("Cancelled.");
    report({ type: "step", line: "Crystal appearance detail (appearance_refine.py)" });
    await runPython(
      RELIEF_PYTHON_EXE,
      [
        path.join(RELIEF_CODE_DIR, "appearance_refine.py"),
        ...buildAppearanceRefinementArgs(values, photo, crystalTone, appearanceQaDir),
      ],
      { cwd: RELIEF_ROOT, onLine: report, signal },
    );
    const appearanceMetadata = JSON.parse(
      await readFile(path.join(jobDir, "crystal-tone.json"), "utf8"),
    );

    // ── Stage six: two visualisations of one completed relief geometry ─────
    if (signal?.aborted) throw new Error("Cancelled.");
    report({ type: "step", line: "RGB relief mesh (depth_to_mesh.py)" });
    await runPython(
      RELIEF_PYTHON_EXE,
      [
        path.join(RELIEF_CODE_DIR, "depth_to_mesh.py"),
        ...buildMeshArgs(values, finalDepth, photo, glb, obj),
      ],
      { cwd: RELIEF_ROOT, onLine: report, signal },
    );
    report({ type: "step", line: "Crystal-tone preview (same relief geometry)" });
    await runPython(
      RELIEF_PYTHON_EXE,
      [
        path.join(RELIEF_CODE_DIR, "depth_to_mesh.py"),
        ...buildMeshArgs(
          { ...values, vertex_color: "texture" },
          finalDepth,
          photo,
          crystalGlb,
          null,
          crystalTone,
        ),
      ],
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
      resolvedReliefDepth: Number(resolvedReliefDepth(values)),
      resolvedGrid: resolvedMeshGrid(values),
      values,
      files: {
        photo: path.basename(photo),
        depth: "depth.png",
        depthMeta: "depth.json",
        refinedDepth: "refined-depth.png",
        headRefinedDepth: "head-refined-depth.png",
        headRefinedDepthMeta: "head-refined-depth.json",
        finalDepth: "final-depth.png",
        finalDepthMeta: "final-depth.json",
        normal: "geometry/normal.png",
        subjectMask: "geometry/mask.png",
        faceMeta: "refined-depth.json",
        faceDetectionPreview: "face-refinement/faces-detected.png",
        faceDifferencePreview: "face-refinement/before-after-difference.png",
        headPriorPreview: "head-refinement/gnm-head-prior.png",
        headroomDepthPreview: "head-refinement/depth-centred-headroom.png",
        headLandmarkFitPreview: "head-refinement/gnm-landmark-fit.png",
        headDepthComparisonPreview: "head-refinement/depth-before-prior-after.png",
        detailHeightPreview: "detail-refinement/microdetail-height.png",
        detailDifferencePreview: "detail-refinement/before-after-microdetail.png",
        crystalTone: "crystal-tone.png",
        crystalToneMeta: "crystal-tone.json",
        appearanceDetailPreview: "appearance-refinement/appearance-microdetail.png",
        appearanceComparisonPreview: "appearance-refinement/rgb-luma-crystal-tone.png",
        preview: "relief.glb",
        crystalPreview: "relief-crystal.glb",
        mesh: "relief.obj",
      },
      faceRefinement: {
        required: faceMetadata.face_refinement_required,
        complete: faceMetadata.face_refinement_complete,
        faceCount: faceMetadata.face_count,
        backend: faceMetadata.backend,
        resolutionLevel: faceMetadata.resolution_level,
      },
      headRefinement: {
        required: headMetadata.head_refinement_required,
        complete: headMetadata.head_refinement_complete,
        backend: headMetadata.backend,
        settings: headMetadata.settings || null,
        faces: headMetadata.faces || [],
      },
      detailRefinement: {
        complete: detailMetadata.detail_refinement_complete,
        backend: detailMetadata.backend,
        settings: detailMetadata.settings,
        measured: detailMetadata.measured,
      },
      appearanceRefinement: {
        complete: appearanceMetadata.appearance_refinement_complete,
        backend: appearanceMetadata.backend,
        semantics: appearanceMetadata.semantics,
        settings: appearanceMetadata.settings,
        measured: appearanceMetadata.measured,
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
