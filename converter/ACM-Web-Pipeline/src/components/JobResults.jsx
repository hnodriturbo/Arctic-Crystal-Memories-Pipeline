"use client";

/*
 * ═══════════════════════════════════════════════════════════════
 * Job Results
 * ═══════════════════════════════════════════════════════════════
 * Path: src/components/JobResults.jsx
 * Purpose: Everything a finished generation produced - turn the model,
 *          download any format, or send it on to the converter.
 *
 * Meshy job history renders this over every job; generation screens render it
 * over the current session, so a result can be judged without leaving its form.
 */

import { useState } from "react";

import ModelViewer from "@/components/ModelViewer";
import { useLanguage } from "@/components/LanguageProvider";
import RetextureControls from "@/components/RetextureControls";
import { MESHY_MODES } from "@/lib/meshy/catalog";
import { readResponseJson } from "@/lib/response-json";

const IMAGE_EXTENSIONS = [".png", ".jpg", ".jpeg", ".webp"];

/** Human-readable byte size, because "103948887" tells nobody anything. */
function formatBytes(bytes) {
  if (!bytes) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / 1024 ** index).toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

const fileUrl = (path, download = false) =>
  `/api/file?root=meshy-output&path=${encodeURIComponent(path)}${download ? "&download=1" : ""}`;

/** The GLB a job produced, if it asked for one - the only format the viewer reads. */
function previewModel(job) {
  const latestRetexture = job?.retextures?.at(-1)?.previewPath;
  if (latestRetexture) {
    const texturedPreview = job?.files?.find((file) => file.path === latestRetexture);
    if (texturedPreview) return texturedPreview;
  }
  return job?.files?.find((file) => file.extension === ".glb" && !file.name.includes("pre-remesh"));
}

