"use client";

/*
 * ═══════════════════════════════════════════════════════════════
 * Review Client
 * ═══════════════════════════════════════════════════════════════
 * Path: src/components/ReviewClient.jsx
 * Purpose: Step 4 - every finished generation, turned and judged before
 *          anything is committed to glass.
 *
 * A step of its own because this is the real decision point: a Meshy bust
 * that looks fine as a thumbnail can have a collapsed back, and finding that
 * out after an hour of point-cloud sampling is the expensive way.
 */

import { useCallback, useState } from "react";

import JobResults from "@/components/JobResults";
import { useLanguage } from "@/components/LanguageProvider";

const CARD = "rounded-xl border border-surface-border bg-surface p-6";

export default function ReviewClient({ initialJobs = [], onSendToConverter }) {
  const { t } = useLanguage();
  const [jobs, setJobs] = useState(initialJobs);
  const [filter, setFilter] = useState("all");
  const [notice, setNotice] = useState(null);

  const refresh = useCallback(async () => {
    try {
      const response = await fetch("/api/meshy/state", { cache: "no-store" });
      const data = await response.json();
      setJobs(data.jobs || []);
    } catch {
      // A listing failure is not worth an error banner.
    }
  }, []);

  const shown = jobs.filter((job) => (filter === "all" ? true : job.status === filter));

  const counts = {
    all: jobs.length,
    succeeded: jobs.filter((job) => job.status === "succeeded").length,
    failed: jobs.filter((job) => job.status === "failed").length,
  };

  return (
    <div className="space-y-8">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold">{t("Review")}</h1>
        <p className="max-w-3xl text-sm text-muted">
          {t("Drag to orbit, scroll to zoom. Check the back of the head and the sides before sending anything to the converter — one view of a photograph is all Meshy had to work from.")}
        </p>
      </header>

      {notice ? (
        <div
          className={`rounded-lg border px-4 py-3 text-sm ${
            notice.tone === "ok"
              ? "border-surface-border bg-surface-sunken text-success-text"
              : "border-danger-border bg-danger-soft text-danger-text"
          }`}
        >
          {notice.text}
        </div>
      ) : null}

      <section className={`${CARD} space-y-4`}>
        {/* Filter and refresh */}
        <div className="flex flex-wrap items-center gap-2">
          {[
            { id: "all", label: t("All") },
            { id: "succeeded", label: t("Finished") },
            { id: "failed", label: t("Failed") },
          ].map((option) => (
            <button
              key={option.id}
              type="button"
              onClick={() => setFilter(option.id)}
              className={`rounded-md border px-3 py-1.5 text-sm transition ${
                filter === option.id
                  ? "border-accent bg-accent-soft text-accent-soft-text"
                  : "border-input-border bg-input-background text-muted hover:border-accent"
              }`}
            >
              {option.label}
              <span className="ml-1.5 font-mono text-xs opacity-70">{counts[option.id]}</span>
            </button>
          ))}
          <button
            type="button"
            onClick={refresh}
            className="ml-auto text-xs text-muted transition hover:text-foreground"
          >
            {t("refresh")}
          </button>
        </div>

        <JobResults
          jobs={shown}
          onSendToConverter={onSendToConverter}
          onNotice={setNotice}
          onProjectChange={(action, updatedJob) => {
            setJobs((current) =>
              action === "discard"
                ? current.filter((job) => job.id !== updatedJob?.id)
                : current.map((job) => (job.id === updatedJob?.id ? updatedJob : job)),
            );
          }}
          openId={shown[0]?.id}
          emptyText={
            filter === "all"
              ? "Nothing generated yet. Step 3 makes the models."
              : `No ${filter} jobs.`
          }
        />
      </section>
    </div>
  );
}
