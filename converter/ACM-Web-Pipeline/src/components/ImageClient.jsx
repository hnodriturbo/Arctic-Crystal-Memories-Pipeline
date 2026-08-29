"use client";

/*
 * ═══════════════════════════════════════════════════════════════
 * Image Client
 * ═══════════════════════════════════════════════════════════════
 * Path: src/components/ImageClient.jsx
 * Purpose: Drive pipeline one - restore, upscale and cut out a photograph,
 *          then push the result at Meshy.
 */

import { useCallback, useMemo, useRef, useState } from "react";

import ConsoleLog from "@/components/ConsoleLog";
import { useLanguage } from "@/components/LanguageProvider";
import { readSse } from "@/lib/read-sse";
import OptionFields from "@/components/OptionFields";
import {
  IMAGE_FIELD_GROUPS,
  IMAGE_FIELDS,
  PHOTO_TYPES,
  defaultImageValues,
  selectedStages,
} from "@/lib/image/catalog";

const CARD = "rounded-xl border border-surface-border bg-surface p-6";
const SECTION_TITLE = "text-xs font-semibold uppercase tracking-wide text-muted-strong";

/** Human-readable byte size, because "103948887" tells nobody anything. */
function formatBytes(bytes) {
  if (!bytes) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / 1024 ** index).toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

const fileUrl = (path, root, download = false) =>
  `/api/file?root=${root}&path=${encodeURIComponent(path)}${download ? "&download=1" : ""}`;