export default function JobResults({
  jobs = [],
  onSendToConverter,
  onNotice,
  onProjectChange,
  openId,
  emptyText,
}) {
  const { t } = useLanguage();
  const [openJob, setOpenJob] = useState(openId ?? null);
  const [busyDecision, setBusyDecision] = useState(null);

  /** Archive only after review, or explicitly discard the complete VPS project. */
  async function decideProject(job, action) {
    if (
      action === "discard" &&
      !window.confirm(
        `Discard ${job.id} and every local output file? This cannot be undone and nothing will be saved to R2.`,
      )
    ) {
      return;
    }

    setBusyDecision(`${action}:${job.id}`);
    onNotice?.(null);
    try {
      const response = await fetch("/api/meshy/project", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action, jobId: job.id }),
      });
      const data = await readResponseJson(response);
      if (!response.ok) throw new Error(data.error || "Project decision failed");

      onProjectChange?.(action, data.job || data.result);
      onNotice?.({
        tone: "ok",
        text:
          action === "archive"
            ? `${job.id} is verified in R2 and its large VPS files were removed.`
            : `${job.id} was discarded from the VPS.`,
      });
    } catch (error) {
      onNotice?.({ tone: "error", text: error.message });
    } finally {
      setBusyDecision(null);
    }
  }

  /** Push one produced file into whichever pipeline consumes it next. */
  async function handOff(job, file, to) {
    try {
      const response = await fetch("/api/handoff", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ from: "meshy-output", to, path: file.path, jobId: job.id }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Handoff failed");

      if (to === "converter-input") onSendToConverter?.(data);
      else onNotice?.({ tone: "ok", text: `${data.file.name} is now in the Meshy input folder.` });
    } catch (error) {
      onNotice?.({ tone: "error", text: error.message });
    }
  }

  if (!jobs.length) {
    return <p className="text-sm text-muted">{t(emptyText || "Nothing generated yet.")}</p>;
  }

  return (
    <ul className="space-y-3">
      {jobs.map((job) => {
        const open = openJob === job.id;
        const preview = previewModel(job);
        const obj = job.files?.find((file) => file.extension === ".obj");
        const pictures = (job.files || []).filter((file) =>
          IMAGE_EXTENSIONS.includes(file.extension),
        );
        const producedImages = MESHY_MODES[job.mode]?.produces === "image";

        return (
          <li key={job.id} className="rounded-lg border border-surface-border">
            {/* Summary row - what it was, what it cost, how it ended */}
            <button
              type="button"
              onClick={() => setOpenJob(open ? null : job.id)}
              className="flex w-full items-center justify-between gap-4 px-4 py-3 text-left transition hover:bg-surface-hover"
            >
              <div className="min-w-0">
                <p className="truncate text-sm">{job.id}</p>
                <p className="truncate font-mono text-xs text-muted">
                  {MESHY_MODES[job.mode]?.label || job.mode}
                  {job.crystalTemplate ? ` · ${job.crystalTemplate}` : ""}
                  {job.consumedCredits ? ` · ${job.consumedCredits} credits` : ""}
                  {job.retentionStatus === "archived" || job.storage === "r2"
                    ? ` · ${t("R2 archive")}`
                    : job.retentionStatus === "pending"
                      ? ` · ${t("awaiting review decision")}`
                      : ""}
                </p>
              </div>
              <span
                className={`shrink-0 font-mono text-xs ${
                  job.status === "succeeded"
                    ? "text-success-text"
                    : job.status === "failed"
                      ? "text-danger-text"
                      : "text-warning-text"
                }`}
              >
                {t(job.status)}
              </span>
            </button>

            {open ? (
              <div className="space-y-4 border-t border-surface-border px-4 py-4">
                {job.error ? (
                  <p className="rounded-md border border-danger-border bg-danger-soft px-3 py-2 text-xs text-danger-text">
                    {job.error}
                  </p>
                ) : null}
                {job.textureWarning ? (
                  <p className="rounded-md border border-warning-border bg-warning-soft px-3 py-2 text-xs text-warning-text">
                    {job.textureWarning}
                  </p>
                ) : null}

                {job.retentionStatus === "pending" || job.retentionStatus === "failed-review" ? (
                  <div className="rounded-lg border border-warning-border bg-warning-soft p-4">
                    <p className="text-sm font-medium text-warning-text">
                      {job.retentionStatus === "pending"
                        ? t("Review the local GLB, then keep or discard this complete project.")
                        : t("This project failed. Discard its local files before starting another 3D job.")}
                    </p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {job.retentionStatus === "pending" ? (
                        <button
                          type="button"
                          onClick={() => decideProject(job, "archive")}
                          disabled={Boolean(busyDecision) || job.retextureStatus === "running"}
                          className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-foreground transition hover:bg-accent-hover disabled:opacity-50"
                        >
                          {busyDecision === `archive:${job.id}`
                            ? t("Archiving and verifying…")
                            : t("Keep in R2 and clear VPS")}
                        </button>
                      ) : null}
                      <button
                        type="button"
                        onClick={() => decideProject(job, "discard")}
                        disabled={Boolean(busyDecision) || job.retextureStatus === "running"}
                        className="rounded-lg border border-danger-border px-4 py-2 text-sm text-danger-text transition hover:bg-danger-soft disabled:opacity-50"
                      >
                        {busyDecision === `discard:${job.id}`
                          ? t("Discarding…")
                          : t("Discard this project")}
                      </button>
                    </div>
                  </div>
                ) : null}

                {job.status === "succeeded" && job.retentionStatus === "pending" ? (
                  <RetextureControls
                    job={job}
                    onJobUpdated={(updatedJob) => onProjectChange?.("retexture", updatedJob)}
                    onNotice={onNotice}
                  />
                ) : null}

                {/* A 2D job shows its pictures and offers them to the 3D step */}
                {producedImages ? (
                  <div className="grid gap-3 sm:grid-cols-3">
                    {pictures.map((file) => (
                      <figure key={file.path} className="space-y-2">
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img
                          src={fileUrl(file.path)}
                          alt={file.name}
                          className="aspect-square w-full rounded-lg border border-surface-border object-contain"
                        />
                        <figcaption className="flex items-center gap-2">
                          <button
                            type="button"
                            onClick={() => handOff(job, file, "meshy-input")}
                            className="rounded-md bg-accent px-2 py-1 text-[10px] font-medium text-accent-foreground transition hover:bg-accent-hover"
                          >
                            {t("Use for 3D →")}
                          </button>
                          <a
                            href={fileUrl(file.path, true)}
                            className="rounded-md border border-surface-border px-2 py-1 text-[10px] transition hover:border-accent hover:text-accent"
                          >
                            {t("download")}
                          </a>
                        </figcaption>
                      </figure>
                    ))}
                  </div>
                ) : (
                  <div className="space-y-4">
                    {/* Keep the orbit preview above the full-width artifact list. */}
                    {preview ? (
                      <ModelViewer
                        src={fileUrl(preview.path)}
                        alt={`Model from ${job.id}`}
                        aspectClassName="aspect-video"
                      />
                    ) : (
                      <div className="flex aspect-video items-center justify-center rounded-lg border border-dashed border-surface-border p-6">
                        <p className="text-center text-xs text-muted">
                          {t("No GLB in this job, so there is nothing to turn. Add glb to the download formats to get one.")}
                        </p>
                      </div>
                    )}

                    <div className="space-y-2">
                      {obj ? (
                        <button
                          type="button"
                          onClick={() => handOff(job, obj, "converter-input")}
                          className="w-full rounded-lg bg-accent px-4 py-2.5 text-sm font-medium text-accent-foreground transition hover:bg-accent-hover"
                        >
                          {t("Send to converter →")}
                        </button>
                      ) : (
                        <p className="rounded-md border border-warning-border bg-warning-soft px-3 py-2 text-xs text-warning-text">
                          {t("No OBJ in this job. The converter reads OBJ and mesh DXF only.")}
                        </p>
                      )}

                      <ul className="divide-y divide-surface-border">
                        {(job.files || []).map((file) => (
                          <li
                            key={file.path}
                            className="grid gap-2 py-2 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center"
                          >
                            <span className="min-w-0 break-all font-mono text-xs leading-relaxed">
                              {file.name}
                            </span>
                            <span className="flex items-center gap-2 sm:justify-self-end">
                              <span className="font-mono text-[10px] text-muted">
                                {formatBytes(file.bytes)}
                              </span>
                              <a
                                href={fileUrl(file.path, true)}
                                className="rounded-md border border-surface-border px-2 py-0.5 text-[10px] transition hover:border-accent hover:text-accent"
                              >
                                {t("download")}
                              </a>
                            </span>
                          </li>
                        ))}
                      </ul>

                      {job.r2?.error ? (
                        <p className="text-[10px] text-warning-text">
                          R2 mirror failed: {job.r2.error}
                        </p>
                      ) : null}
                    </div>
                  </div>
                )}
              </div>
            ) : null}
          </li>
        );
      })}
    </ul>
  );
}
