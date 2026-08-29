/*
 * ═══════════════════════════════════════════════════════════════
 * Meshy Retexture Runner
 * ═══════════════════════════════════════════════════════════════
 * Path: src/lib/meshy/retexture-job.js
 * Purpose: Apply a new Meshy texture to a reviewed model without changing
 *          its geometry, then add every returned asset to the same project.
 */

import { createReadStream, createWriteStream } from "node:fs";
import { once } from "node:events";
import { rename, rm } from "node:fs/promises";
import path from "node:path";
import { createInterface } from "node:readline";

import { createTask, downloadTo, getBalance, meshyConfigured, waitForTask } from "@/lib/meshy/client";
import { indexJobFiles, jobDir, readJob, saveJob } from "@/lib/meshy/jobs";

const AI_MODELS = new Set(["latest", "meshy-7", "meshy-6", "meshy-5"]);
const TEXTURE_RESOLUTIONS = new Set(["2k", "4k", "8k"]);
const TARGET_FORMATS = new Set(["glb", "obj", "fbx", "stl", "usdz", "3mf"]);
const ACTIVE_RETEXTURES = new Set();
const STALE_RUN_MS = 4 * 60 * 60 * 1000;

function sourceFileName(url, fallback) {
  try {
    return path.basename(decodeURIComponent(new URL(url).pathname)) || fallback;
  } catch {
    return fallback;
  }
}

function textureExtension(url) {
  const extension = path.extname(sourceFileName(url, "texture.png")).toLowerCase();
  return [".png", ".jpg", ".jpeg", ".webp"].includes(extension) ? extension : ".png";
}

/** Collect complete textured exports, including OBJ companions and PBR maps. */
function collectRetextureDownloads(task, formats, baseName) {
  const downloads = [];

  for (const format of formats) {
    const url = task?.model_urls?.[format];
    if (!url) continue;
    downloads.push({
      url,
      name: `${baseName}.${format}`,
      sourceName: sourceFileName(url, `model.${format}`),
    });
  }

  // Meshy returns MTL beside textured OBJ even though MTL is not itself a
  // target format. Keep it and every map it references so OBJ is not grey.
  if (task?.model_urls?.mtl) {
    downloads.push({
      url: task.model_urls.mtl,
      name: `${baseName}.mtl`,
      sourceName: sourceFileName(task.model_urls.mtl, "model.mtl"),
    });
  }

  for (const [setIndex, textureSet] of (task?.texture_urls || []).entries()) {
    for (const [mapType, url] of Object.entries(textureSet || {})) {
      if (!url) continue;
      downloads.push({
        url,
        name: `${baseName}-texture-${String(setIndex + 1).padStart(2, "0")}-${mapType.replaceAll("_", "-")}${textureExtension(url)}`,
        sourceName: sourceFileName(url, `texture-${setIndex + 1}-${mapType}.png`),
      });
    }
  }

  if (task?.thumbnail_url) {
    downloads.push({
      url: task.thumbnail_url,
      name: `${baseName}-thumbnail.png`,
      sourceName: sourceFileName(task.thumbnail_url, "preview.png"),
    });
  }
  if (task?.alpha_thumbnail_url) {
    downloads.push({
      url: task.alpha_thumbnail_url,
      name: `${baseName}-thumbnail-alpha.png`,
      sourceName: sourceFileName(task.alpha_thumbnail_url, "preview-alpha.png"),
    });
  }

  const seen = new Set();
  return downloads.filter((item) => {
    if (seen.has(item.url)) return false;
    seen.add(item.url);
    return true;
  });
}

/** Rewrite OBJ/MTL relative references after giving every downloaded file a unique name. */
async function repairCompanionReferences(directory, downloads) {
  const replacements = new Map(
    downloads
      .filter((item) => item.sourceName && item.sourceName !== item.name)
      .map((item) => [item.sourceName, item.name]),
  );

  for (const item of downloads.filter(({ name }) => [".obj", ".mtl"].includes(path.extname(name)))) {
    const target = path.join(directory, item.name);
    const temporary = `${target}.references`;
    const input = createReadStream(target, { encoding: "utf8" });
    const output = createWriteStream(temporary, { encoding: "utf8" });
    const lines = createInterface({ input, crlfDelay: Infinity });

    try {
      for await (const line of lines) {
        let updated = line;
        for (const [sourceName, localName] of replacements) {
          updated = updated.split(sourceName).join(localName);
        }
        if (!output.write(`${updated}\n`)) await once(output, "drain");
      }
      output.end();
      await once(output, "finish");
      await rename(temporary, target);
    } catch (error) {
      output.destroy();
      throw error;
    } finally {
      lines.close();
      await rm(temporary, { force: true }).catch(() => {});
    }
  }
}

function normalizeSettings(values = {}) {
  const prompt = String(values.textStylePrompt || "").trim();
  if (!prompt) throw new Error("Retexture needs a texture prompt.");
  if (prompt.length > 600) throw new Error("Texture prompt must be 600 characters or fewer.");

  const aiModel = AI_MODELS.has(values.aiModel) ? values.aiModel : "latest";
  const textureResolution = TEXTURE_RESOLUTIONS.has(values.textureResolution)
    ? values.textureResolution
    : "4k";
  if (aiModel === "meshy-5" && textureResolution !== "2k") {
    throw new Error("Meshy 5 Retexture supports 2K textures only.");
  }

  const requestedFormats = Array.isArray(values.targetFormats) ? values.targetFormats : [];
  const targetFormats = [
    ...new Set(["glb", ...requestedFormats.filter((format) => TARGET_FORMATS.has(format))]),
  ];

  return {
    prompt,
    aiModel,
    textureResolution,
    targetFormats,
    enableOriginalUv: values.enableOriginalUv !== false,
    enablePbr: values.enablePbr !== false,
    removeLighting: aiModel === "meshy-6" ? values.removeLighting !== false : undefined,
  };
}

