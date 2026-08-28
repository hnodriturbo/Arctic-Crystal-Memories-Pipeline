"use client";

/*
 * ═══════════════════════════════════════════════════════════════
 * Converter Client
 * ═══════════════════════════════════════════════════════════════
 * Path: src/components/ConverterClient.jsx
 * Purpose: Drive the whole flow - pick a file, pick an operation,
 *          run the Python script, watch it, collect the results.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import ConsoleLog from "@/components/ConsoleLog";
import { useLanguage } from "@/components/LanguageProvider";
import OptionFields from "@/components/OptionFields";
import { CRYSTAL_BLANKS } from "@/lib/crystal-blanks";
import { OPERATIONS, defaultValues, groupsFor } from "@/lib/operations";
import { readSse } from "@/lib/read-sse";
import { readResponseJson } from "@/lib/response-json";
import { uploadToR2 } from "@/lib/upload-to-r2";

const OPERATION_KEYS = Object.keys(OPERATIONS);

/** Human-readable byte size, because "103948887" tells nobody anything. */
function formatBytes(bytes) {
  if (!bytes) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / 1024 ** index).toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

const CARD = "rounded-xl border border-surface-border bg-surface p-6";
const SECTION_TITLE = "text-xs font-semibold uppercase tracking-wide text-muted-strong";

/*
 * A model handed over from the Meshy pipeline arrives as `handoff`, and the
 * shell remounts this component when one lands. That is why the handoff is
 * read in the state initialisers rather than synchronised by an effect: the
 * file is already selected and the crystal blank already chosen on the very
 * first render, with no cascading re-render on the way there.
 */
