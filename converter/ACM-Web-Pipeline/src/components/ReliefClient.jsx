"use client";

/*
 * ═══════════════════════════════════════════════════════════════
 * Relief Client
 * ═══════════════════════════════════════════════════════════════
 * Path: src/components/ReliefClient.jsx
 * Purpose: Drive the 2.5D pipeline - photograph to depth map to relief mesh -
 *          and show the result inside the glass it will actually be cut into.
 *
 * The preview compares the source with the textured 2.5D result handed to ACM
 * Scene Composer in Blender. A point-cloud view remains available as a later
 * production check, but it is deliberately not this pipeline's deliverable.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import ConsoleLog from "@/components/ConsoleLog";
import CrystalPreview, { PREVIEW_DOT_SIZE_MM } from "@/components/CrystalPreview";
import { useLanguage } from "@/components/LanguageProvider";
import OptionFields from "@/components/OptionFields";
import { CRYSTAL_BLANKS } from "@/lib/crystal-blanks";
import { readSse } from "@/lib/read-sse";
import { readResponseJson } from "@/lib/response-json";
import {
  PHOTO_TYPES,
  RELIEF_FIELDS,
  RELIEF_FIELD_GROUPS,
  defaultReliefValues,
} from "@/lib/relief/catalog";

const CARD = "rounded-xl border border-surface-border bg-surface p-6";
const SECTION_TITLE = "text-xs font-semibold uppercase tracking-wide text-muted-strong";

/** Human-readable byte size, because "103948887" tells nobody anything. */
function formatBytes(bytes) {
  if (!bytes) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / 1024 ** index).toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

const fileUrl = (jobId, name, download = false) =>
  `/api/file?root=relief-output&path=${encodeURIComponent(`${jobId}/${name}`)}${
    download ? "&download=1" : ""
  }`;

const inputUrl = (name) => `/api/file?root=relief-input&path=${encodeURIComponent(name)}`;

/**
 * Blank dimensions for the viewer.
 *
 * Every blank key is literally WIDTHxHEIGHTxDEPTH, so the name parses even
 * when it is a custom size that was never in the table.
 */
function blankDimensions(template) {
  const known = CRYSTAL_BLANKS[template];
  if (known) return { width: known.width, height: known.height, depth: known.depth };

  const parts = String(template || "").split("x").map(Number);
  if (parts.length === 3 && parts.every((value) => value > 0)) {
    return { width: parts[0], height: parts[1], depth: parts[2] };
  }
  return { width: 60, height: 80, depth: 40 };
}

/**
 * The imported Cockpit 3D shape whose millimetres match this blank, if any.
 *
 * Matched on dimensions rather than name, because our blank keys are
 * WIDTHxHEIGHTxDEPTH while theirs are product names like "2D Heart Large
 * 125x110". A 1 mm tolerance absorbs their rounding.
 */
function matchBlankModel(blanks, template) {
  const known = CRYSTAL_BLANKS[template];
  if (known?.model) {
    return `/api/file?root=relief-blanks&path=${encodeURIComponent(known.model)}`;
  }

  const parts = known
    ? [known.width, known.height, known.depth]
    : String(template || "").split("x").map(Number);
  if (parts.length !== 3 || parts.some((value) => !(value > 0))) return null;

  const [width, height, depth] = parts;
  const hit = blanks.find(
    (blank) =>
      blank.model &&
      Math.abs(blank.width - width) <= 1 &&
      Math.abs(blank.height - height) <= 1 &&
      Math.abs(blank.depth - depth) <= 1,
  );
  return hit ? `/api/file?root=relief-blanks&path=${encodeURIComponent(hit.model)}` : null;
}