export default function ImageClient({ initialState, onSendToMeshy }) {
  const { t, locale } = useLanguage();
  const [values, setValues] = useState(defaultImageValues);
  const [selected, setSelected] = useState([]);
  const [photos, setPhotos] = useState(initialState.photos || []);
  const [results, setResults] = useState(initialState.results || []);
  const ready = initialState.ready;

  const [uploading, setUploading] = useState(false);
  const [running, setRunning] = useState(false);
  const [lines, setLines] = useState([]);
  const [notice, setNotice] = useState(null);

  const abortRef = useRef(null);
  const stages = useMemo(() => selectedStages(values), [values]);

  const refresh = useCallback(async () => {
    try {
      const response = await fetch("/api/image/state", { cache: "no-store" });
      const data = await response.json();
      setPhotos(data.photos || []);
      setResults(data.results || []);
    } catch {
      // A listing failure is not worth interrupting the run for.
    }
  }, []);

  const toggle = (photo) =>
    setSelected((current) =>
      current.some((item) => item.path === photo.path)
        ? current.filter((item) => item.path !== photo.path)
        : [...current, photo],
    );

  async function upload(fileList) {
    setNotice(null);
    setUploading(true);
    try {
      const added = [];
      for (const file of fileList) {
        const response = await fetch("/api/upload", {
          method: "POST",
          headers: { "x-filename": encodeURIComponent(file.name), "x-target": "image" },
          body: file,
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Upload failed");
        added.push({ path: data.path, name: data.name, bytes: data.bytes, extension: data.extension });
      }
      setSelected((current) => [...current, ...added]);
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
    if (!stages.length) {
      setNotice({ tone: "error", text: "Turn on at least one stage." });
      return;
    }

    setRunning(true);
    setLines([]);
    setNotice(null);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const response = await fetch("/api/image/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ photos: selected.map((item) => item.path), values }),
        signal: controller.signal,
      });
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.error || `Server returned ${response.status}`);
      }

      await readSse(response, (event) => {
        if (event.type === "result") {
          setLines((current) => [...current, { type: "done", text: `Final: ${event.final}` }]);
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

  /** Copy a cleaned photo into the Meshy workspace and jump there. */
  async function sendOn(item) {
    setNotice(null);
    try {
      const response = await fetch("/api/handoff", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ from: "image-output", to: "meshy-input", path: item.path }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Handoff failed");
      onSendToMeshy?.(data);
    } catch (error) {
      setNotice({ tone: "error", text: error.message });
    }
  }

  return (
    <div className="space-y-8">
      {!ready ? (
        <div className="rounded-lg border border-danger-border bg-danger-soft px-4 py-3 text-sm text-danger-text">
          <p>{locale === "is" ? "Python-umhverfi myndavinnslunnar vantar." : "No Python venv for the image pipeline."}</p>
          <pre className="mt-2 overflow-x-auto font-mono text-xs">
            cd ../image-pipeline{"\n"}python -m venv .venv{"\n"}
            .venv/bin/pip install -r requirements.txt
          </pre>
        </div>
      ) : null}
      {notice ? (
        <div className="rounded-lg border border-danger-border bg-danger-soft px-4 py-3 text-sm text-danger-text">
          {notice.text}
        </div>
      ) : null}

      {/* Step 1 - photos */}
      <section className={`${CARD} space-y-4`}>
        <div className="flex items-baseline justify-between gap-4">
          <h2 className={SECTION_TITLE}>1 &middot; {locale === "is" ? "Ljósmyndir" : "Photographs"}</h2>
          <span className="font-mono text-xs text-muted">{PHOTO_TYPES.join("  ")}</span>
        </div>

        <label className="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-input-border bg-surface-sunken px-6 py-8 text-center transition hover:border-accent">
          <input
            type="file"
            accept={PHOTO_TYPES.join(",")}
            multiple
            className="hidden"
            onChange={(event) => {
              const files = Array.from(event.target.files || []);
              if (files.length) upload(files);
            }}
          />
          <span className="text-sm">{uploading ? "Uploading…" : locale === "is" ? "Smelltu til að bæta við ljósmyndum" : "Click to add photographs"}</span>
          <span className="text-xs text-muted">{locale === "is" ? "Hvert vinnsluþrep keyrir á hverri mynd í röð" : "Every stage runs on each one in turn"}</span>
        </label>

        {photos.length ? (
          <div className="grid max-h-72 grid-cols-3 gap-2 overflow-y-auto sm:grid-cols-6">
            {photos.map((photo) => {
              const active = selected.some((item) => item.path === photo.path);
              return (
                <button
                  key={photo.path}
                  type="button"
                  onClick={() => toggle(photo)}
                  title={`${photo.name} · ${formatBytes(photo.bytes)}`}
                  className={`overflow-hidden rounded-md border transition ${
                    active ? "border-accent" : "border-surface-border hover:border-accent"
                  }`}
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={fileUrl(photo.path, "image-input")}
                    alt={photo.name}
                    className="aspect-square w-full object-cover"
                  />
                </button>
              );
            })}
          </div>
        ) : (
          <p className="text-sm text-muted">{locale === "is" ? "Ekkert er komið í input/ enn." : "Nothing in input/ yet."}</p>
        )}

        {selected.length ? (
          <p className="text-xs text-muted">
            {selected.length} selected &middot;{" "}
            <button
              type="button"
              onClick={() => setSelected([])}
              className="underline hover:text-foreground"
            >
              clear
            </button>
          </p>
        ) : null}
      </section>

      {/* Step 2 - stages */}
      <section className={`${CARD} space-y-5`}>
        <div className="flex items-baseline justify-between gap-4">
          <h2 className={SECTION_TITLE}>2 &middot; {locale === "is" ? "Vinnsluþrep" : "Stages"}</h2>
          <span className="font-mono text-xs text-muted">
            {stages.length ? stages.map((stage) => stage.label).join(" → ") : "none selected"}
          </span>
        </div>
        <OptionFields
          fields={IMAGE_FIELDS}
          groups={IMAGE_FIELD_GROUPS}
          values={values}
          onChange={setValues}
          inputs={[]}
        />
      </section>

      {/* Run controls */}
      <section className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={run}
          disabled={running || !ready || !selected.length}
          className="rounded-lg bg-accent px-5 py-2.5 text-sm font-medium text-accent-foreground transition hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-40"
        >
          {running ? (locale === "is" ? "Vinn…" : "Processing…") : locale === "is" ? "Keyra myndavinnslu" : "Run the chain"}
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
        <p className="text-xs text-muted">Every intermediate is kept, so each stage can be judged.</p>
      </section>

      <ConsoleLog lines={lines} running={running} />

      {/* Results */}
      <section className={`${CARD} space-y-4`}>
        <div className="flex items-baseline justify-between gap-4">
          <h2 className={SECTION_TITLE}>{t("Results")}</h2>
          <button
            type="button"
            onClick={refresh}
            className="text-xs text-muted transition hover:text-foreground"
          >
            {t("refresh")}
          </button>
        </div>

        {results.length === 0 ? (
          <p className="text-sm text-muted">{t("Nothing in output/ yet.")}</p>
        ) : (
          <div className="grid gap-4 sm:grid-cols-3">
            {results.slice(0, 12).map((item) => (
              <figure key={item.path} className="space-y-2">
                {/* Checkerboard behind the image, so transparency reads as transparency */}
                <div
                  className="overflow-hidden rounded-lg border border-surface-border"
                  style={{
                    backgroundImage:
                      "linear-gradient(45deg,#8884 25%,transparent 25%,transparent 75%,#8884 75%),linear-gradient(45deg,#8884 25%,transparent 25%,transparent 75%,#8884 75%)",
                    backgroundSize: "16px 16px",
                    backgroundPosition: "0 0, 8px 8px",
                  }}
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={fileUrl(item.path, "image-output")}
                    alt={item.name}
                    className="aspect-square w-full object-contain"
                  />
                </div>
                <figcaption className="space-y-1">
                  <p className="truncate font-mono text-[11px]">{item.name}</p>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => sendOn(item)}
                      className="rounded-md bg-accent px-2 py-1 text-[10px] font-medium text-accent-foreground transition hover:bg-accent-hover"
                    >
                      {locale === "is" ? "Senda í Meshy →" : "Send to Meshy →"}
                    </button>
                    <a
                      href={fileUrl(item.path, "image-output", true)}
                      className="rounded-md border border-surface-border px-2 py-1 text-[10px] transition hover:border-accent hover:text-accent"
                    >
                      download
                    </a>
                    <span className="ml-auto font-mono text-[10px] text-muted">
                      {formatBytes(item.bytes)}
                    </span>
                  </div>
                </figcaption>
              </figure>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
