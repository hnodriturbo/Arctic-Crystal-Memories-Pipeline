/*
 * ═══════════════════════════════════════════════════════════════
 * Meshy Job Runner
 * ═══════════════════════════════════════════════════════════════
 * Path: src/lib/meshy/run-job.js
 * Purpose: Generate the model from photos already prepared, and bring the
 *          files home.
 *
 * Everything the route streams to the browser is emitted through `emit`,
 * so the runner itself knows nothing about Server-Sent Events.
 */

import { readFile } from "node:fs/promises";
import path from "node:path";

import { createTask, downloadTo, getBalance, meshyConfigured, waitForTask } from "@/lib/meshy/client";
import {
  buildMeshyPayload,
  DEFAULT_CRYSTAL_MARGIN_MM,
  estimateCredits,
  MESHY_MODES,
  MIN_CRYSTAL_MARGIN_MM,
  usableSpace,
} from "@/lib/meshy/catalog";
import { createJob, indexJobFiles, jobDir, listJobs, newJobId, saveJob } from "@/lib/meshy/jobs";
import { MESHY_INPUT_DIR, resolveInside } from "@/lib/paths";

const MIME_TYPES = { ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png" };

/** Meshy takes a public URL or a data URI; a local tool has no public URL to offer. */
async function toDataUri(filePath) {
  const extension = path.extname(filePath).toLowerCase();
  const mime = MIME_TYPES[extension];
  if (!mime) throw new Error(`Meshy accepts .jpg and .png only, not ${extension || "that file"}.`);

  const bytes = await readFile(filePath);
  return `data:${mime};base64,${bytes.toString("base64")}`;
}

/** The 2D generators return a plain list of picture URLs and nothing else. */
function collectImages(task, baseName) {
  return (task?.image_urls || []).map((url, index) => ({
    url,
    // Multi-view returns three, so number them; a single result keeps a clean name.
    name: task.image_urls.length > 1 ? `${baseName}-view-${index + 1}.png` : `${baseName}.png`,
  }));
}

/** Model formats first, then whatever thumbnails the task produced. */
function collectDownloads(task, formats, baseName) {
  const wanted = [];

  for (const format of formats) {
    const url = task?.model_urls?.[format];
    if (url) wanted.push({ url, name: `${baseName}.${format}` });
  }
  if (task?.model_urls?.pre_remeshed_glb) {
    wanted.push({ url: task.model_urls.pre_remeshed_glb, name: `${baseName}-pre-remesh.glb` });
  }
  if (task?.thumbnail_url) {
    wanted.push({ url: task.thumbnail_url, name: `${baseName}-thumbnail.png` });
  }
  if (task?.alpha_thumbnail_url) {
    wanted.push({ url: task.alpha_thumbnail_url, name: `${baseName}-thumbnail-alpha.png` });
  }
  for (const [view, url] of Object.entries(task?.thumbnail_urls || {})) {
    if (url) wanted.push({ url, name: `${baseName}-view-${view}.png` });
  }
  return wanted;
}

/**
 * Close a finished job and leave it local for the operator's review decision.
 *
 * R2 is deliberately not touched here. A model must be inspected through its
 * local GLB before the operator archives or discards the whole project.
 */
async function finishJob(job, consumed, emit) {
  job.status = "succeeded";
  job.finishedAt = Date.now();
  job.consumedCredits = consumed || job.estimatedCredits;
  job.files = await indexJobFiles(job.id);

  if (job.kind !== "text-to-image" && job.kind !== "image-to-image") {
    const hasGlb = job.files.some((file) => file.extension === ".glb");
    if (!hasGlb) throw new Error("Meshy returned no GLB, so this project cannot pass local review.");
    job.retentionStatus = "pending";
    job.storage = "vps-review";
  }
  await saveJob(job);

  emit({ type: "job", job });
  emit({ type: "stdout", line: `Done. Meshy charged ${job.consumedCredits} credits.` });
  return job;
}

/**
 * Run one Meshy job from photos on disk to model files on disk.
 *
 * `photos` are paths relative to meshy-pipeline/input/. Returns the finished
 * manifest; throws with a readable message on any failure, having already
 * written that message onto the job so the UI can show it after a reload.
 */
export async function runMeshyJob({ mode, photos = [], values = {}, signal, emit }) {
  const definition = MESHY_MODES[mode];
  if (!definition) throw new Error(`Unknown Meshy mode: ${mode}`);
  if (definition.locked) throw new Error(`${definition.label}: ${definition.locked}`);
  if (!meshyConfigured()) {
    throw new Error("MESHY_API_KEY is not set. Add it to .env.local and restart the dev server.");
  }

  // Large 3D jobs are a review queue of one. The operator must explicitly
  // archive or discard the current model before credits can be spent on the next.
  if (definition.produces === "model") {
    const pending = (await listJobs()).find((item) =>
      ["generating", "pending", "archiving", "failed-review"].includes(item.retentionStatus),
    );
    if (pending) {
      throw new Error(
        `Review ${pending.id} first: archive it to R2 or discard it before starting another 3D project.`,
      );
    }
  }

  // Fence every photo inside input/ before anything touches it.
  const sources = photos.map((relative) => {
    const absolute = resolveInside(MESHY_INPUT_DIR, relative);
    if (!absolute) throw new Error(`Photo escapes the input folder: ${relative}`);
    return absolute;
  });

  if (definition.photoCount > 0 && sources.length === 0) {
    throw new Error("This mode needs at least one photo.");
  }
  if (sources.length > definition.photoCount) {
    throw new Error(`${definition.label} takes at most ${definition.photoCount} photos.`);
  }
  // Every mode with a prompt field requires one; only the pure photo-to-mesh
  // modes can run on an image alone.
  const needsPrompt = definition.fields.some((field) => field.name === "prompt");
  if (needsPrompt && !String(values.prompt || "").trim()) {
    throw new Error(`${definition.label} needs a prompt.`);
  }

  const crystalMargin =
    definition.produces === "model"
      ? Number(values.crystal_margin ?? DEFAULT_CRYSTAL_MARGIN_MM)
      : null;
  if (
    definition.produces === "model" &&
    (!Number.isFinite(crystalMargin) || crystalMargin < MIN_CRYSTAL_MARGIN_MM)
  ) {
    throw new Error(`Crystal margin must be at least ${MIN_CRYSTAL_MARGIN_MM} mm.`);
  }

  const crystalSpace =
    definition.produces === "model"
      ? usableSpace(values.crystal_template, {
          width: values.custom_width,
          height: values.custom_height,
          depth: values.custom_depth,
          margin: crystalMargin,
        })
      : null;
  const invalidDimension = crystalSpace
    ? Object.entries(crystalSpace.physical).find(
        ([axis, dimension]) => dimension !== null && crystalSpace[axis] <= 0,
      )
    : null;
  if (invalidDimension) {
    throw new Error(
      `Crystal margin ${crystalMargin} mm leaves no usable ${invalidDimension[0]} in that blank.`,
    );
  }

  const label =
    values.subject ||
    (sources[0] ? path.basename(sources[0], path.extname(sources[0])) : values.prompt) ||
    mode;

  const job = {
    id: newJobId(label),
    createdAt: Date.now(),
    finishedAt: null,
    mode,
    kind: definition.kind,
    status: "running",
    error: null,
    crystalTemplate: values.crystal_template || null,
    crystalMargin,
    // Typed-in millimetres, if any. Carried to the converter alongside the
    // blank so a one-off size does not have to be entered twice.
    customSize:
      Number(values.custom_width) || Number(values.custom_height) || Number(values.custom_depth)
        ? {
            width: Number(values.custom_width) || null,
            height: Number(values.custom_height) || null,
            depth: Number(values.custom_depth) || null,
          }
        : null,
    estimatedCredits: estimateCredits(mode, values),
    consumedCredits: null,
    values,
    sourcePhotos: photos,
    preparedPhotos: [],
    meshyTaskId: null,
    files: [],
    retentionStatus: definition.produces === "model" ? "generating" : null,
    storage: "vps",
  };

  await createJob(job);
  emit({ type: "step", line: `Job ${job.id}` });
  emit({ type: "job", job });

  try {
    // ── Credit check ────────────────────────────────────────────────────────
    // One cheap call, and far kinder than discovering the shortfall as a 402
    // after Meshy has already queued the job.
    const balance = await getBalance();
    emit({
      type: "stdout",
      line: `Meshy balance: ${balance} credits. This job is estimated at ${job.estimatedCredits}.`,
    });
    if (balance < job.estimatedCredits) {
      throw new Error(
        `Not enough Meshy credits: ${balance} left, about ${job.estimatedCredits} needed.`,
      );
    }

    // ── Photo clean-up ──────────────────────────────────────────────────────
    /*
     * Photos arrive ready.
     *
     * Cleaning them is the image pipeline's own step, with its own settings
     * and its own results to look at, so this one sends what it is given.
     */
    const prepared = sources;
    job.preparedPhotos = prepared.map((file) => path.basename(file));
    await saveJob(job);

    // ── Generation ──────────────────────────────────────────────────────────
    const images = [];
    for (const file of prepared) images.push(await toDataUri(file));

    const payload = buildMeshyPayload(mode, values, images);
    emit({ type: "step", line: `Sending to Meshy (${definition.kind})` });

    // Log the settings but never the base64 - one photo is megabytes of noise.
    const { image_url: _image, image_urls: _images, ...loggable } = payload;
    emit({ type: "cmd", line: `POST ${definition.kind} ${JSON.stringify(loggable)}` });

    const taskId = await createTask(definition.kind, payload);
    job.meshyTaskId = taskId;
    await saveJob(job);
    emit({ type: "stdout", line: `Task ${taskId} accepted.` });

    let task = await waitForTask(definition.kind, taskId, {
      signal,
      onUpdate: (update) => {
        const queued = update.preceding_tasks
          ? ` (${update.preceding_tasks} task(s) ahead in the queue)`
          : "";
        emit({
          type: "progress",
          percent: Number(update.progress ?? 0),
          status: update.status,
          line: `${update.status} ${update.progress ?? 0}%${queued}`,
        });
      },
    });

    let consumed = Number(task?.consumed_credits || 0);

    // ── 2D generators stop here ─────────────────────────────────────────────
    // Nothing to remesh, texture or fit to a crystal; the result is pictures,
    // which the panel then offers to push into meshy-pipeline/input/ as the
    // source for a 3D run.
    if (definition.produces === "image") {
      const pictures = collectImages(task, job.id);
      emit({ type: "step", line: `Downloading ${pictures.length} image(s)` });

      for (const item of pictures) {
        if (signal?.aborted) throw new Error("Cancelled.");
        await downloadTo(item.url, path.join(jobDir(job.id), item.name));
        emit({ type: "stdout", line: `  ${item.name}` });
      }

      return finishJob(job, consumed, emit);
    }

    // ── Texture pass, text-to-3d only ───────────────────────────────────────
    // The image modes texture in one call; text-to-3d splits it into a second
    // refine task that takes the preview's id.
    if (mode === "text_to_3d" && values.should_texture) {
      emit({ type: "step", line: "Texturing (refine pass)" });
      const refineId = await createTask("text-to-3d", {
        mode: "refine",
        preview_task_id: taskId,
        ai_model: values.ai_model,
        texture_resolution: values.texture_resolution,
        enable_pbr: Boolean(values.enable_pbr),
        ...(values.texture_prompt ? { texture_prompt: values.texture_prompt.slice(0, 600) } : {}),
        target_formats: values.target_formats,
      });
      task = await waitForTask("text-to-3d", refineId, {
        signal,
        onUpdate: (update) =>
          emit({
            type: "progress",
            percent: Number(update.progress ?? 0),
            status: update.status,
            line: `refine ${update.status} ${update.progress ?? 0}%`,
          }),
      });
      consumed += Number(task?.consumed_credits || 0);
    }

    // ── Optional resize to the crystal blank ────────────────────────────────
    // Meshy sizes in metres, so a blank's usable height converts straight over.
    // Skipping this changes nothing downstream - mesh_to_pointcloud refits the
    // model to the blank regardless - it only makes the exported file itself
    // measure correctly in Blender or a slicer.
    // A typed-in height wins over the blank, so an odd size can be produced
    // without adding a blank to the catalogue for it.
    const targetHeight = crystalSpace?.height || 0;

    if (values.scale_to_crystal && targetHeight > 0) {
      const label = `${values.crystal_template || "custom blank"} (${targetHeight} mm usable height, ${crystalMargin} mm margin per side)`;
      emit({ type: "step", line: `Resizing to ${label}` });

      const remeshId = await createTask("remesh", {
        input_task_id: task.id,
        target_formats: values.target_formats,
        resize_height: targetHeight / 1000,
        origin_at: values.origin_at || "center",
      });
      task = await waitForTask("remesh", remeshId, {
        signal,
        onUpdate: (update) =>
          emit({
            type: "progress",
            percent: Number(update.progress ?? 0),
            status: update.status,
            line: `remesh ${update.status} ${update.progress ?? 0}%`,
          }),
      });
      consumed += Number(task?.consumed_credits || 0);
    }

    // ── Bring the files home ────────────────────────────────────────────────
    const directory = jobDir(job.id);
    const targetFormats = [...new Set(["glb", ...(values.target_formats || [])])];
    const downloads = collectDownloads(task, targetFormats, job.id);
    emit({ type: "step", line: `Downloading ${downloads.length} file(s)` });

    for (const item of downloads) {
      if (signal?.aborted) throw new Error("Cancelled.");
      await downloadTo(item.url, path.join(directory, item.name));
      emit({ type: "stdout", line: `  ${item.name}` });
    }

    return await finishJob(job, consumed, emit);
  } catch (error) {
    job.status = "failed";
    job.finishedAt = Date.now();
    job.error = error.message;
    if (definition.produces === "model") job.retentionStatus = "failed-review";
    job.files = await indexJobFiles(job.id).catch(() => []);
    await saveJob(job).catch(() => {});
    emit({ type: "job", job });
    throw error;
  }
}
