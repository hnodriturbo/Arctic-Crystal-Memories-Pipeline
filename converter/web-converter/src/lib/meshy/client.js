/*
 * ═══════════════════════════════════════════════════════════════
 * Meshy API Client
 * ═══════════════════════════════════════════════════════════════
 * Path: src/lib/meshy/client.js
 * Purpose: Every call this app makes to api.meshy.ai, in one place.
 *
 * Meshy is asynchronous throughout - a create call returns a task id and
 * nothing else, so almost every useful operation is create-then-poll.
 */

import { createWriteStream } from "node:fs";
import { mkdir } from "node:fs/promises";
import path from "node:path";
import { Readable } from "node:stream";
import { pipeline } from "node:stream/promises";

const API_URL = (process.env.MESHY_API_URL || "https://api.meshy.ai/openapi").replace(/\/+$/, "");

// Meshy versions its endpoints per feature, not globally, so the version is
// part of the route rather than a shared prefix.
const ENDPOINTS = {
  "text-to-image": "v1/text-to-image",
  "image-to-image": "v1/image-to-image",
  "image-to-3d": "v1/image-to-3d",
  "multi-image-to-3d": "v1/multi-image-to-3d",
  "text-to-3d": "v2/text-to-3d",
  remesh: "v1/remesh",
};

/** The key is optional at build time, so every route checks before calling. */
export function meshyConfigured() {
  return Boolean(process.env.MESHY_API_KEY);
}

/** Turn Meshy's terse `{message}` errors into something a user can act on. */
function describeError(status, body) {
  const detail = body?.message || body?.error || "";

  if (status === 401) return "Meshy rejected the API key. Check MESHY_API_KEY in .env.local.";
  if (status === 402) return "Out of Meshy credits. Top up at meshy.ai, then run this again.";
  if (status === 429) {
    return detail.includes("NoMoreConcurrentTasks")
      ? "Meshy is already running your plan's maximum number of tasks. Wait for one to finish."
      : "Too many requests to Meshy in one second. Wait a moment and retry.";
  }
  if (status === 404) return "Meshy has no such task - it may have expired or been deleted.";
  if (status >= 500) return `Meshy server error (${status}). ${detail}`.trim();
  return detail || `Meshy returned ${status}.`;
}

/** One authenticated request. Throws with a readable message on any non-2xx. */
async function meshyFetch(route, init = {}) {
  if (!meshyConfigured()) {
    throw new Error("MESHY_API_KEY is not set. Add it to .env.local and restart the dev server.");
  }

  const response = await fetch(`${API_URL}/${route}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${process.env.MESHY_API_KEY}`,
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      ...init.headers,
    },
  });

  const text = await response.text();
  let body = null;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = { message: text.slice(0, 400) };
  }

  if (!response.ok) {
    const error = new Error(describeError(response.status, body));
    error.status = response.status;
    throw error;
  }
  return body;
}

/** Remaining credits, so the UI can warn before a job that cannot pay for itself. */
export async function getBalance() {
  const body = await meshyFetch("v1/balance");
  return Number(body?.balance ?? 0);
}

/** Create a task. Returns the task id; nothing is generated yet. */
export async function createTask(kind, payload) {
  const route = ENDPOINTS[kind];
  if (!route) throw new Error(`Unknown Meshy task kind: ${kind}`);

  const body = await meshyFetch(route, { method: "POST", body: JSON.stringify(payload) });
  const id = body?.result;
  if (!id) throw new Error("Meshy accepted the request but returned no task id.");
  return id;
}

/** Current state of one task, including progress and model_urls once it succeeds. */
export async function getTask(kind, id) {
  const route = ENDPOINTS[kind];
  if (!route) throw new Error(`Unknown Meshy task kind: ${kind}`);
  return meshyFetch(`${route}/${encodeURIComponent(id)}`);
}

const TERMINAL = new Set(["SUCCEEDED", "FAILED", "CANCELED"]);

/**
 * Poll until the task stops moving, reporting each change.
 *
 * Polling rather than the /stream SSE endpoint: this route is already
 * streaming its own SSE to the browser, and nesting one event stream inside
 * another buys nothing but a second failure mode on a long generation.
 */
export async function waitForTask(kind, id, { onUpdate, signal, intervalMs } = {}) {
  const wait = Number(intervalMs || process.env.MESHY_POLL_INTERVAL_MS || 3000);
  let lastProgress = -1;
  let lastStatus = "";

  for (;;) {
    if (signal?.aborted) throw new Error("Cancelled.");

    const task = await getTask(kind, id);
    const status = task?.status || "PENDING";
    const progress = Number(task?.progress ?? 0);

    // Only report movement; a 3-second poll on a 4-minute job is otherwise 80
    // identical lines of console noise.
    if (status !== lastStatus || progress !== lastProgress) {
      lastStatus = status;
      lastProgress = progress;
      onUpdate?.(task);
    }

    if (TERMINAL.has(status)) {
      if (status !== "SUCCEEDED") {
        const reason = task?.task_error?.message || status.toLowerCase();
        throw new Error(`Meshy task ${status}: ${reason}`);
      }
      return task;
    }

    await new Promise((resolve) => setTimeout(resolve, wait));
  }
}

/**
 * Stream one model file to disk.
 *
 * No Authorization header on purpose - model_urls are already presigned and
 * time-limited, and the CDN has no business seeing the API key.
 */
export async function downloadTo(url, destinationPath) {
  await mkdir(path.dirname(destinationPath), { recursive: true });

  const response = await fetch(url);
  if (!response.ok || !response.body) {
    throw new Error(`Download failed (${response.status}) for ${path.basename(destinationPath)}`);
  }

  await pipeline(Readable.fromWeb(response.body), createWriteStream(destinationPath));
  return destinationPath;
}