export default function ConverterClient({
  initialInputs = [],
  initialOutputs = [],
  initialMeshyJobs = [],
  handoff = null,
}) {
  const { t } = useLanguage();
  const [operation, setOperation] = useState("mesh_to_pointcloud");
  const [values, setValues] = useState(() => ({
    ...defaultValues("mesh_to_pointcloud"),
    ...(handoff?.template ? { template: handoff.template } : {}),
    // A one-off size typed into the Meshy step fills the custom fields here,
    // where 0 means "leave the blank alone".
    ...(handoff?.customSize
      ? {
          width: handoff.customSize.width || 0,
          height: handoff.customSize.height || 0,
          depth: handoff.customSize.depth || 0,
        }
      : {}),
  }));

  const [sourceFile, setSourceFile] = useState(handoff?.file ?? null);
  const [inputs, setInputs] = useState(initialInputs);
  const [outputs, setOutputs] = useState(initialOutputs);

  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(null);
  const [r2Jobs, setR2Jobs] = useState([]);
  const [r2Configured, setR2Configured] = useState(null);
  const [libraryLoading, setLibraryLoading] = useState(true);
  const [importingKey, setImportingKey] = useState(null);
  const [running, setRunning] = useState(false);
  const [lines, setLines] = useState([]);
  const [notice, setNotice] = useState(null);

  const abortRef = useRef(null);
  const definition = OPERATIONS[operation];
  const groups = useMemo(() => groupsFor(operation), [operation]);

  const refreshFiles = useCallback(async () => {
    try {
      const response = await fetch("/api/files", { cache: "no-store" });
      const data = await readResponseJson(response);
      if (!response.ok) return;
      setInputs(data.inputs || []);
      setOutputs(data.outputs || []);
    } catch {
      // A listing failure is not worth interrupting the run for.
    }
  }, []);

  /** R2 is the durable Meshy archive; refresh it independently of local disk. */
  const refreshR2Library = useCallback(async () => {
    setLibraryLoading(true);
    try {
      const response = await fetch("/api/r2/library", { cache: "no-store" });
      const data = await readResponseJson(response);
      if (!response.ok) throw new Error(data.error || "Could not read the R2 library");
      setR2Configured(Boolean(data.configured));
      setR2Jobs(data.jobs || []);
    } catch (error) {
      setR2Configured(false);
      setNotice({ tone: "error", text: error.message });
    } finally {
      setLibraryLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(refreshR2Library, 0);
    return () => window.clearTimeout(timer);
  }, [refreshR2Library]);

  // Each operation carries its own defaults, so reset the form when it changes.
  const chooseOperation = (key) => {
    setOperation(key);
    setValues(defaultValues(key));
  };

  const compatibleInputs = useMemo(
    () => inputs.filter((item) => definition.accepts.includes(item.extension)),
    [inputs, definition],
  );

  const sourceIsCompatible =
    sourceFile && definition.accepts.includes(sourceFile.extension.toLowerCase());

  /** Merge durable R2 runs with current local jobs while a backfill is in progress. */
  const meshyRuns = useMemo(() => {
    const runs = new Map();
    for (const job of initialMeshyJobs) {
      const files = (job.files || [])
        .filter((file) => [".obj", ".dxf"].includes(file.extension))
        .map((file) => ({ ...file, source: "local", jobId: job.id }));
      if (files.length) {
        runs.set(job.id, {
          id: job.id,
          createdAt: job.createdAt || 0,
          modified: job.createdAt || 0,
          files,
        });
      }
    }

    for (const run of r2Jobs) {
      const r2Files = (run.files || [])
        .filter((file) => [".obj", ".dxf"].includes(file.extension))
        .map((file) => ({ ...file, source: "r2", jobId: run.id }));
      const existing = runs.get(run.id);
      const localByName = new Map((existing?.files || []).map((file) => [file.name, file]));
      for (const file of r2Files) localByName.set(file.name, file);
      if (localByName.size) {
        runs.set(run.id, {
          ...existing,
          ...run,
          files: [...localByName.values()],
        });
      }
    }

    return [...runs.values()].sort(
      (a, b) => (b.modified || b.createdAt || 0) - (a.modified || a.createdAt || 0),
    );
  }, [initialMeshyJobs, r2Jobs]);

  const crystalSummary = useMemo(() => {
    const preset = CRYSTAL_BLANKS[values.template];
    if (!preset) return null;
    const width = Number(values.width) > 0 ? Number(values.width) : preset.width;
    const height = Number(values.height) > 0 ? Number(values.height) : preset.height;
    const depth = Number(values.depth) > 0 ? Number(values.depth) : preset.depth;
    const margin = Number(values.border) > 0 ? Number(values.border) : preset.border;
    const usable = {
      width: Math.max(width - 2 * margin, 0),
      height: Math.max(height - 2 * margin, 0),
      depth: Math.max(depth - 2 * margin, 0),
    };
    const layerSpacing = Number(values.layer_spacing) || 0;
    const maximumPlanes = layerSpacing
      ? Math.max(Math.round(usable.depth / layerSpacing) + 1, 1)
      : Number(values.layers) || null;
    return { width, height, depth, margin, usable, maximumPlanes };
  }, [values]);

  async function uploadFile(file) {
    setNotice(null);
    setUploading(true);
    setUploadProgress(0);
    try {
      const uploaded = await uploadToR2(file, {
        prefix: "uploads",
        onProgress: (ratio) => setUploadProgress(Math.round(ratio * 100)),
      });
      setUploadProgress(100);

      const response = await fetch("/api/r2/import", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ key: uploaded.key }),
      });
      const data = await readResponseJson(response);
      if (!response.ok) throw new Error(data.error || "Could not import the R2 upload");

      setSourceFile(data.file);
      await Promise.all([refreshFiles(), refreshR2Library()]);
    } catch (error) {
      setNotice({ tone: "error", text: error.message });
    } finally {
      setUploading(false);
      setUploadProgress(null);
    }
  }

  /** Materialize a Meshy model from R2, or use the local copy before backfill. */
  async function selectMeshyFile(file) {
    const identity = file.key || `${file.jobId}/${file.name}`;
    setImportingKey(identity);
    setNotice(null);
    try {
      const request =
        file.source === "r2"
          ? { url: "/api/r2/import", body: { key: file.key } }
          : {
              url: "/api/handoff",
              body: {
                from: "meshy-output",
                to: "converter-input",
                path: file.path || `${file.jobId}/${file.name}`,
                jobId: file.jobId,
              },
            };
      const response = await fetch(request.url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request.body),
      });
      const data = await readResponseJson(response);
      if (!response.ok) throw new Error(data.error || "Could not open that Meshy model");
      setSourceFile(data.file);
      if (data.template || data.customSize) {
        setValues((current) => ({
          ...current,
          ...(data.template ? { template: data.template } : {}),
          ...(data.customSize
            ? {
                width: data.customSize.width || 0,
                height: data.customSize.height || 0,
                depth: data.customSize.depth || 0,
              }
            : {}),
        }));
      }
      await refreshFiles();
    } catch (error) {
      setNotice({ tone: "error", text: error.message });
    } finally {
      setImportingKey(null);
    }
  }

  async function run() {
    if (!sourceFile) {
      setNotice({ tone: "error", text: "Pick a file first." });
      return;
    }

    setRunning(true);
    setLines([]);
    setNotice(null);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const response = await fetch("/api/convert", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ operation, file: sourceFile.path, values }),
        signal: controller.signal,
      });

      if (!response.ok) {
        const data = await readResponseJson(response);
        throw new Error(data.error || `Server returned ${response.status}`);
      }

      await readSse(response, (event) => {
        if (event.type === "done") {
          setLines((current) => [
            ...current,
            {
              type: event.code === 0 ? "done" : "error",
              text: event.code === 0 ? "Finished." : `Exited with code ${event.code}.`,
            },
          ]);
        } else {
          setLines((current) => [
            ...current,
            { type: event.type, text: event.line ?? event.message ?? "" },
          ]);
        }
      });

      await refreshFiles();
    } catch (error) {
      if (error.name !== "AbortError") {
        setNotice({ tone: "error", text: error.message });
      }
    } finally {
      setRunning(false);
      abortRef.current = null;
    }
  }

  const recentOutputs = outputs.slice(0, 15);

  return (
    <div className="space-y-8">
      {/* Header - the shell owns the theme control and the breadcrumb */}
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold">{t("Crystal Converter")}</h1>
        <p className="max-w-3xl text-sm text-muted">
          {t("Upload a model, choose what happens to it, download something the SSLE engraver reads.")}
        </p>
      </header>

      {notice ? (
        <div className="rounded-lg border border-danger-border bg-danger-soft px-4 py-3 text-sm text-danger-text">
          {notice.text}
        </div>
      ) : null}

      {/* Durable source library comes first: a VPS rebuild must not hide Meshy work. */}
      <section className={`${CARD} space-y-4`}>
        <div className="flex flex-wrap items-baseline justify-between gap-3">
          <div>
            <h2 className={SECTION_TITLE}>{t("Meshy projects · R2 source library")}</h2>
            <p className="mt-1 text-xs text-muted">
              {t("Finished Meshy models live in private R2 storage; choosing one copies a working file into the converter.")}
            </p>
          </div>
          <button
            type="button"
            onClick={refreshR2Library}
            disabled={libraryLoading}
            className="text-xs text-muted transition hover:text-foreground disabled:opacity-50"
          >
            {libraryLoading ? t("refreshing…") : t("refresh library")}
          </button>
        </div>

        {meshyRuns.length ? (
          <div className="max-h-80 space-y-2 overflow-y-auto pr-1">
            {meshyRuns.map((run) => (
              <details key={run.id} className="rounded-lg border border-surface-border bg-surface-sunken">
                <summary className="cursor-pointer px-4 py-3 text-sm">
                  <span className="font-medium">{run.id}</span>
                  <span className="ml-2 text-xs text-muted">
                    {run.files.length} converter model{run.files.length === 1 ? "" : "s"}
                  </span>
                </summary>
                <ul className="border-t border-surface-border px-2 py-2">
                  {run.files.map((file) => {
                    const identity = file.key || `${file.jobId}/${file.name}`;
                    return (
                      <li key={identity}>
                        <button
                          type="button"
                          onClick={() => selectMeshyFile(file)}
                          disabled={Boolean(importingKey)}
                          className="flex w-full items-center justify-between gap-4 rounded-md px-2 py-2 text-left transition hover:bg-surface-hover disabled:opacity-50"
                        >
                          <span className="min-w-0 truncate text-sm">{file.name}</span>
                          <span className="shrink-0 font-mono text-xs text-muted">
                            {importingKey === identity
                              ? "opening…"
                              : `${formatBytes(file.bytes)} · ${file.source === "r2" ? "R2" : "local"}`}
                          </span>
                        </button>
                      </li>
                    );
                  })}
                </ul>
              </details>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted">
            {libraryLoading
              ? t("Reading the Meshy archive…")
              : r2Configured === false
                ? t("R2 is not available on this server.")
                : t("No OBJ or DXF models are archived yet.")}
          </p>
        )}
      </section>

      {/* Step 1 - source file */}
      <section className={`${CARD} space-y-4`}>
        <div className="flex items-baseline justify-between gap-4">
          <h2 className={SECTION_TITLE}>1 &middot; {t("Source file")}</h2>
          <span className="font-mono text-xs text-muted">{definition.accepts.join("  ")}</span>
        </div>

        <label className="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-input-border bg-surface-sunken px-6 py-8 text-center transition hover:border-accent">
          <input
            type="file"
            accept={definition.accepts.join(",")}
            className="hidden"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) uploadFile(file);
            }}
          />
          <span className="text-sm">
            {uploading
              ? `Uploading to R2${uploadProgress === null ? "…" : ` · ${uploadProgress}%`}`
              : t("Click to choose a file")}
          </span>
          <span className="text-xs text-muted">
            {t("Stored in private R2 first, then streamed into the converter; large OBJ files bypass the website proxy limit")}
          </span>
        </label>

        {sourceFile ? (
          <div
            className={`flex items-center justify-between gap-4 rounded-lg border px-4 py-3 ${
              sourceIsCompatible
                ? "border-surface-border bg-surface-sunken"
                : "border-warning-border bg-warning-soft"
            }`}
          >
            <div className="min-w-0">
              <p className="truncate text-sm">{sourceFile.name}</p>
              <p className="truncate font-mono text-xs text-muted">
                {formatBytes(sourceFile.bytes)} &middot; {sourceFile.path}
              </p>
            </div>
            {!sourceIsCompatible ? (
              <span className="shrink-0 text-xs text-warning-text">
                wrong type for this operation
              </span>
            ) : null}
          </div>
        ) : null}

        {/* Files already on disk, so nothing needs re-uploading */}
        {compatibleInputs.length ? (
          <details>
            <summary className="cursor-pointer text-xs text-muted hover:text-foreground">
              or pick one of {compatibleInputs.length} files already in input/
            </summary>
            <ul className="mt-3 max-h-56 space-y-0.5 overflow-y-auto">
              {compatibleInputs.map((item) => (
                <li key={item.path}>
                  <button
                    type="button"
                    onClick={() => setSourceFile(item)}
                    className="flex w-full items-center justify-between gap-4 rounded-md px-3 py-2 text-left text-sm transition hover:bg-surface-hover"
                  >
                    <span className="truncate">{item.path}</span>
                    <span className="shrink-0 font-mono text-xs text-muted">
                      {formatBytes(item.bytes)}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </details>
        ) : null}
      </section>

      {/* Step 2 - operation */}
      <section className={`${CARD} space-y-4`}>
        <h2 className={SECTION_TITLE}>2 &middot; {t("Operation")}</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          {OPERATION_KEYS.map((key) => {
            const item = OPERATIONS[key];
            const active = key === operation;
            return (
              <button
                key={key}
                type="button"
                onClick={() => chooseOperation(key)}
                className={`rounded-lg border p-4 text-left transition ${
                  active
                    ? "border-accent bg-accent-soft"
                    : "border-surface-border bg-surface-sunken hover:border-accent"
                }`}
              >
                <p
                  className={`text-sm font-medium ${
                    active ? "text-accent-soft-text" : "text-foreground"
                  }`}
                >
                  {t(item.label)}
                </p>
                <p className="mt-1 text-xs leading-relaxed text-muted">{t(item.blurb)}</p>
              </button>
            );
          })}
        </div>
      </section>

      {/* Step 3 - options */}
      <section className={`${CARD} space-y-5`}>
        <h2 className={SECTION_TITLE}>3 &middot; {t("Options")}</h2>
        {crystalSummary ? (
          <div className="grid gap-3 rounded-lg border border-accent/30 bg-accent-soft p-4 text-xs sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <p className="font-semibold text-accent-soft-text">{t("Physical blank")}</p>
              <p className="mt-1 text-muted-strong">
                {crystalSummary.width} × {crystalSummary.height} × {crystalSummary.depth} mm
              </p>
            </div>
            <div>
              <p className="font-semibold text-accent-soft-text">{t("Effective margin")}</p>
              <p className="mt-1 text-muted-strong">{crystalSummary.margin} mm {t("on every side")}</p>
            </div>
            <div>
              <p className="font-semibold text-accent-soft-text">{t("Usable volume")}</p>
              <p className="mt-1 text-muted-strong">
                {crystalSummary.usable.width} × {crystalSummary.usable.height} ×{" "}
                {crystalSummary.usable.depth} mm
              </p>
            </div>
            <div>
              <p className="font-semibold text-accent-soft-text">{t("Depth reference")}</p>
              <p className="mt-1 text-muted-strong">
                {crystalSummary.maximumPlanes
                  ? `up to about ${crystalSummary.maximumPlanes} planes across usable depth`
                  : t("continuous depth (no layer spacing)")}
              </p>
            </div>
            <p className="sm:col-span-2 lg:col-span-4 text-muted">
              {t("Point spacing controls XY density. Depth-dot spacing thins Z before layering; 0 reuses XY. Layer spacing then defines the final focus planes. “UV” below means mesh texture coordinates—not laser wavelength—so DXF output is equally suitable for a green-beam engraver.")}
            </p>
          </div>
        ) : null}
        <OptionFields
          fields={definition.fields}
          groups={groups}
          values={values}
          onChange={setValues}
          inputs={inputs}
        />
      </section>

      {/* Run controls */}
      <section className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={run}
          disabled={running || !sourceFile || !sourceIsCompatible}
          className="rounded-lg bg-accent px-5 py-2.5 text-sm font-medium text-accent-foreground transition hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-40"
        >
          {running ? t("Converting…") : t("Run conversion")}
        </button>
        {running ? (
          <button
            type="button"
            onClick={() => abortRef.current?.abort()}
            className="rounded-lg border border-surface-border px-4 py-2.5 text-sm transition hover:bg-surface-hover"
          >
            {t("Stop")}
          </button>
        ) : null}
        <p className="text-xs text-muted">
          Large meshes take a few minutes; progress appears below as it happens.
        </p>
      </section>

      <ConsoleLog lines={lines} running={running} />

      {/* Results */}
      <section className={`${CARD} space-y-4`}>
        <div className="flex items-baseline justify-between gap-4">
          <h2 className={SECTION_TITLE}>{t("Results")}</h2>
          <button
            type="button"
            onClick={refreshFiles}
            className="text-xs text-muted transition hover:text-foreground"
          >
            {t("refresh")}
          </button>
        </div>

        {recentOutputs.length === 0 ? (
          <p className="text-sm text-muted">{t("Nothing in output/ yet.")}</p>
        ) : (
          <ul className="divide-y divide-surface-border">
            {recentOutputs.map((item) => (
              <li key={item.path} className="flex items-center justify-between gap-4 py-2.5">
                <div className="min-w-0">
                  <p className="truncate text-sm">{item.name}</p>
                  <p className="truncate font-mono text-xs text-muted">{item.path}</p>
                </div>
                <div className="flex shrink-0 items-center gap-3">
                  <span className="font-mono text-xs text-muted">{formatBytes(item.bytes)}</span>
                  <a
                    href={`/api/download?root=output&path=${encodeURIComponent(item.path)}`}
                    className="rounded-md border border-surface-border px-3 py-1 text-xs transition hover:border-accent hover:text-accent"
                  >
                    {t("download")}
                  </a>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
