"use client";

/*
 * ═══════════════════════════════════════════════════════════════
 * Meshy Client
 * ═══════════════════════════════════════════════════════════════
 * Path: src/components/MeshyClient.jsx
 * Purpose: Drive every Meshy mode - pick inputs, set the options, run it,
 *          look at what came back, and pass it to the next pipeline.
 *
 * The mode comes from the sidebar rather than a picker of its own, so the
 * rail is the single place the app is navigated from.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import ConsoleLog from "@/components/ConsoleLog";
import { useLanguage } from "@/components/LanguageProvider";
import JobResults from "@/components/JobResults";
import OptionFields from "@/components/OptionFields";
import PromptSuggestion from "@/components/PromptSuggestion";
import {
  MESHY_MODES,
  PHOTO_TYPES,
  defaultMeshyValues,
  estimateCredits,
  meshyFieldsFor,
  meshyGroupsFor,
  usableSpace,
} from "@/lib/meshy/catalog";
import { readSse } from "@/lib/read-sse";

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

export default function MeshyClient({
  mode,
  initialState,
  onSendToConverter,
  onGoTo,
  refreshRef,
}) {
  const { t, locale } = useLanguage();
  const definition = MESHY_MODES[mode];

  const [values, setValues] = useState(() => defaultMeshyValues(mode));
  const [selected, setSelected] = useState([]);
  const [photos, setPhotos] = useState(initialState.photos || []);
  // Only what this session produced. Every past job remains in Meshy job history.
  const [sessionJobs, setSessionJobs] = useState([]);
  const [cleaned, setCleaned] = useState(initialState.cleaned || []);
  const [balance, setBalance] = useState(initialState.balance);
  const configured = initialState.configured || {};

  const [uploading, setUploading] = useState(false);
  const [describing, setDescribing] = useState(false);
  const [suggestion, setSuggestion] = useState(null);
  const [running, setRunning] = useState(false);
  const [lines, setLines] = useState([]);
  const [notice, setNotice] = useState(null);

  const abortRef = useRef(null);
  const groups = useMemo(() => meshyGroupsFor(mode), [mode]);
  const fields = useMemo(() => meshyFieldsFor(mode, values), [mode, values]);
  const credits = useMemo(() => estimateCredits(mode, values), [mode, values]);
  const space = usableSpace(values.crystal_template);

  // No effect resets the form on a mode change: the shell keys this component
  // by mode, so switching modes remounts it and the initialisers above do the
  // reset on their own.

  const refresh = useCallback(async () => {
    try {
      const response = await fetch("/api/meshy/state", { cache: "no-store" });
      const data = await response.json();
      setPhotos(data.photos || []);
      setCleaned(data.cleaned || []);
    } catch {
      // A listing failure is not worth interrupting the run for.
    }
  }, []);

  const refreshBalance = useCallback(async () => {
    try {
      const response = await fetch("/api/meshy/balance", { cache: "no-store" });
      const data = await response.json();
      setBalance(data.balance);
    } catch {
      // Credit display is advisory; the runner performs its own authoritative check.
    }
  }, []);

  /*
   * Let the shell pull a refresh after it drops a file into meshy input/.
   *
   * Publishing the callback rather than watching a counter prop: the shell
   * knows exactly when a handoff finished, and an effect that reacts to a
   * changing prop by calling setState is the cascading-render pattern React
   * now warns about.
   */
  useEffect(() => {
    if (!refreshRef) return undefined;
    refreshRef.current = refresh;
    return () => {
      refreshRef.current = null;
    };
  }, [refreshRef, refresh]);

  useEffect(() => {
    const timer = window.setTimeout(refreshBalance, 0);
    return () => window.clearTimeout(timer);
  }, [refreshBalance]);

  /** Copy a step-2 result into Meshy's input folder, then select it. */
  async function takeCleaned(photo) {
    setNotice(null);
    try {
      const response = await fetch("/api/handoff", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ from: "image-output", to: "meshy-input", path: photo.path }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Could not use that image");

      setSelected((current) => [...current, data.file].slice(-definition.photoCount));
      await refresh();
    } catch (error) {
      setNotice({ tone: "error", text: error.message });
    }
  }

  const togglePhoto = (photo) => {
    setSelected((current) => {
      const already = current.some((item) => item.path === photo.path);
      if (already) return current.filter((item) => item.path !== photo.path);
      if (current.length >= definition.photoCount) {
        // Replace the oldest pick rather than silently ignoring the click.
        return [...current.slice(1), photo];
      }
      return [...current, photo];
    });
  };

  async function uploadPhotos(fileList) {
    setNotice(null);
    setUploading(true);
    try {
      const added = [];
      for (const file of fileList) {
        const response = await fetch("/api/upload", {
          method: "POST",
          headers: { "x-filename": encodeURIComponent(file.name), "x-target": "meshy" },
          body: file,
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Upload failed");
        added.push({
          path: data.path,
          name: data.name,
          bytes: data.bytes,
          extension: data.extension,
        });
      }
      setSelected((current) => [...current, ...added].slice(-definition.photoCount));
      await refresh();
    } catch (error) {
      setNotice({ tone: "error", text: error.message });
    } finally {
      setUploading(false);
    }
  }

  /**
   * Ask OpenAI to read the first picked photo.
   *
   * The result is parked in `suggestion` rather than written into the form -
   * a bad reading of a photo should cost a glance, not a silently replaced
   * prompt.
   */
  async function describe() {
    const photo = selected[0];
    if (!photo) {
      setNotice({ tone: "error", text: "Pick a photo first." });
      return;
    }

    setDescribing(true);
    setNotice(null);
    try {
      const response = await fetch("/api/meshy/prompt", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ photo: photo.path, hint: values.prompt || "" }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Prompt generation failed");
      setSuggestion(data);
    } catch (error) {
      setNotice({ tone: "error", text: error.message });
    } finally {
      setDescribing(false);
    }
  }

  // image-to-3d has no prompt of its own; the description is only useful there
  // as a texture prompt, so that is where an accepted suggestion lands.
  const promptTarget = definition.fields.some((field) => field.name === "prompt")
    ? "prompt"
    : "texture_prompt";

  const acceptSuggestion = (accepted) => {
    setValues((current) => ({
      ...current,
      [promptTarget]: accepted.prompt,
      ...(promptTarget === "prompt" && accepted.texture_prompt
        ? { texture_prompt: accepted.texture_prompt }
        : {}),
      subject: accepted.subject || current.subject,
    }));
    setSuggestion(null);
  };

  /** Keep dependent selects inside the combinations Meshy's API accepts. */
  const updateValues = (next) => {
    const normalized = { ...next };
    if (definition.produces === "model" && Array.isArray(normalized.target_formats)) {
      normalized.target_formats = [...new Set(["glb", ...normalized.target_formats])];
    }
    const gptRatios = new Set(["1:1", "16:9", "9:16", "3:2", "2:3"]);
    const meshyRatios = new Set(["1:1", "16:9", "9:16", "4:3", "3:4"]);

    if (normalized.ai_model === "gpt-image-2" && !gptRatios.has(normalized.aspect_ratio)) {
      normalized.aspect_ratio = "1:1";
    }
    if (
      normalized.ai_model?.startsWith("nano-banana") &&
      !meshyRatios.has(normalized.aspect_ratio)
    ) {
      normalized.aspect_ratio = "1:1";
    }
    if (normalized.ai_model === "meshy-5" && normalized.texture_resolution !== "2k") {
      normalized.texture_resolution = "2k";
    }
    setValues(normalized);
  };

  async function run() {
    if (definition.photoCount > 0 && selected.length === 0) {
      setNotice({ tone: "error", text: "Pick at least one photo." });
      return;
    }

    setRunning(true);
    setLines([]);
    setNotice(null);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const response = await fetch("/api/meshy/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode, photos: selected.map((item) => item.path), values }),
        signal: controller.signal,
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.error || `Server returned ${response.status}`);
      }

      await readSse(response, (event) => {
        // A job arrives as an object, not a console line.
        if (event.type === "job") {
          setSessionJobs((current) => [
            event.job,
            ...current.filter((item) => item.id !== event.job.id),
          ]);
          return;
        }
        if (event.type === "done") {
          setLines((current) => [
            ...current,
            {
              type: event.code === 0 ? "done" : "error",
              text: event.code === 0 ? "Finished." : "Job failed.",
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

  const canRun = definition.photoCount === 0 || selected.length > 0;
  const step = definition.photoCount > 0 ? 2 : 1;

  return (
    <div className="space-y-8">
      {/* Header - what this mode is, and what it costs */}
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold">{t(definition.label)}</h1>
        <p className="max-w-3xl text-sm text-muted">{t(definition.blurb)}</p>
      </header>

      {!configured.meshy ? (
        <div className="rounded-lg border border-danger-border bg-danger-soft px-4 py-3 text-sm text-danger-text">
          MESHY_API_KEY is not set. Add it to .env.local and restart the server.
        </div>
      ) : null}
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

      {/* Step 1 - inputs */}
      {definition.photoCount > 0 ? (
        <section className={`${CARD} space-y-4`}>
          <div className="flex items-baseline justify-between gap-4">
            <h2 className={SECTION_TITLE}>
              1 &middot; {t(definition.photoCount > 1 ? "Reference images" : "Photo")}
            </h2>
            <span className="font-mono text-xs text-muted">
              {PHOTO_TYPES.join("  ")} &middot; {selected.length}/{definition.photoCount}
            </span>
          </div>

          <label className="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-input-border bg-surface-sunken px-6 py-8 text-center transition hover:border-accent">
            <input
              type="file"
              accept={PHOTO_TYPES.join(",")}
              multiple={definition.photoCount > 1}
              className="hidden"
              onChange={(event) => {
                const files = Array.from(event.target.files || []);
                if (files.length) uploadPhotos(files);
              }}
            />
            <span className="text-sm">{uploading ? "Uploading…" : t("Click to add images")}</span>
            <span className="text-xs text-muted">
              {t("Or run the image pipeline first and send the result here")}
            </span>
          </label>

          {/* Picked images, in the order Meshy will receive them */}
          {selected.length ? (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
              {selected.map((photo, index) => (
                <figure key={photo.path} className="space-y-1">
                  <div className="relative overflow-hidden rounded-lg border border-accent bg-surface-sunken">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={fileUrl(photo.path, "meshy-input")}
                      alt={photo.name}
                      className="aspect-square w-full object-contain"
                    />
                    <button
                      type="button"
                      onClick={() => togglePhoto(photo)}
                      className="absolute right-1 top-1 rounded bg-console-background/80 px-1.5 py-0.5 font-mono text-[10px] text-console-foreground"
                    >
                      {t("remove")}
                    </button>
                    {definition.photoCount > 1 ? (
                      <span className="absolute left-1 top-1 rounded bg-accent px-1.5 py-0.5 font-mono text-[10px] text-accent-foreground">
                        {index === 0 ? "1 · front" : index + 1}
                      </span>
                    ) : null}
                  </div>
                  <figcaption className="truncate font-mono text-[10px] text-muted">
                    {photo.name}
                  </figcaption>
                </figure>
              ))}
            </div>
          ) : null}

          {/* Images already on disk, so nothing needs re-uploading */}
          {photos.length ? (
            <details>
              <summary className="cursor-pointer text-xs text-muted hover:text-foreground">
                or pick from {photos.length} image(s) already in input/
              </summary>
              <div className="mt-3 grid max-h-72 grid-cols-3 gap-2 overflow-y-auto sm:grid-cols-6">
                {photos.map((photo) => {
                  const active = selected.some((item) => item.path === photo.path);
                  return (
                    <button
                      key={photo.path}
                      type="button"
                      onClick={() => togglePhoto(photo)}
                      title={`${photo.name} · ${formatBytes(photo.bytes)}`}
                      className={`overflow-hidden rounded-md border transition ${
                        active ? "border-accent" : "border-surface-border hover:border-accent"
                      }`}
                    >
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={fileUrl(photo.path, "meshy-input")}
                        alt={photo.name}
                        className="aspect-square w-full object-cover"
                      />
                    </button>
                  );
                })}
              </div>
            </details>
          ) : null}

          {/*
           * Straight from the Image pipeline, without a trip through the library.
           * Clicking one copies it into Meshy's input folder first, because
           * that is the only folder a generation is allowed to read from.
           */}
          {cleaned.length ? (
            <details>
              <summary className="cursor-pointer text-xs text-muted hover:text-foreground">
                or take one of {cleaned.length} image(s) the image pipeline just made
              </summary>
              <div className="mt-3 grid max-h-72 grid-cols-3 gap-2 overflow-y-auto sm:grid-cols-6">
                {cleaned.map((photo) => (
                  <button
                    key={photo.path}
                    type="button"
                    onClick={() => takeCleaned(photo)}
                    title={`${photo.name} · ${formatBytes(photo.bytes)}`}
                    className="overflow-hidden rounded-md border border-surface-border transition hover:border-accent"
                  >
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={fileUrl(photo.path, "image-output")}
                      alt={photo.name}
                      className="aspect-square w-full object-cover"
                    />
                  </button>
                ))}
              </div>
            </details>
          ) : null}
        </section>
      ) : null}

      {/* Prompt builder - suggestion first, form second */}
      {configured.openai && definition.photoCount > 0 ? (
        <section className={`${CARD} space-y-4`}>
          <div className="flex items-baseline justify-between gap-4">
            <h2 className={SECTION_TITLE}>Prompt builder</h2>
            <span className="font-mono text-xs text-muted">OpenAI reads the photo</span>
          </div>
          <p className="text-xs text-muted">
            {promptTarget === "prompt"
              ? "Describes the subject so the generator has words as well as pixels."
              : "Image to 3D takes no prompt of its own - an accepted description becomes the texture prompt, and is worth reading either way for what it says about the photo."}
          </p>

          <button
            type="button"
            onClick={describe}
            disabled={describing || !selected.length}
            className="rounded-lg border border-surface-border px-4 py-2 text-sm transition hover:border-accent disabled:cursor-not-allowed disabled:opacity-40"
          >
            {describing ? "Looking at the photo…" : "Suggest a prompt"}
          </button>

          <PromptSuggestion
            suggestion={suggestion}
            target={promptTarget}
            onAccept={acceptSuggestion}
            onDiscard={() => setSuggestion(null)}
          />
        </section>
      ) : null}

      {/* Options */}
      <section className={`${CARD} space-y-5`}>
        <h2 className={SECTION_TITLE}>{step} &middot; {locale === "is" ? "Stillingar" : "Settings"}</h2>
        <OptionFields
          fields={fields}
          groups={groups}
          values={values}
          onChange={updateValues}
          inputs={[]}
        />
        {space ? (
          <p className="text-xs text-muted">
            {values.crystal_template} leaves {space.width} &times; {space.height} &times;{" "}
            {space.depth} mm of engravable space. Depth is almost always what limits a full 3D
            subject.
          </p>
        ) : null}
      </section>

      {/* Run controls */}
      <section className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={run}
          disabled={running || !canRun || !configured.meshy}
          className="rounded-lg bg-accent px-5 py-2.5 text-sm font-medium text-accent-foreground transition hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-40"
        >
          {running ? t("Generating…") : `${locale === "is" ? "Keyra" : "Run"} ${t(definition.label)}`}
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
          About <span className="font-mono text-foreground">{credits}</span> credits
          {balance != null ? ` · ${balance} left` : ""}.
          {definition.produces === "model" ? " Generation takes one to three minutes." : ""}
        </p>
      </section>

      <ConsoleLog lines={lines} running={running} />

      {/* This run's result, so a generation can be judged without leaving the
          form that made it. Every past job lives in Meshy job history. */}
      {sessionJobs.length ? (
        <section className={`${CARD} space-y-4`}>
          <div className="flex items-baseline justify-between gap-4">
            <h2 className={SECTION_TITLE}>{t("This run")}</h2>
            <button
              type="button"
              onClick={() => onGoTo?.("review")}
              className="text-xs text-accent transition hover:text-accent-hover"
            >
              {t("open jobs and review →")}
            </button>
          </div>
          <JobResults
            jobs={sessionJobs}
            onSendToConverter={onSendToConverter}
            onNotice={setNotice}
            onProjectChange={(action, updatedJob) => {
              setSessionJobs((current) =>
                action === "discard"
                  ? current.filter((job) => job.id !== updatedJob?.id)
                  : current.map((job) => (job.id === updatedJob?.id ? updatedJob : job)),
              );
            }}
            openId={sessionJobs[0]?.id}
          />
        </section>
      ) : null}
    </div>
  );
}