/** One finished relief: before and after, the viewer controls, and where it goes next. */
function JobCard({ job, locale, blankModel }) {
  const [mode, setMode] = useState("surface");
  const [showGlass, setShowGlass] = useState(true);
  const [autoRotate, setAutoRotate] = useState(true);
  const [compare, setCompare] = useState("after");
  const [appearance, setAppearance] = useState("crystal");

  const blank = useMemo(() => blankDimensions(job.template), [job.template]);
  const border = Number(job.values?.border) || 1;

  const photo = fileUrl(job.jobId, job.files?.photo || "source.png");
  const relief = fileUrl(
    job.jobId,
    appearance === "crystal"
      ? job.files?.crystalPreview || job.files?.preview || "relief.glb"
      : job.files?.preview || "relief.glb",
  );

  /*
   * Before is the flat photograph suspended in the glass - the plain 2D
   * engraving, and the honest baseline the relief has to beat. After is the
   * depth-built surface. Side-by-side is the default because the difference
   * between them is the entire argument for this pipeline existing, and it is
   * genuinely hard to see one at a time.
   */
  const views = {
    before: [{ key: "before", src: photo, kind: "photo" }],
    after: [{ key: "after", src: relief, kind: "glb" }],
    both: [
      { key: "before", src: photo, kind: "photo" },
      { key: "after", src: relief, kind: "glb" },
    ],
  }[compare];

  const label = {
    before: locale === "is" ? "Fyrir · flöt mynd" : "Before · flat photo",
    after: locale === "is" ? "Eftir · upphleyping" : "After · relief",
  };

  return (
    <div className={`${CARD} space-y-4`}>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="font-mono text-sm text-muted-strong">{job.jobId}</h3>
        <span className="font-mono text-xs text-muted">
          {job.template} · {job.values?.engine} · {job.resolvedGrid || job.values?.grid} grid
          {job.resolvedReliefDepth
            ? ` · ${job.resolvedReliefDepth}mm ${job.values?.relief_depth_profile || "custom"}`
            : ""}
        </span>
      </div>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_16rem]">
        <div className={`grid gap-3 ${views.length > 1 ? "sm:grid-cols-2" : ""}`}>
          {views.map((view) => (
            <div key={view.key} className="space-y-1.5">
              <span className="block text-[11px] font-medium uppercase tracking-wide text-muted">
                {label[view.key]}
              </span>
              <CrystalPreview
                src={view.src}
                kind={view.kind}
                blank={blank}
                blankModel={blankModel}
                border={border}
                mode={mode}
                pointSize={PREVIEW_DOT_SIZE_MM}
                showGlass={showGlass}
                autoRotate={autoRotate}
              />
            </div>
          ))}
        </div>

        {/* Viewer controls - presentation only, they never touch the geometry */}
        <div className="space-y-4">
          {/* Before / after - the comparison this pipeline exists to win */}
          <div className="space-y-1.5">
            <span className={SECTION_TITLE}>
              {locale === "is" ? "Samanburður" : "Compare"}
            </span>
            <div className="flex gap-1.5">
              {[
                ["before", locale === "is" ? "Fyrir" : "Before"],
                ["both", locale === "is" ? "Bæði" : "Both"],
                ["after", locale === "is" ? "Eftir" : "After"],
              ].map(([option, text]) => (
                <button
                  key={option}
                  type="button"
                  onClick={() => setCompare(option)}
                  className={`flex-1 rounded-md border px-2 py-1.5 text-xs transition ${
                    compare === option
                      ? "border-accent bg-surface-strong text-foreground"
                      : "border-surface-border text-muted hover:border-accent"
                  }`}
                >
                  {text}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-1.5">
            <span className={SECTION_TITLE}>{locale === "is" ? "Áferð" : "Appearance"}</span>
            <div className="flex gap-1.5">
              {[
                ["crystal", locale === "is" ? "Kristall" : "Crystal"],
                ["rgb", "RGB"],
              ].map(([option, text]) => (
                <button
                  key={option}
                  type="button"
                  onClick={() => setAppearance(option)}
                  className={`flex-1 rounded-md border px-2 py-1.5 text-xs transition ${
                    appearance === option
                      ? "border-accent bg-surface-strong text-foreground"
                      : "border-surface-border text-muted hover:border-accent"
                  }`}
                >
                  {text}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-1.5">
            <span className={SECTION_TITLE}>{locale === "is" ? "Sýn" : "Render"}</span>
            <div className="flex gap-1.5">
              {["points", "surface"].map((option) => (
                <button
                  key={option}
                  type="button"
                  onClick={() => setMode(option)}
                  className={`flex-1 rounded-md border px-2 py-1.5 text-xs transition ${
                    mode === option
                      ? "border-accent bg-surface-strong text-foreground"
                      : "border-surface-border text-muted hover:border-accent"
                  }`}
                >
                  {option === "points"
                    ? locale === "is"
                      ? "Punktar"
                      : "Dots"
                    : locale === "is"
                      ? "Yfirborð"
                      : "Surface"}
                </button>
              ))}
            </div>
            <p className="text-[11px] leading-snug text-muted">
              {locale === "is"
                ? "Yfirborð er 2.5D GLB-skráin fyrir Blender Composer. Punktar eru aðeins síðara framleiðslupróf."
                : "Surface is the 2.5D GLB for Blender Composer. Dots are only a later production check."}
            </p>
          </div>

          {mode === "points" ? (
          <div className="rounded-md border border-surface-border bg-surface-sunken px-3 py-2">
            <span className="block text-xs text-muted">
              {locale === "is" ? "Punktastærð" : "Dot size"}
            </span>
            <strong className="font-mono text-sm text-muted-strong">
              {PREVIEW_DOT_SIZE_MM.toFixed(2)} mm
            </strong>
          </div>
          ) : null}

          <label className="flex items-center gap-2 text-xs text-muted">
            <input type="checkbox" checked={showGlass} onChange={() => setShowGlass((on) => !on)} />
            {locale === "is" ? "Sýna glerið" : "Show the glass"}
          </label>
          <label className="flex items-center gap-2 text-xs text-muted">
            <input type="checkbox" checked={autoRotate} onChange={() => setAutoRotate((on) => !on)} />
            {locale === "is" ? "Snúa sjálfkrafa" : "Auto-rotate"}
          </label>

          {/* Primary handoff: the finished 2.5D asset goes to Blender Composer. */}
          <a
            href={fileUrl(
              job.jobId,
              job.files?.crystalPreview || job.files?.preview || "relief.glb",
              true,
            )}
            className="w-full rounded-md bg-accent px-3 py-2 text-sm font-medium text-accent-foreground transition hover:opacity-90"
          >
            {locale === "is" ? "Sækja fyrir Blender Composer →" : "Download for Blender Composer →"}
          </a>

          <div className="space-y-1 border-t border-surface-border pt-3">
            {[
              [job.files?.preview || "relief.glb", locale === "is" ? "RGB GLB" : "RGB GLB"],
              ...(job.files?.crystalPreview
                ? [[job.files.crystalPreview, locale === "is" ? "Svarthvítt crystal GLB" : "Monochrome crystal GLB"]]
                : []),
              ...(job.files?.crystalTone
                ? [[job.files.crystalTone, locale === "is" ? "Crystal tónakort" : "Crystal tone map"]]
                : []),
              [job.files?.mesh || "relief.obj", locale === "is" ? "Möskvi" : "Mesh"],
              ...(job.files?.pointCloud
                ? [[job.files.pointCloud, locale === "is" ? "Prentpunktar" : "Printer points"]]
                : []),
              ...(job.files?.pointPreview
                ? [[job.files.pointPreview, locale === "is" ? "XYZ punktaforskoðun" : "XYZ point preview"]]
                : []),
              [job.files?.depth || "depth.png", locale === "is" ? "Dýptarkort" : "Depth map"],
              [job.files?.photo || "source.png", locale === "is" ? "Ljósmynd" : "Photo"],
            ].map(([name, label]) => (
              <a
                key={name}
                href={fileUrl(job.jobId, name, true)}
                className="flex items-center justify-between font-mono text-[11px] text-muted hover:text-foreground"
              >
                <span>{label}</span>
                <span>{name.split(".").pop()}</span>
              </a>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function ReliefClient({ initialState, handoff, onOpenViewer }) {
  const { locale } = useLanguage();
  const [values, setValues] = useState(defaultReliefValues);
  const [selected, setSelected] = useState([]);
  const [photos, setPhotos] = useState(initialState.photos || []);
  const [jobs, setJobs] = useState(initialState.jobs || []);
  const ready = initialState.ready;

  const [uploading, setUploading] = useState(false);
  const [running, setRunning] = useState(false);
  const [lines, setLines] = useState([]);
  const [notice, setNotice] = useState(null);
  const [library, setLibrary] = useState({ configured: false, sources: [] });
  const [blanks, setBlanks] = useState([]);

  const abortRef = useRef(null);

  // The durable photo library lives in R2 so the VPS holds nothing. An
  // unconfigured bucket just means the section stays hidden.
  useEffect(() => {
    let cancelled = false;
    fetch("/api/relief/library", { cache: "no-store" })
      .then((response) => response.json())
      .then((data) => !cancelled && setLibrary(data))
      .catch(() => {
        // A missing library is not worth an error banner.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Real blank geometry, if import_blanks.py has been run. Absent is normal
  // and simply leaves the viewer on its chamfered-box fallback.
  useEffect(() => {
    let cancelled = false;
    fetch("/api/relief/blanks", { cache: "no-store" })
      .then((response) => response.json())
      .then((data) => !cancelled && setBlanks(data.blanks || []))
      .catch(() => {
        // No import yet; the fallback box is a perfectly good stand-in.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // The blank the form is currently pointed at, so the pre-conversion preview
  // frames the photo in the crystal it would actually be cut into.
  const blank = useMemo(() => {
    return blankDimensions(values.template);
  }, [values.template]);

  const refresh = useCallback(async () => {
    try {
      const response = await fetch("/api/relief/state", { cache: "no-store" });
      const data = await response.json();
      setPhotos(data.photos || []);
      setJobs(data.jobs || []);
    } catch {
      // A listing failure is not worth interrupting the run for.
    }
  }, []);

  // Leið A has already written the composed PNG to relief/input. Select that
  // exact file and carry its authoritative blank dimensions into the form.
  useEffect(() => {
    if (!handoff?.path) return;
    queueMicrotask(() => {
      setSelected([handoff.path]);
      setValues((current) => ({
        ...current,
        template: handoff.template || current.template,
        border: handoff.border ?? current.border,
      }));
      setNotice(null);
      refresh();
    });
  }, [handoff, refresh]);

  const toggle = (photo) =>
    setSelected((current) =>
      current.includes(photo.path)
        ? current.filter((item) => item !== photo.path)
        : [...current, photo.path],
    );

  async function upload(fileList) {
    setNotice(null);
    setUploading(true);
    try {
      for (const file of fileList) {
        const response = await fetch("/api/upload", {
          method: "POST",
          headers: { "x-filename": encodeURIComponent(file.name), "x-target": "relief" },
          body: file,
        });
        const data = await readResponseJson(response);
        if (!response.ok) throw new Error(data.error || "Upload failed");
        setSelected((current) => [...current, data.path]);
      }
      await refresh();
    } catch (error) {
      setNotice({ tone: "error", text: error.message });
    } finally {
      setUploading(false);
    }
  }

  async function run() {
    if (!selected.length) {
      setNotice({ tone: "error", text: "Pick at least one photo." });
      return;
    }

    setRunning(true);
    setLines([]);
    setNotice(null);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const response = await fetch("/api/relief/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ photos: selected, values }),
        signal: controller.signal,
      });
      if (!response.ok) {
        const data = await readResponseJson(response).catch(() => ({}));
        throw new Error(data.error || `Server returned ${response.status}`);
      }

      await readSse(response, (event) => {
        if (event.type === "result") {
          // Prepend, so the newest relief is the one already on screen.
          setJobs((current) => [event.job, ...current.filter((job) => job.jobId !== event.job.jobId)]);
          setLines((current) => [...current, { type: "done", text: `Job ${event.job.jobId}` }]);
          return;
        }
        if (event.type === "done") {
          setLines((current) => [
            ...current,
            {
              type: event.code === 0 ? "done" : "error",
              text: event.code === 0 ? "Finished." : "Failed.",
            },
          ]);
          return;
        }
        setLines((current) => [
          ...current,
          { type: event.type, text: event.line ?? event.message ?? "" },
        ]);
      });

      await refresh();
    } catch (error) {
      if (error.name !== "AbortError") setNotice({ tone: "error", text: error.message });
    } finally {
      setRunning(false);
      abortRef.current = null;
    }
  }

  /** Pull one library photograph back onto local disk so a run can use it. */
  async function importFromLibrary(source) {
    setNotice(null);
    try {
      const response = await fetch("/api/relief/library", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ key: source.key }),
      });
      const data = await readResponseJson(response);
      if (!response.ok) throw new Error(data.error || "Could not import that photo");
      setSelected((current) => [...current, data.path]);
      await refresh();
    } catch (error) {
      setNotice({ tone: "error", text: error.message });
    }
  }

  return (
    <div className="space-y-8">
      {!ready ? (
        <div className="rounded-lg border border-danger-border bg-danger-soft px-4 py-3 text-sm text-danger-text">
          <p>
            {locale === "is"
              ? "Python-umhverfi 2.5D-vinnslunnar vantar."
              : "No Python venv for the 2.5D pipeline."}
          </p>
          <pre className="mt-2 overflow-x-auto font-mono text-xs">
            cd ../2.5D-pipeline{"\n"}python -m venv .venv{"\n"}
            .venv/bin/pip install -r requirements.txt{"\n"}
            .venv/bin/python code/download_models.py --model large
          </pre>
        </div>
      ) : null}

      {notice ? (
        <div className="rounded-lg border border-danger-border bg-danger-soft px-4 py-3 text-sm text-danger-text">
          {notice.text}
        </div>
      ) : null}

      {/* Step 1 - photographs */}
      <section className={`${CARD} space-y-4`}>
        <div className="flex items-baseline justify-between gap-4">
          <h2 className={SECTION_TITLE}>
            1 &middot; {locale === "is" ? "Ljósmyndir" : "Photographs"}
          </h2>
          <span className="font-mono text-xs text-muted">{PHOTO_TYPES.join("  ")}</span>
        </div>

        <p className="text-xs text-muted">
          {locale === "is"
            ? "Best er PNG með gegnsæjum bakgrunni úr myndavinnslunni — þá fær aðeins viðfangsefnið upphleypingu."
            : "A cut-out PNG from the image pipeline works best - then only the subject gets relief."}
        </p>

        <label className="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-input-border bg-surface-sunken px-6 py-8 text-center transition hover:border-accent">
          <input
            type="file"
            multiple
            accept={PHOTO_TYPES.join(",")}
            className="hidden"
            disabled={uploading || running}
            onChange={(event) => {
              if (event.target.files?.length) upload(Array.from(event.target.files));
              event.target.value = "";
            }}
          />
          <span className="text-sm text-muted-strong">
            {uploading
              ? locale === "is"
                ? "Hleð upp…"
                : "Uploading…"
              : locale === "is"
                ? "Veldu eða dragðu myndir hingað"
                : "Choose or drop photographs here"}
          </span>
        </label>

        {photos.length ? (
          <ul className="grid gap-2 sm:grid-cols-2">
            {photos.map((photo) => (
              <li key={photo.path}>
                <label className="flex cursor-pointer items-center gap-3 rounded-lg border border-surface-border px-3 py-2 transition hover:border-accent">
                  <input
                    type="checkbox"
                    checked={selected.includes(photo.path)}
                    onChange={() => toggle(photo)}
                  />
                  <span className="min-w-0 flex-1 truncate text-sm">{photo.name}</span>
                  <span className="font-mono text-[11px] text-muted">{formatBytes(photo.bytes)}</span>
                </label>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-muted">
            {locale === "is" ? "Engar myndir í input/." : "No photographs in input/ yet."}
          </p>
        )}

        {/* The durable R2 library - every photo ever built, re-runnable */}
        {library.configured && library.sources?.length ? (
          <div className="space-y-2 border-t border-surface-border pt-4">
            <span className={SECTION_TITLE}>
              {locale === "is" ? "Úr myndasafninu (R2)" : "From the library (R2)"}
            </span>
            <ul className="grid max-h-48 gap-1.5 overflow-y-auto sm:grid-cols-2">
              {library.sources.map((source) => (
                <li key={source.key}>
                  <button
                    type="button"
                    disabled={running}
                    onClick={() => importFromLibrary(source)}
                    className="w-full truncate rounded-md border border-surface-border px-3 py-1.5 text-left text-xs transition hover:border-accent disabled:opacity-40"
                  >
                    {source.label || source.name}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        {/*
         * The photograph in the blank, before any depth work. This is what a
         * customer would see on acm.is at the moment they upload - and it is
         * the honest baseline the relief has to beat to be worth the compute.
         */}
        {selected.length ? (
          <div className="space-y-2 border-t border-surface-border pt-4">
            <span className={SECTION_TITLE}>
              {locale === "is" ? "Fyrir umbreytingu" : "Before conversion"}
            </span>
            <div className="max-w-sm">
              <CrystalPreview
                src={inputUrl(selected[0])}
                kind="photo"
                blank={blank}
                blankModel={matchBlankModel(blanks, values.template)}
                border={Number(values.border) || 1}
                autoRotate={false}
              />
            </div>
          </div>
        ) : null}
      </section>

      {/* Step 2 - settings */}
      <section className={`${CARD} space-y-5`}>
        <h2 className={SECTION_TITLE}>2 &middot; {locale === "is" ? "Stillingar" : "Settings"}</h2>
        <OptionFields
          fields={RELIEF_FIELDS}
          groups={RELIEF_FIELD_GROUPS}
          values={values}
          onChange={setValues}
        />

        <div className="flex flex-wrap gap-2 border-t border-surface-border pt-4">
          <button
            type="button"
            onClick={run}
            disabled={running || !ready || !selected.length}
            className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-accent-foreground transition hover:opacity-90 disabled:opacity-40"
          >
            {running
              ? locale === "is"
                ? "Vinn…"
                : "Building…"
              : locale === "is"
                ? "Búa til upphleypingu"
                : "Build the relief"}
          </button>
          {running ? (
            <button
              type="button"
              onClick={() => abortRef.current?.abort()}
              className="rounded-md border border-surface-border px-4 py-2 text-sm transition hover:border-accent"
            >
              {locale === "is" ? "Hætta við" : "Cancel"}
            </button>
          ) : null}
        </div>
      </section>

      <ConsoleLog lines={lines} running={running} />

      {/* Step 3 - the crystal */}
      {jobs.length ? (
        <section className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className={SECTION_TITLE}>
              3 &middot; {locale === "is" ? "Kristallinn" : "The crystal"}
            </h2>
            <button
              type="button"
            onClick={() => onOpenViewer?.(jobs[0])}
              className="rounded-md bg-accent px-3 py-2 text-xs font-medium text-accent-foreground"
            >
            {locale === "is" ? "Opna Leið B" : "Open Model B"}
            </button>
          </div>
          {jobs.map((job) => (
            <JobCard
              key={job.jobId}
              job={job}
              locale={locale}
              blankModel={matchBlankModel(blanks, job.template)}
            />
          ))}
        </section>
      ) : null}
    </div>
  );
}
