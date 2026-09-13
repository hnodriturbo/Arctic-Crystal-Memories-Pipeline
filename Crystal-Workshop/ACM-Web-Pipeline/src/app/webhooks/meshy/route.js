/*
 * ═══════════════════════════════════════════════════════════════
 * Meshy Webhook
 * ═══════════════════════════════════════════════════════════════
 * Path: src/app/webhooks/meshy/route.js
 * Purpose: Receive Meshy's task-status callbacks at
 *          https://pipeline.acm.is/webhooks/meshy
 *
 * Not under /api on purpose - the URL registered in Meshy's portal is
 * /webhooks/meshy, and a route handler does not have to live under /api to
 * answer one.
 *
 * The runner still polls, so nothing depends on this arriving. What it buys
 * is a job whose manifest finishes correctly even when the browser tab that
 * started it was closed mid-generation.
 */

import { createHmac, timingSafeEqual } from "node:crypto";
import { appendFile, mkdir } from "node:fs/promises";
import path from "node:path";

import { indexJobFiles, listJobs, saveJob } from "@/lib/meshy/jobs";
import { MESHY_ROOT } from "@/lib/paths";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// Meshy's own docs do not name the signature header or its algorithm. Rather
// than guess one and silently accept everything, every plausible name is
// checked, and the first real delivery's headers are written to
// meshy-pipeline/webhook-headers.log so the scheme can be pinned down from
// evidence instead.
const SIGNATURE_HEADERS = [
  "x-meshy-signature",
  "meshy-signature",
  "x-webhook-signature",
  "x-signature",
  "x-hub-signature-256",
];

/** Constant-time compare that tolerates length mismatches. */
function matches(a, b) {
  const left = Buffer.from(a);
  const right = Buffer.from(b);
  if (left.length !== right.length) return false;
  return timingSafeEqual(left, right);
}

/** HMAC-SHA256 of the raw body, in both encodings Meshy might use. */
function signatureOk(rawBody, provided) {
  const secret = process.env.MESHY_WEBHOOK_SECRET;
  if (!secret) return false;

  const digest = createHmac("sha256", secret).update(rawBody);
  const hex = digest.copy().digest("hex");
  const base64 = digest.digest("base64");

  const candidate = provided.replace(/^sha256[=\s]/i, "").trim();
  return matches(candidate, hex) || matches(candidate, base64);
}

/** Keep one record of what a real delivery looks like, so this can be tightened. */
async function recordHeaders(request) {
  try {
    await mkdir(MESHY_ROOT, { recursive: true });
    const headers = Object.fromEntries(request.headers.entries());
    delete headers.authorization;
    await appendFile(
      path.join(MESHY_ROOT, "webhook-headers.log"),
      `${new Date().toISOString()} ${JSON.stringify(headers)}\n`,
      "utf8",
    );
  } catch {
    // Diagnostics must never turn a delivery into a failure.
  }
}

export async function POST(request) {
  const rawBody = await request.text();

  const providedHeader = SIGNATURE_HEADERS.map((name) => request.headers.get(name)).find(Boolean);
  const signed = providedHeader ? signatureOk(rawBody, providedHeader) : false;
  if (!providedHeader) await recordHeaders(request);

  let payload;
  try {
    payload = JSON.parse(rawBody);
  } catch {
    return Response.json({ error: "Body is not JSON" }, { status: 400 });
  }

  const taskId = payload?.id;
  if (!taskId) {
    return Response.json({ error: "No task id in payload" }, { status: 400 });
  }

  // Authorisation, in order of strength: a verified signature, or - while the
  // signature scheme is still unknown - the task id matching a job this
  // installation actually started. An unknown id is refused either way, so a
  // stranger posting here changes nothing.
  const job = (await listJobs()).find((item) => item.meshyTaskId === taskId);
  if (!signed && !job) {
    return Response.json({ error: "Unknown task" }, { status: 404 });
  }
  if (!job) {
    // Signed, but for a job this box has no record of. Nothing to update.
    return Response.json({ ok: true, note: "No local job for that task" });
  }

  // Only fill in an ending the poller missed; a live run owns its own manifest.
  if (job.status === "running") {
    const status = payload.status;
    if (status === "SUCCEEDED") {
      job.status = "succeeded";
      job.finishedAt = Date.now();
      job.consumedCredits = Number(payload.consumed_credits || job.estimatedCredits);
      job.files = await indexJobFiles(job.id).catch(() => []);
      job.note = "Completed via webhook - model files were not downloaded automatically.";
      await saveJob(job);
    } else if (status === "FAILED" || status === "CANCELED") {
      job.status = "failed";
      job.finishedAt = Date.now();
      job.error = payload?.task_error?.message || String(status).toLowerCase();
      await saveJob(job);
    }
  }

  // Meshy disables a webhook that keeps erroring, so acknowledge and stop.
  return Response.json({ ok: true, signatureVerified: signed });
}