/** Retexture one pending review project and stream progress back to its open card. */
export async function runMeshyRetexture({ jobId, values, emit }) {
  if (!meshyConfigured()) throw new Error("MESHY_API_KEY is not configured.");
  if (ACTIVE_RETEXTURES.has(jobId)) throw new Error("This project is already being retextured.");

  ACTIVE_RETEXTURES.add(jobId);
  let job = null;

  try {
    job = await readJob(jobId);
    if (!job) throw new Error("Meshy project not found.");
    if (job.status !== "succeeded" || job.retentionStatus !== "pending") {
      throw new Error("Retexture is available while a successful model is waiting for review on the VPS.");
    }
    if (
      job.retextureStatus === "running" &&
      Date.now() - Number(job.retextureStartedAt || 0) < STALE_RUN_MS
    ) {
      throw new Error("This project already has an active Retexture task.");
    }

    const sourceTaskId = job.outputMeshyTaskId || job.meshyTaskId;
    if (!sourceTaskId) throw new Error("This older project has no Meshy task id to retexture.");

    const settings = normalizeSettings(values);
    const estimatedCredits = settings.textureResolution === "8k" ? 15 : 10;
    const version = (job.retextures || []).length + 1;
    const outputBase = `${job.id}-retexture-${String(version).padStart(2, "0")}`;

    job.retextureStatus = "running";
    job.retextureError = null;
    job.retextureStartedAt = Date.now();
    await saveJob(job);
    emit({ type: "job", job });
    emit({ type: "step", line: `Retexture ${version} · ${settings.textureResolution}` });

    const balance = await getBalance();
    emit({
      type: "stdout",
      line: `Meshy balance: ${balance} credits. Retexture is estimated at ${estimatedCredits}.`,
    });
    if (balance < estimatedCredits) {
      throw new Error(`Not enough Meshy credits: ${balance} left, ${estimatedCredits} needed.`);
    }

    const payload = {
      input_task_id: sourceTaskId,
      text_style_prompt: settings.prompt,
      ai_model: settings.aiModel,
      enable_original_uv: settings.enableOriginalUv,
      enable_pbr: settings.enablePbr,
      texture_resolution: settings.textureResolution,
      target_formats: settings.targetFormats,
      alpha_thumbnail: true,
      ...(settings.removeLighting === undefined
        ? {}
        : { remove_lighting: settings.removeLighting }),
    };

    emit({ type: "cmd", line: `POST retexture ${JSON.stringify(payload)}` });
    const taskId = await createTask("retexture", payload);
    job.activeRetextureTaskId = taskId;
    await saveJob(job);
    emit({ type: "stdout", line: `Retexture task ${taskId} accepted.` });

    const task = await waitForTask("retexture", taskId, {
      onUpdate: (update) =>
        emit({
          type: "progress",
          percent: Number(update.progress ?? 0),
          status: update.status,
          line: `retexture ${update.status} ${update.progress ?? 0}%`,
        }),
    });

    const directory = jobDir(job.id);
    const downloads = collectRetextureDownloads(task, settings.targetFormats, outputBase);
    if (!downloads.some((item) => item.name.endsWith(".glb"))) {
      throw new Error("Meshy returned no GLB for the Retexture preview.");
    }

    emit({ type: "step", line: `Downloading ${downloads.length} Retexture file(s)` });
    for (const item of downloads) {
      await downloadTo(item.url, path.join(directory, item.name));
      emit({ type: "stdout", line: `  ${item.name}` });
    }
    await repairCompanionReferences(directory, downloads);

    const consumedCredits = Number(task?.consumed_credits || estimatedCredits);
    const finishedAt = Date.now();
    job.files = await indexJobFiles(job.id);
    job.retextures = [
      ...(job.retextures || []),
      {
        version,
        taskId,
        sourceTaskId,
        prompt: settings.prompt,
        aiModel: settings.aiModel,
        textureResolution: settings.textureResolution,
        enableOriginalUv: settings.enableOriginalUv,
        enablePbr: settings.enablePbr,
        targetFormats: settings.targetFormats,
        consumedCredits,
        createdAt: job.retextureStartedAt,
        finishedAt,
        previewPath: `${job.id}/${outputBase}.glb`,
        files: downloads.map((item) => `${job.id}/${item.name}`),
      },
    ];
    job.retextureStatus = "succeeded";
    job.retextureError = null;
    job.retextureFinishedAt = finishedAt;
    job.latestRetextureTaskId = taskId;
    job.activeRetextureTaskId = null;
    await saveJob(job);

    emit({ type: "job", job });
    emit({ type: "stdout", line: `Done. Meshy charged ${consumedCredits} Retexture credits.` });
    return job;
  } catch (error) {
    if (job) {
      job.retextureStatus = "failed";
      job.retextureError = error.message;
      job.retextureFinishedAt = Date.now();
      job.activeRetextureTaskId = null;
      job.files = await indexJobFiles(job.id).catch(() => job.files || []);
      await saveJob(job).catch(() => {});
      emit({ type: "job", job });
    }
    throw error;
  } finally {
    ACTIVE_RETEXTURES.delete(jobId);
  }
}
