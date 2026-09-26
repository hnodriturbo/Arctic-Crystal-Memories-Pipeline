/*
 * ═══════════════════════════════════════════════════════════════
 * Claude Design Render Jobs
 * ═══════════════════════════════════════════════════════════════
 * Path: src/lib/claude-design/render-jobs.js
 * Purpose: Hold the render queue, spawn one renderer at a time, and push every
 *          line it prints out to the console panel as it happens.
 *
 * One at a time, deliberately. Rendering saturates the CPU, and this VPS also
 * serves www.acm.is: two concurrent renders would each be worse than half
 * speed and would make the live shop feel slow while they ran. Queued, the
 * first video is also simply finished sooner.
 *
 * The state hangs off globalThis because `next dev` re-evaluates modules on
 * every save. Without that, a queue would empty itself each time a file is
 * edited while a render is running.
 */

import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

import { DESIGN_ROOT, EXPORT_ROOT, R2_VIDEO_PREFIX, safeJoin } from "./paths";
import { putFile, workshopR2Configured } from "@/lib/storage/workshop-r2";

const RENDERER = path.join(process.cwd(), "scripts", "render-design-video.mjs");

// ========================================
// State
// ========================================

const store =
  globalThis.__acmDesignRenderStore ??
  (globalThis.__acmDesignRenderStore = {
    jobs: new Map(),
    queue: [],
    activeId: null,
    listeners: new Set(),
    counter: 0,
  });

/** Push one event to every open stream, dropping connections that have gone away. */
function broadcast(event) {
  for (const send of store.listeners) {
    try {
      send(event);
    } catch {
      store.listeners.delete(send);
    }
  }
}

export function subscribe(send) {
  store.listeners.add(send);
  return () => store.listeners.delete(send);
}

/** The browser's view of a job. The log is trimmed so a poll stays small. */
function publicJob(job) {
  return {
    id: job.id,
    label: job.label,
    collection: job.collection,
    outName: job.outName,
    status: job.status,
    pct: job.pct,
    etaSec: job.etaSec,
    frames: job.frames,
    frame: job.frame,
    width: job.width,
    height: job.height,
    fps: job.fps,
    seconds: job.seconds,
    keepChrome: job.keepChrome,
    uploadedKey: job.uploadedKey,
    error: job.error,
    startedAt: job.startedAt,
    finishedAt: job.finishedAt,
    log: job.log.slice(-200),
  };
}

export function listJobs() {
  return [...store.jobs.values()].map(publicJob);
}

// ========================================
// Queueing
// ========================================

/**
 * spec: { rootRel, collection, outName, width, height, fps, crf, seconds,
 *         siteScale, keepChrome }
 * `rootRel` is the design's path relative to the Claude Design root.
 */
