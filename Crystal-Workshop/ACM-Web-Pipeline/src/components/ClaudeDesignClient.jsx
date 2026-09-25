"use client";

/*
 * ═══════════════════════════════════════════════════════════════
 * Claude Design Client
 * ═══════════════════════════════════════════════════════════════
 * Path: src/components/ClaudeDesignClient.jsx
 * Purpose: The animations workspace - look at a design, decide what the video
 *          should be, render it, and play the result back out of R2.
 *
 * Preview before render, deliberately. A render costs tens of minutes, and the
 * usual reason one is wasted is that a scene was cut off or an asset had not
 * been moved into place. Both are visible in a few seconds in the frame.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import ConsoleLog from "@/components/ConsoleLog";
import SettingHelp from "@/components/SettingHelp";
import DesignPreviewFrame from "@/components/DesignPreviewFrame";
import { useLanguage } from "@/components/LanguageProvider";

// ========================================
// Frame sizes
// ========================================

// Grouped by aspect ratio, because that is the decision that actually gets made
// first - where the video is going - and the pixel count follows from it.
const RATIOS = [
  {
    id: "16:9",
    label: "16:9 · landscape",
    sizes: [
      { label: "1280 × 720", width: 1280, height: 720 },
      { label: "1920 × 1080", width: 1920, height: 1080 },
      { label: "2560 × 1440", width: 2560, height: 1440 },
      { label: "3840 × 2160", width: 3840, height: 2160 },
    ],
  },
  {
    id: "9:16",
    label: "9:16 · reel and story",
    sizes: [
      { label: "720 × 1280", width: 720, height: 1280 },
      { label: "1080 × 1920", width: 1080, height: 1920 },
      { label: "1440 × 2560", width: 1440, height: 2560 },
    ],
  },
  {
    id: "1:1",
    label: "1:1 · square",
    sizes: [
      { label: "1080 × 1080", width: 1080, height: 1080 },
      { label: "1440 × 1440", width: 1440, height: 1440 },
    ],
  },
  {
    id: "4:5",
    label: "4:5 · feed portrait",
    sizes: [{ label: "1080 × 1350", width: 1080, height: 1350 }],
  },
];

const FINISHED = ["done", "error", "cancelled"];

/** Bytes as something readable at a glance rather than exact. */
function megabytes(bytes) {
  if (!bytes) return "—";
  return `${(bytes / 1048576).toFixed(1)} MB`;
}

/** Seconds as m:ss, which is how a video length is actually read. */
function clock(seconds) {
  if (!seconds && seconds !== 0) return "—";
  const whole = Math.round(seconds);
  return `${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, "0")}`;
}