export function enqueue(spec) {
  const sourceAbsolute = safeJoin(DESIGN_ROOT, spec.rootRel);
  if (!sourceAbsolute || !fs.existsSync(sourceAbsolute)) {
    throw new Error(`Design not found: ${spec.rootRel}`);
  }

  const collection = String(spec.collection || "untitled").replace(/[\\/:*?"<>|]/g, "-");
  const outDir = safeJoin(EXPORT_ROOT, collection);
  if (!outDir) throw new Error("Invalid collection name");

  // The file name is cleaned here rather than in the browser, because the
  // browser is not trusted to have done it.
  const outName =
    (spec.outName || path.basename(sourceAbsolute).replace(/\.dc\.html$/i, "").replace(/\.html$/i, ""))
      .replace(/[\\/:*?"<>|]/g, "-")
      .replace(/\.mp4$/i, "") + ".mp4";

  const crf = spec.crf == null ? 18 : Number(spec.crf);
  if (!Number.isInteger(crf) || crf < 0 || crf > 51) throw new Error("CRF must be an integer from 0 to 51.");

  const id = `render-${++store.counter}-${Date.now()}`;
  const job = {
    id,
    label: path.basename(sourceAbsolute),
    collection,
    sourceAbsolute,
    outDir,
    outName,
    outPath: path.join(outDir, outName),
    posterPath: path.join(outDir, outName.replace(/\.mp4$/i, ".jpg")),
    width: Number(spec.width) || 1920,
    height: Number(spec.height) || 1080,
    fps: Number(spec.fps) || 60,
    crf,
    seconds: spec.seconds ? Number(spec.seconds) : null,
    siteScale: spec.siteScale == null ? 1.6 : Number(spec.siteScale),
    keepChrome: Boolean(spec.keepChrome),
    status: "queued",
    pct: 0,
    etaSec: null,
    frames: null,
    frame: 0,
    uploadedKey: null,
    error: null,
    startedAt: null,
    finishedAt: null,
    log: [],
    child: null,
  };

  store.jobs.set(id, job);
  store.queue.push(id);
  broadcast({ type: "job", job: publicJob(job) });
  pump();
  return publicJob(job);
}

export function cancel(id) {
  const job = store.jobs.get(id);
  if (!job) return false;

  if (job.status === "queued") {
    store.queue = store.queue.filter((queued) => queued !== id);
    job.status = "cancelled";
    job.finishedAt = Date.now();
    broadcast({ type: "job", job: publicJob(job) });
    return true;
  }

  if (job.status === "running" && job.child) {
    job.cancelled = true;
    // A signal alone does not take the process tree down on Windows, and ffmpeg
    // is a child of the renderer - taskkill /t is what actually stops both.
    if (process.platform === "win32") {
      spawn("taskkill", ["/pid", String(job.child.pid), "/f", "/t"], { stdio: "ignore" });
    } else {
      job.child.kill("SIGKILL");
    }
    return true;
  }
  return false;
}

export function clearFinished() {
  for (const [id, job] of store.jobs) {
    if (["done", "error", "cancelled"].includes(job.status)) store.jobs.delete(id);
  }
  broadcast({ type: "reset" });
}

// ========================================
// Running
// ========================================

/** Start the next job whenever nothing is running. */
function pump() {
  if (store.activeId || !store.queue.length) return;
  const id = store.queue.shift();
  const job = store.jobs.get(id);
  if (!job) return pump();
  store.activeId = id;
  run(job);
}

function pushLine(job, line) {
  job.log.push(line);
  if (job.log.length > 500) job.log.shift();
  broadcast({ type: "log", id: job.id, line });
}

function run(job) {
  fs.mkdirSync(job.outDir, { recursive: true });

  const args = [
    RENDERER,
    "--dir", path.dirname(job.sourceAbsolute),
    "--file", path.basename(job.sourceAbsolute),
    "--out", job.outPath,
    "--poster", job.posterPath,
    "--size", `${job.width}x${job.height}`,
    "--fps", String(job.fps),
    "--crf", String(job.crf),
    "--site-scale", String(job.siteScale),
    "--json-progress",
  ];
  if (job.seconds) args.push("--seconds", String(job.seconds));
  if (job.keepChrome) args.push("--keep-chrome");
  // The renderer serves the design tree itself, on loopback, for the length of
  // this job. Going through the application instead would mean an
  // unauthenticated request redirected to the public sign-in URL, where a
  // headless browser meets Cloudflare's bot check and renders that.
  args.push("--serve-root", DESIGN_ROOT);

  job.status = "running";
  job.startedAt = Date.now();
  pushLine(job, `$ node ${args.slice(1).join(" ")}`);
  broadcast({ type: "job", job: publicJob(job) });

  const child = spawn(process.execPath, args, { cwd: process.cwd() });
  job.child = child;

  // stdout arrives in arbitrary chunks; lines are reassembled here so a
  // progress frame is never split down the middle.
  let buffer = "";
  const onChunk = (chunk) => {
    buffer += chunk.toString();
    const lines = buffer.split(/\r?\n/);
    buffer = lines.pop();
    for (const line of lines) handleLine(job, line);
  };
  child.stdout.on("data", onChunk);
  child.stderr.on("data", onChunk);

  child.on("close", async (code) => {
    if (buffer.trim()) handleLine(job, buffer);
    buffer = "";
    job.child = null;

    if (job.cancelled) {
      job.status = "cancelled";
    } else if (code === 0 && fs.existsSync(job.outPath)) {
      job.status = "uploading";
      job.pct = 100;
      broadcast({ type: "job", job: publicJob(job) });
      await publish(job);
    } else {
      job.status = "error";
      job.error = job.error || `The renderer exited with code ${code}`;
    }

    job.finishedAt = Date.now();
    broadcast({ type: "job", job: publicJob(job) });
    store.activeId = null;
    pump();
  });
}

/**
 * Put the finished video in R2.
 *
 * A failed upload does not fail the job: the mp4 is on disk and can be pushed
 * up again, and marking a render that actually succeeded as an error would be
 * a lie about where the work stands.
 */
async function publish(job) {
  if (!workshopR2Configured()) {
    pushLine(job, "  ccm-workshop is not configured - the video stays local only");
    job.status = "done";
    return;
  }

  const key = `${R2_VIDEO_PREFIX}${job.collection}/${job.outName}`;
  try {
    pushLine(job, `  uploading to ${key}`);
    await putFile(job.outPath, key, {
      width: String(job.width),
      height: String(job.height),
      fps: String(job.fps),
    });

    if (fs.existsSync(job.posterPath)) {
      const posterKey = key.replace(/\.mp4$/i, ".jpg");
      await putFile(job.posterPath, posterKey);
      pushLine(job, `  uploading to ${posterKey}`);
    }

    job.uploadedKey = key;
    job.status = "done";
    pushLine(job, "  stored in ccm-workshop");
  } catch (error) {
    job.status = "done";
    job.error = `Rendered, but the upload failed: ${error.message}`;
    pushLine(job, `  !! upload failed: ${error.message}`);
  }
}

/**
 * Lines beginning with @@ are machine-readable progress from the renderer.
 * Everything else is ordinary output and goes straight to the console panel.
 */
function handleLine(job, line) {
  const text = line.trimEnd();
  if (!text) return;

  if (text.startsWith("@@")) {
    try {
      const data = JSON.parse(text.slice(2));
      if (data.event === "start") {
        job.frames = data.frames;
        job.seconds = data.seconds;
        job.width = data.width;
        job.height = data.height;
      } else if (data.event === "progress") {
        job.frame = data.frame;
        job.frames = data.frames;
        job.pct = data.pct;
        job.etaSec = data.etaSec;
      } else if (data.event === "error") {
        job.error = data.message;
      }
      broadcast({ type: "job", job: publicJob(job) });
    } catch {
      pushLine(job, text);
    }
    return;
  }
  pushLine(job, text);
}