export default function ClaudeDesignClient() {
  const { t } = useLanguage();

  const [library, setLibrary] = useState(null);
  const [remote, setRemote] = useState([]);
  const [loadError, setLoadError] = useState("");
  const [selected, setSelected] = useState([]);
  const [preview, setPreview] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);

  // Render settings. `sizeMode` of "design" means each design keeps the size
  // read from its own file, which is right far more often than one global
  // override - a mobile edition and a desktop edition are usually queued
  // together and want different frames.
  const [sizeMode, setSizeMode] = useState("design");
  const [ratio, setRatio] = useState("16:9");
  const [sizeLabel, setSizeLabel] = useState("1920 × 1080");
  const [fps, setFps] = useState(60);
  const [crf, setCrf] = useState(18);
  const [testSeconds, setTestSeconds] = useState("");
  const [keepChrome, setKeepChrome] = useState(false);
  const [siteScale, setSiteScale] = useState(1.6);
  const [collection, setCollection] = useState("");
  const [newCollection, setNewCollection] = useState("");

  // ========================================
  // Loading
  // ========================================

  // Asking for a reload is a counter rather than a call, so the effect below
  // stays the only thing that touches the library state. Setting it from an
  // effect body directly would cascade renders on every refresh.
  const [reloadCount, setReloadCount] = useState(0);
  const loadLibrary = useCallback(() => setReloadCount((value) => value + 1), []);

  useEffect(() => {
    const controller = new AbortController();

    fetch("/api/claude-design/library", { cache: "no-store", signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error(t("Sign in again to read the design library."));
        return response.json();
      })
      .then((data) => {
        setLibrary(data);
        setLoadError("");
      })
      .catch((error) => {
        if (error.name !== "AbortError") setLoadError(error.message);
      });

    return () => controller.abort();
  }, [reloadCount, t]);

  /*
   * What the bucket holds, listed separately from what is on this disk. On the
   * VPS these are the only collections there are until one is fetched down, so
   * without this list the page would show nothing and offer no way forward.
   */
  useEffect(() => {
    const controller = new AbortController();

    fetch("/api/claude-design/sync", { cache: "no-store", signal: controller.signal })
      .then((response) => (response.ok ? response.json() : { collections: [] }))
      .then((data) => setRemote(data.collections || []))
      .catch(() => {
        // A bucket listing that fails is not worth an error banner; the local
        // library is still usable and the notice line will carry any real failure.
      });

    return () => controller.abort();
  }, [reloadCount]);

  /*
   * One event stream for the whole queue. It carries both job updates and the
   * renderer's console lines, so progress and output can never disagree about
   * what is happening.
   */
  useEffect(() => {
    const source = new EventSource("/api/claude-design/render/stream");

    source.onmessage = (event) => {
      let payload;
      try {
        payload = JSON.parse(event.data);
      } catch {
        return;
      }

      if (payload.type === "snapshot") {
        setJobs(payload.jobs);
      } else if (payload.type === "reset") {
        setJobs([]);
      } else if (payload.type === "job") {
        setJobs((current) => {
          const index = current.findIndex((job) => job.id === payload.job.id);
          if (index < 0) return [...current, payload.job];
          const next = [...current];
          next[index] = { ...next[index], ...payload.job };
          return next;
        });
        // A finished render means a new object in the bucket.
        if (payload.job.status === "done") loadLibrary();
      } else if (payload.type === "log") {
        setJobs((current) =>
          current.map((job) =>
            job.id === payload.id ? { ...job, log: [...(job.log || []), payload.line].slice(-200) } : job,
          ),
        );
      }
    };

    return () => source.close();
  }, [loadLibrary]);

  // ========================================
  // Derived
  // ========================================

  // Memoised because a fresh [] on every render would re-key the lookup below.
  const collections = useMemo(() => library?.collections || [], [library]);
  const capability = library?.capability || { ready: false };

  const designsByPath = useMemo(() => {
    const map = new Map();
    for (const group of collections) {
      for (const design of group.designs) map.set(design.rootRel, { ...design, collection: group.name });
    }
    return map;
  }, [collections]);

  const activeJob = jobs.find((job) => job.status === "running" || job.status === "uploading");
  const queuedCount = jobs.filter((job) => job.status === "queued").length;

  // The console shows whichever render is actually talking, falling back to the
  // most recent one so a finished run's output does not vanish on completion.
  const consoleJob = activeJob || [...jobs].reverse().find((job) => job.log?.length);
  const consoleLines = useMemo(
    () =>
      (consoleJob?.log || []).map((line) => ({
        text: line,
        type: line.startsWith("$")
          ? "cmd"
          : line.includes("!!")
            ? "stderr"
            : line.includes("finished:") || line.includes("stored in")
              ? "done"
              : "stdout",
      })),
    [consoleJob],
  );

  const chosenSize = useMemo(() => {
    const group = RATIOS.find((entry) => entry.id === ratio) || RATIOS[0];
    return group.sizes.find((size) => size.label === sizeLabel) || group.sizes[0];
  }, [ratio, sizeLabel]);

  // ========================================
  // Actions
  // ========================================

  const toggleDesign = (rootRel) => {
    setSelected((current) =>
      current.includes(rootRel) ? current.filter((item) => item !== rootRel) : [...current, rootRel],
    );
  };

  /** Select or clear a whole collection in one click - editions come in sets. */
  const toggleCollection = (group) => {
    const paths = group.designs.map((design) => design.rootRel);
    const allSelected = paths.every((path) => selected.includes(path));
    setSelected((current) =>
      allSelected
        ? current.filter((item) => !paths.includes(item))
        : [...new Set([...current, ...paths])],
    );
  };

  async function startRender() {
    if (!selected.length || collection === "__new__") return;
    setBusy(true);
    setNotice("");

    const items = selected.map((rootRel) => {
      const design = designsByPath.get(rootRel);
      const size = sizeMode === "design" ? { width: design.width, height: design.height } : chosenSize;
      return {
        rootRel,
        collection: collection || design.collection,
        // Both the .dc.html and .html suffixes come off, so the video is named
        // after the design rather than after a file extension.
        outName: design.name.replace(/\.dc\.html$/i, "").replace(/\.html$/i, ""),
        width: size.width,
        height: size.height,
      };
    });

    try {
      const response = await fetch("/api/claude-design/render", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          items,
          fps,
          crf,
          siteScale,
          keepChrome,
          seconds: testSeconds ? Number(testSeconds) : null,
        }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || t("Could not start the render."));

      setNotice(
        data.failed?.length
          ? `${data.jobs.length} ${t("queued")} · ${data.failed.length} ${t("could not be queued")}`
          : `${data.jobs.length} ${t("queued")}`,
      );
      setSelected([]);
    } catch (error) {
      setNotice(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function stopJob(id) {
    await fetch("/api/claude-design/render/cancel", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id }),
    });
  }

  async function clearFinished() {
    await fetch("/api/claude-design/render", { method: "DELETE" });
    setJobs((current) => current.filter((job) => !FINISHED.includes(job.status)));
  }

  async function syncCollection(name) {
    setBusy(true);
    setNotice(t("Synchronizing with R2…"));
    try {
      const response = await fetch("/api/claude-design/sync", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ collection: name, direction: "sync" }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || t("The sync failed."));

      const summary = data.summary;
      setNotice(name + ': ' + summary.uploaded + ' ' + t('uploaded') + ', ' + summary.fetched + ' ' + t('fetched') + ', ' + summary.conflicts + ' ' + t('conflicts — both copies preserved; check the sync log') + '\n' + (data.lines || []).filter(line => line.startsWith('CONFLICT')).join('\n'));
      loadLibrary();
    } catch (error) {
      setNotice(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function createCollection() {
    setBusy(true);
    try {
      const name = newCollection.trim();
      const response = await fetch('/api/claude-design/sync', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ direction: 'create', collection: name }) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || t('The sync failed.'));
      setCollection(name); setNewCollection(''); loadLibrary(); setNotice(t('Collection created.'));
    } catch (error) { setNotice(error.message); } finally { setBusy(false); }
  }

  async function deleteVideo(key) {
    setBusy(true);
    try {
      const response = await fetch("/api/claude-design/videos", {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ key }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || t("Could not delete it."));
      if (preview?.key === key) setPreview(null);
      setNotice(t("Deleted from R2."));
      loadLibrary();
    } catch (error) {
      setNotice(error.message);
    } finally {
      setBusy(false);
    }
  }

  // ========================================
  // Render
  // ========================================

  if (loadError) {
    return (
      <p className="rounded-xl border border-danger-border bg-danger-soft p-5 text-sm text-danger-text">
        {loadError}
      </p>
    );
  }

  if (!library) {
    return <p className="p-5 text-sm text-muted">{t("Reading the design library…")}</p>;
  }

  return (
    <div className="space-y-6">
      {/* Where the designs are, and whether this machine can actually render */}
      <section className="rounded-2xl border border-surface-border bg-surface p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <h2 className="text-lg font-semibold">{t("Claude Design animations")}</h2>
            <p className="mt-1 break-all font-mono text-xs text-muted">{library.root}</p>
          </div>
          <button
            type="button"
            onClick={loadLibrary}
            className="rounded-lg border border-surface-border px-4 py-2 text-sm hover:bg-surface-hover"
          >
            ↻ {t("Refresh")}
          </button>
        </div>

        <div className="mt-4 flex flex-wrap gap-2 text-xs">
          <span
            className={`rounded-full px-3 py-1 ${
              capability.ready
                ? "bg-accent-soft text-accent-soft-text"
                : "bg-warning-soft text-warning-text"
            }`}
          >
            {capability.ready
              ? t("This machine can render")
              : capability.ffmpeg
                ? t("Chromium is missing - rendering is unavailable")
                : t("ffmpeg is missing - rendering is unavailable")}
          </span>
          <span
            className={`rounded-full px-3 py-1 ${
              library.r2Configured ? "bg-accent-soft text-accent-soft-text" : "bg-warning-soft text-warning-text"
            }`}
          >
            {library.r2Configured ? "acm-workshop" : t("acm-workshop is not configured")}
          </span>
          {!library.rootPresent ? (
            <span className="rounded-full bg-warning-soft px-3 py-1 text-warning-text">
              {t("Nothing local yet - fetch a collection from R2 first")}
            </span>
          ) : null}
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,22rem)_minmax(0,1fr)]">
        {/* ── Collections and their designs ───────────────────────────── */}
        <section className="space-y-3 rounded-2xl border border-surface-border bg-surface p-5">
          <h3 className="text-sm font-semibold">{t("Collections")}</h3>

          {collections.length === 0 ? (
            <p className="text-sm text-muted">{t("No designs found in this folder.")}</p>
          ) : null}

          {/* In acm-workshop but not on this disk - one click brings it down */}
          {remote.some((entry) => !collections.some((group) => group.name === entry.name)) ? (
            <div className="space-y-1.5 rounded-lg border border-surface-border bg-surface-sunken p-3">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-strong">
                {t("In acm-workshop")}
              </p>
              {remote
                .filter((entry) => !collections.some((group) => group.name === entry.name))
                .map((entry) => (
                  <div key={entry.name} className="flex items-center gap-2">
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-xs">{entry.name}</span>
                      <span className="block text-[10px] text-muted">
                        {entry.files} {t("files")} · {megabytes(entry.bytes)}
                      </span>
                    </span>
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => syncCollection(entry.name, "pull")}
                      className="shrink-0 rounded-md border border-accent/40 px-2 py-1 text-[10px] text-accent disabled:opacity-40"
                      title={t("Synchronize this collection with R2")}
                    >
                      ↕ R2
                    </button>
                  </div>
                ))}
            </div>
          ) : null}

          <div className="max-h-[36rem] space-y-4 overflow-y-auto pr-1">
            {collections.map((group) => (
              <div key={group.name}>
                <div className="flex items-center justify-between gap-2">
                  <button
                    type="button"
                    onClick={() => toggleCollection(group)}
                    className="min-w-0 flex-1 truncate text-left text-sm font-semibold hover:text-accent"
                    title={t("Select every design in this collection")}
                  >
                    {group.name}
                  </button>
                  {library.r2Configured ? (
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => syncCollection(group.name, "push")}
                      className="shrink-0 rounded-md border border-surface-border px-2 py-1 text-[10px] text-muted hover:bg-surface-hover disabled:opacity-40"
                      title={t("Synchronize this collection with R2")}
                    >
                      ↕ R2
                    </button>
                  ) : null}
                </div>

                <ul className="mt-1 space-y-0.5">
                  {group.designs.map((design) => {
                    const isSelected = selected.includes(design.rootRel);
                    const isPreviewing = preview?.kind === "design" && preview.rootRel === design.rootRel;

                    return (
                      <li key={design.rootRel}>
                        <div
                          className={`flex items-center gap-2 rounded-lg px-2 py-1.5 ${
                            isPreviewing ? "bg-accent-soft" : "hover:bg-surface-hover"
                          }`}
                        >
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => toggleDesign(design.rootRel)}
                            aria-label={`${t("Select")} ${design.name}`}
                            className="shrink-0"
                          />
                          <button
                            type="button"
                            onClick={() =>
                              setPreview({
                                kind: "design",
                                rootRel: design.rootRel,
                                name: design.name,
                                width: design.width,
                                height: design.height,
                              })
                            }
                            className="min-w-0 flex-1 text-left"
                          >
                            <span className="block truncate text-xs">{design.name}</span>
                            <span className="block text-[10px] text-muted">
                              {design.width}×{design.height} · {clock(design.duration)} ·{" "}
                              {design.kind === "design" ? t("source") : t("standalone")}
                            </span>
                          </button>
                        </div>
                      </li>
                    );
                  })}
                </ul>
              </div>
            ))}
          </div>
        </section>

        {/* ── Preview: the design running, or a finished video playing ── */}
        <section className="space-y-3 rounded-2xl border border-surface-border bg-surface p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h3 className="text-sm font-semibold">{t("Preview")}</h3>
            {preview ? (
              <p className="truncate font-mono text-xs text-muted">{preview.name}</p>
            ) : null}
          </div>

          {!preview ? (
            <div className="flex h-64 items-center justify-center rounded-lg border border-dashed border-surface-border text-sm text-muted">
              {t("Choose a design to look at it before rendering.")}
            </div>
          ) : preview.kind === "video" ? (
            <video
              key={preview.key}
              controls
              playsInline
              poster={
                preview.posterKey
                  ? `/api/claude-design/videos?key=${encodeURIComponent(preview.posterKey)}`
                  : undefined
              }
              src={`/api/claude-design/videos?key=${encodeURIComponent(preview.key)}`}
              className="w-full rounded-lg bg-black object-contain"
              style={{ height: "min(65vh, 680px)" }}
            />
          ) : (
            <DesignPreviewFrame preview={preview} />
          )}

          {preview?.kind === "video" ? (
            <div className="flex flex-wrap gap-2">
              <a
                href={`/api/claude-design/videos?key=${encodeURIComponent(preview.key)}&download=1`}
                className="rounded-lg bg-accent px-4 py-2 text-sm text-accent-foreground hover:bg-accent-hover"
              >
                ↓ {t("Download")}
              </a>
              <button
                type="button"
                disabled={busy}
                onClick={() => deleteVideo(preview.key)}
                className="rounded-lg border border-danger-border bg-danger-soft px-4 py-2 text-sm text-danger-text disabled:opacity-40"
              >
                {t("Delete from R2")}
              </button>
            </div>
          ) : null}
        </section>
      </div>

      {/* ── Render settings ─────────────────────────────────────────── */}
      <section className="space-y-4 rounded-2xl border border-surface-border bg-surface p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h3 className="text-sm font-semibold">{t("Video settings")}</h3>
          <p className="text-xs text-muted">
            {selected.length} {t("selected")}
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {/* Frame size */}
          <label className="block text-xs">
            <span className="mb-1 block font-semibold text-muted-strong">{t("Frame size")} <SettingHelp label={t("Frame size")} text={t("Keep the original design dimensions, or choose one fixed size for all selected designs.")} /></span>
            <select
              value={sizeMode}
              onChange={(event) => setSizeMode(event.target.value)}
              className="w-full rounded-lg border border-input-border bg-input-background p-2 text-sm"
            >
              <option value="design">{t("As each design specifies")}</option>
              <option value="fixed">{t("One size for all of them")}</option>
            </select>
          </label>

          <label className="block text-xs">
            <span className="mb-1 block font-semibold text-muted-strong">{t("Aspect ratio")} <SettingHelp label={t("Aspect ratio")} text={t("Width compared with height: 16:9 is landscape, 9:16 is portrait, 1:1 is square and 4:5 is a portrait feed post.")} /></span>
            <select
              value={ratio}
              disabled={sizeMode === "design"}
              onChange={(event) => {
                setRatio(event.target.value);
                const group = RATIOS.find((entry) => entry.id === event.target.value);
                setSizeLabel(group.sizes[group.sizes.length > 1 ? 1 : 0].label);
              }}
              className="w-full rounded-lg border border-input-border bg-input-background p-2 text-sm disabled:opacity-40"
            >
              {RATIOS.map((entry) => (
                <option key={entry.id} value={entry.id}>
                  {entry.label}
                </option>
              ))}
            </select>
          </label>

          <label className="block text-xs">
            <span className="mb-1 block font-semibold text-muted-strong">{t("Resolution")} <SettingHelp label={t("Resolution")} text={t("The number of pixels in the video. More pixels preserve more detail but take longer to render. Upscaling does not create missing detail.")} /></span>
            <select
              value={sizeLabel}
              disabled={sizeMode === "design"}
              onChange={(event) => setSizeLabel(event.target.value)}
              className="w-full rounded-lg border border-input-border bg-input-background p-2 text-sm disabled:opacity-40"
            >
              {(RATIOS.find((entry) => entry.id === ratio) || RATIOS[0]).sizes.map((size) => (
                <option key={size.label} value={size.label}>
                  {size.label}
                </option>
              ))}
            </select>
          </label>

          <label className="block text-xs">
            <span className="mb-1 block font-semibold text-muted-strong">{t("Frame rate")} <SettingHelp label={t("Frame rate")} text={t("Frames per second. 60 fps gives smoother motion; 30 fps renders fewer frames; 24 fps has a film-like cadence. Rendering time is not guaranteed to halve.")} /></span>
            <select
              value={fps}
              onChange={(event) => setFps(Number(event.target.value))}
              className="w-full rounded-lg border border-input-border bg-input-background p-2 text-sm"
            >
              <option value={60}>60 fps</option>
              <option value={30}>30 fps</option>
              <option value={24}>24 fps · {t("film")}</option>
            </select>
          </label>

          <label className="block text-xs">
            <span className="mb-1 block font-semibold text-muted-strong">{t("Quality (CRF)")} <SettingHelp label={t("Quality (CRF)")} text={t("CRF controls compression, not resolution. Workshop defaults to 18; x264 defaults to 23. Lower values retain more detail and make larger files. 18: high quality, a useful starting point. 10: very little compression, much larger files. 5: even less compression, often little visible improvement over 10. 25: smaller files, with more risk of visible artefacts around text and motion. 0 is lossless; 51 is the lowest quality. There is no single best value or fixed file size: compare a short render at the intended viewing size.")} /></span>
            <input
              type="number"
              min="0"
              max="51"
              value={crf}
              onChange={(event) => setCrf(Number(event.target.value))}
              className="w-full rounded-lg border border-input-border bg-input-background p-2 text-sm"
            />
            <span className="mt-1 block text-[10px] text-muted">{t("Lower is better and larger.")}</span>
          </label>

          <label className="block text-xs">
            <span className="mb-1 block font-semibold text-muted-strong">{t("Test length")} <SettingHelp label={t("Test length")} text={t("Render only this many seconds from the start. Leave blank for the whole animation. Use a short test to compare quality and framing.")} /></span>
            <input
              type="number"
              min="1"
              placeholder={t("whole animation")}
              value={testSeconds}
              onChange={(event) => setTestSeconds(event.target.value)}
              className="w-full rounded-lg border border-input-border bg-input-background p-2 text-sm"
            />
            <span className="mt-1 block text-[10px] text-muted">
              {t("Seconds. Check the look before committing an hour.")}
            </span>
          </label>

          <label className="block text-xs">
            <span className="mb-1 block font-semibold text-muted-strong">{t("Closing www.ccm.is")} <SettingHelp label={t("Closing www.ccm.is")} text={t("Scale the website address in the final scene. 1 means its original size; 1.6 means 160%. This does not enlarge the whole video.")} /></span>
            <input
              type="number"
              step="0.1"
              min="1"
              max="3"
              value={siteScale}
              onChange={(event) => setSiteScale(Number(event.target.value))}
              className="w-full rounded-lg border border-input-border bg-input-background p-2 text-sm"
            />
            <span className="mt-1 block text-[10px] text-muted">{t("Size multiplier in the last scene.")}</span>
          </label>

          <label className="block text-xs">
            <span className="mb-1 block font-semibold text-muted-strong">{t("Save into collection")} <SettingHelp label={t("Save into collection")} text={t("Choose a collection for the finished video, or create a new one. Design sources stay in their original collection.")} /></span>
            <select value={collection} onChange={(event) => setCollection(event.target.value)} className="w-full rounded-lg border border-input-border bg-input-background p-2 text-sm">
              <option value="">{t("same as the design's")}</option>
              {[...new Set([...collections.map(x => x.name), ...remote.map(x => x.name), ...(library.videos || []).map(x => x.collection), ...(collection && collection !== '__new__' ? [collection] : [])])].sort().map(name => <option key={name} value={name}>{name}</option>)}
              <option value="__new__">{t("Create a new collection…")}</option>
            </select>
            {collection === '__new__' && <span className="mt-2 flex flex-wrap gap-2">
              <input aria-label={t("New collection name")} value={newCollection} onChange={event => setNewCollection(event.target.value)} className="min-w-0 w-full rounded-lg border border-input-border bg-input-background p-2 text-sm" />
              <button type="button" onClick={createCollection} disabled={busy || !newCollection.trim()} className="rounded-lg border border-accent px-3 py-2 disabled:opacity-40">{t("Create collection")}</button>
            </span>}
          </label>
        </div>

        {/* The player bar is part of the design, so whether it belongs in the
            finished file is a real choice rather than always-off. */}
        <label className="flex items-start gap-3 rounded-lg bg-surface-sunken p-3 text-sm">
          <input
            type="checkbox"
            checked={keepChrome}
            onChange={(event) => setKeepChrome(event.target.checked)}
            className="mt-0.5"
          />
          <span>
            {t("Keep the player bar at the bottom of the video")}
            <span className="block text-xs text-muted">
              {t("Off by default. It belongs to the design's own preview, not to a finished video.")}
            </span>
          </span>
        </label>

        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            disabled={busy || collection === "__new__" || !selected.length || !capability.ready}
            onClick={startRender}
            className="rounded-lg bg-accent px-5 py-2.5 text-sm font-semibold text-accent-foreground hover:bg-accent-hover disabled:opacity-40"
          >
            {selected.length > 1
              ? `${t("Render")} ${selected.length} ${t("videos")}`
              : t("Render video")}
          </button>
          {!capability.ready ? (
            <p className="text-xs text-warning-text">
              {t("Rendering needs ffmpeg and Chromium on this machine.")}
            </p>
          ) : null}
          {notice ? <p className="text-xs text-muted">{notice}</p> : null}
        </div>
      </section>

      {/* ── Queue and live console ──────────────────────────────────── */}
      <section className="space-y-4 rounded-2xl border border-surface-border bg-surface p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h3 className="text-sm font-semibold">
            {t("Render queue")}
            {queuedCount ? (
              <span className="ml-2 font-normal text-muted">
                {queuedCount} {t("waiting")}
              </span>
            ) : null}
          </h3>
          {jobs.some((job) => FINISHED.includes(job.status)) ? (
            <button
              type="button"
              onClick={clearFinished}
              className="rounded-lg border border-surface-border px-3 py-1.5 text-xs hover:bg-surface-hover"
            >
              {t("Clear finished")}
            </button>
          ) : null}
        </div>

        {jobs.length === 0 ? (
          <p className="text-sm text-muted">{t("Nothing has been rendered in this session.")}</p>
        ) : (
          <ul className="space-y-2">
            {jobs.map((job) => (
              <li key={job.id} className="rounded-lg bg-surface-sunken p-3">
                <div className="flex flex-wrap items-center gap-3">
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm">
                      {job.collection} / {job.outName}
                    </span>
                    <span className="block text-[10px] text-muted">
                      {job.width}×{job.height} · {job.fps} fps · {clock(job.seconds)}
                      {job.frames ? ` · ${job.frame}/${job.frames}` : ""}
                      {job.etaSec ? ` · ~${Math.ceil(job.etaSec / 60)} ${t("min left")}` : ""}
                    </span>
                  </span>

                  <span
                    className={`shrink-0 rounded-full px-2.5 py-1 text-[10px] ${
                      job.status === "error"
                        ? "bg-danger-soft text-danger-text"
                        : job.status === "done"
                          ? "bg-accent-soft text-accent-soft-text"
                          : "bg-surface-hover text-muted-strong"
                    }`}
                  >
                    {t(job.status)}
                  </span>

                  {!FINISHED.includes(job.status) ? (
                    <button
                      type="button"
                      onClick={() => stopJob(job.id)}
                      className="shrink-0 rounded-md border border-danger-border px-2.5 py-1 text-[10px] text-danger-text"
                    >
                      {t("Stop")}
                    </button>
                  ) : null}
                </div>

                {/* Progress is only honest once the renderer has reported a
                    frame count, so the bar appears then rather than at zero. */}
                {job.frames ? (
                  <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-surface-hover">
                    <div
                      className="h-full rounded-full bg-accent transition-[width] duration-500"
                      style={{ width: `${Math.min(100, job.pct || 0)}%` }}
                    />
                  </div>
                ) : null}

                {job.error ? <p className="mt-2 text-xs text-danger-text">{job.error}</p> : null}
              </li>
            ))}
          </ul>
        )}

        <ConsoleLog lines={consoleLines} running={Boolean(activeJob)} />
      </section>

      {/* ── Finished videos, played straight out of R2 ──────────────── */}
      <section className="space-y-4 rounded-2xl border border-surface-border bg-surface p-5">
        <h3 className="text-sm font-semibold">{t("Rendered videos")}</h3>

        {library.r2Error ? (
          <p className="text-sm text-danger-text">{library.r2Error}</p>
        ) : library.videos.length === 0 ? (
          <p className="text-sm text-muted">{t("Nothing stored in acm-workshop yet.")}</p>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4">
            {library.videos.map((video) => (
              <div key={video.id} className="overflow-hidden rounded-xl border border-surface-border">
                <button
                  type="button"
                  onClick={() =>
                    setPreview({
                      kind: "video",
                      key: video.key,
                      posterKey: video.posterKey,
                      name: `${video.collection} / ${video.name}`,
                    })
                  }
                  className="block w-full bg-black"
                >
                  {video.posterKey ? (
                    /* eslint-disable-next-line @next/next/no-img-element -- a presigned R2 redirect, not an optimizable asset */
                    <img
                      src={`/api/claude-design/videos?key=${encodeURIComponent(video.posterKey)}`}
                      alt=""
                      className="aspect-video w-full object-cover"
                    />
                  ) : (
                    <span className="flex aspect-video w-full items-center justify-center text-xs text-console-muted">
                      ▶
                    </span>
                  )}
                </button>

                <div className="space-y-2 p-3">
                  <p className="truncate text-xs font-semibold" title={video.name}>
                    {video.name}
                  </p>
                  <p className="text-[10px] text-muted">
                    {video.collection} · {megabytes(video.bytes)}
                  </p>
                  <div className="flex gap-2">
                    <a
                      href={`/api/claude-design/videos?key=${encodeURIComponent(video.key)}&download=1`}
                      className="flex-1 rounded-md border border-surface-border px-2 py-1 text-center text-[10px] hover:bg-surface-hover"
                    >
                      ↓ {t("Download")}
                    </a>
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => deleteVideo(video.key)}
                      className="rounded-md border border-danger-border px-2 py-1 text-[10px] text-danger-text disabled:opacity-40"
                    >
                      {t("Delete")}
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
