"use client";

/*
 * ═══════════════════════════════════════════════════════════════
 * Crystal Viewer Client
 * ═══════════════════════════════════════════════════════════════
 * Path: src/components/CrystalViewerClient.jsx
 * Purpose: Look at any GLB, point-cloud DXF or photograph inside a real
 *          blank, without running a pipeline first.
 *
 * This is the bench where the acm.is viewer gets proven. Nothing here touches
 * the server: a dropped file becomes an object URL and is rendered straight
 * out of the browser's own memory, which is both instant and exactly the
 * privacy behaviour the customer-facing version needs.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import CrystalPreview, { PREVIEW_DOT_SIZE_MM } from "@/components/CrystalPreview";
import { useLanguage } from "@/components/LanguageProvider";
import { CRYSTAL_BLANKS, blankOptions } from "@/lib/crystal-blanks";
import { readResponseJson } from "@/lib/response-json";

const CARD = "rounded-xl border border-surface-border bg-surface p-6";
const SECTION_TITLE = "text-xs font-semibold uppercase tracking-wide text-muted-strong";

const ACCEPTS = ".glb,.gltf,.dxf,.png,.jpg,.jpeg,.webp,.bmp";

/** Which of the three renderers a filename asks for. */
function kindOf(name) {
  const clean = String(name || "").toLowerCase();
  if (clean.endsWith(".dxf")) return "dxf";
  if (/\.(png|jpe?g|webp|bmp)$/.test(clean)) return "photo";
  return "glb";
}

function blankDimensions(template) {
  const known = CRYSTAL_BLANKS[template];
  if (known) return { width: known.width, height: known.height, depth: known.depth };
  const parts = String(template || "").split("x").map(Number);
  if (parts.length === 3 && parts.every((value) => value > 0)) {
    return { width: parts[0], height: parts[1], depth: parts[2] };
  }
  return { width: 60, height: 80, depth: 40 };
}

export default function CrystalViewerClient({ handoff = null }) {
  const { locale } = useLanguage();

  const [file, setFile] = useState(null);
  const [template, setTemplate] = useState("60x80x40");
  const [mode, setMode] = useState("points");
  const [maxPoints, setMaxPoints] = useState(400000);
  const [showGlass, setShowGlass] = useState(true);
  const [autoRotate, setAutoRotate] = useState(true);

  const [library, setLibrary] = useState({ configured: false, sources: [] });
  const [notice, setNotice] = useState(null);
  const objectUrlRef = useRef(null);

  const options = useMemo(() => {
    const standard = blankOptions({ includeNone: false });
    if (!handoff?.template || standard.some((option) => option.value === handoff.template)) {
      return standard;
    }
    return [
      { value: handoff.template, label: handoff.template, labelIs: handoff.template },
      ...standard,
    ];
  }, [handoff]);
  const blank = useMemo(() => blankDimensions(template), [template]);

  // The durable photo library lives in R2, so the VPS holds nothing. An
  // unconfigured bucket simply means the section stays hidden.
  useEffect(() => {
    let cancelled = false;
    fetch("/api/relief/library", { cache: "no-store" })
      .then((response) => response.json())
      .then((data) => !cancelled && setLibrary(data))
      .catch(() => {
        // A missing library is not worth an error banner on a viewer.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Revoke the previous object URL whenever it is replaced, or the tab slowly
  // pins every file the operator has looked at into memory.
  const show = useCallback((nextUrl, name) => {
    if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current);
    objectUrlRef.current = nextUrl.startsWith("blob:") ? nextUrl : null;
    setFile({ url: nextUrl, name, kind: kindOf(name) });
  }, []);

  // A finished 2.5D job enters Model B already loaded, while direct uploads
  // remain fully browser-local as before.
  useEffect(() => {
    if (!handoff?.url) return;
    queueMicrotask(() => {
      show(handoff.url, handoff.name || "relief.glb");
      if (handoff.template) setTemplate(handoff.template);
    });
  }, [handoff, show]);

  useEffect(
    () => () => {
      if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current);
    },
    [],
  );

  /** Open a library photograph through a short-lived presigned URL. */
  async function openFromLibrary(source) {
    setNotice(null);
    try {
      const response = await fetch(
        `/api/relief/library/url?key=${encodeURIComponent(source.key)}`,
        { cache: "no-store" },
      );
      const data = await readResponseJson(response);
      if (!response.ok) throw new Error(data.error || "Could not open that file");
      show(data.url, source.label || source.name);
    } catch (error) {
      setNotice(error.message);
    }
  }

  return (
    <div className="space-y-8">
      {notice ? (
        <div className="rounded-lg border border-danger-border bg-danger-soft px-4 py-3 text-sm text-danger-text">
          {notice}
        </div>
      ) : null}

      <section className={`${CARD} space-y-4`}>
        <h2 className={SECTION_TITLE}>1 &middot; {locale === "is" ? "Skrá" : "File"}</h2>

        <p className="text-xs text-muted">
          {locale === "is"
            ? "GLB eða GLTF · þrívíddarmódel. DXF · punktaský frá skráabreytinum. Mynd · flöt greypting eins og viðskiptavinurinn sæi hana. Skráin fer aldrei í netþjóninn — hún er lesin beint í vafranum."
            : "GLB or GLTF · a 3D model. DXF · a point cloud from the converter. An image · a flat engraving, the way a customer would see it. Nothing is uploaded - the file is read straight out of the browser."}
        </p>

        <label className="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-input-border bg-surface-sunken px-6 py-8 text-center transition hover:border-accent">
          <input
            type="file"
            accept={ACCEPTS}
            className="hidden"
            onChange={(event) => {
              const chosen = event.target.files?.[0];
              if (chosen) show(URL.createObjectURL(chosen), chosen.name);
              event.target.value = "";
            }}
          />
          <span className="text-sm text-muted-strong">
            {file
              ? file.name
              : locale === "is"
                ? "Veldu eða dragðu skrá hingað"
                : "Choose or drop a file here"}
          </span>
          <span className="font-mono text-[11px] text-muted">{ACCEPTS.replaceAll(",", "  ")}</span>
        </label>

        {/* The durable R2 photo library - re-open anything already used */}
        {library.configured && library.sources?.length ? (
          <div className="space-y-2 border-t border-surface-border pt-4">
            <span className={SECTION_TITLE}>
              {locale === "is" ? "Úr myndasafninu (R2)" : "From the library (R2)"}
            </span>
            <ul className="grid max-h-56 gap-1.5 overflow-y-auto sm:grid-cols-2">
              {library.sources.map((source) => (
                <li key={source.key}>
                  <button
                    type="button"
                    onClick={() => openFromLibrary(source)}
                    className="w-full truncate rounded-md border border-surface-border px-3 py-1.5 text-left text-xs transition hover:border-accent"
                  >
                    {source.label || source.name}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </section>

      {file ? (
        <section className={`${CARD} space-y-4`}>
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h2 className={SECTION_TITLE}>2 &middot; {locale === "is" ? "Kristallinn" : "The crystal"}</h2>
            <span className="font-mono text-xs text-muted">{file.kind}</span>
          </div>

          <div className="grid items-start gap-4 lg:grid-cols-[minmax(0,1fr)_16rem]">
            <CrystalPreview
              src={file.url}
              kind={file.kind}
              blank={blank}
              mode={mode}
              pointSize={PREVIEW_DOT_SIZE_MM}
              maxPoints={maxPoints}
              showGlass={showGlass}
              autoRotate={autoRotate}
            />

            <div className="space-y-4">
              <label className="block space-y-1">
                <span className="text-xs text-muted">{locale === "is" ? "Kristall" : "Blank"}</span>
                <select
                  value={template}
                  onChange={(event) => setTemplate(event.target.value)}
                  className="w-full rounded-md border border-input-border bg-input-background px-2 py-1.5 text-xs"
                >
                  {options.map((option) => (
                    <option key={option.value} value={option.value}>
                      {locale === "is" ? option.labelIs : option.label}
                    </option>
                  ))}
                </select>
              </label>

              {file.kind === "glb" ? (
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
              ) : null}

              {file.kind !== "photo" ? (
                <div className="rounded-md border border-surface-border bg-surface-sunken px-3 py-2">
                  <span className="block text-xs text-muted">
                    {locale === "is" ? "Punktastærð" : "Dot size"}
                  </span>
                  <strong className="font-mono text-sm text-muted-strong">
                    {PREVIEW_DOT_SIZE_MM.toFixed(2)} mm
                  </strong>
                </div>
              ) : null}

              {file.kind === "dxf" ? (
                <label className="block space-y-1">
                  <span className="text-xs text-muted">
                    {locale === "is" ? "Hámark punkta" : "Point cap"} ·{" "}
                    {maxPoints.toLocaleString()}
                  </span>
                  <input
                    type="range"
                    min="50000"
                    max="1000000"
                    step="50000"
                    value={maxPoints}
                    onChange={(event) => setMaxPoints(Number(event.target.value))}
                    className="w-full"
                  />
                  <span className="block text-[11px] leading-snug text-muted">
                    {locale === "is"
                      ? "Grisjar jafnt yfir allt skýið, ekki fyrstu N punktana."
                      : "Strides evenly across the cloud, not the first N points."}
                  </span>
                </label>
              ) : null}

              <label className="flex items-center gap-2 text-xs text-muted">
                <input type="checkbox" checked={showGlass} onChange={() => setShowGlass((on) => !on)} />
                {locale === "is" ? "Sýna glerið" : "Show the glass"}
              </label>
              <label className="flex items-center gap-2 text-xs text-muted">
                <input
                  type="checkbox"
                  checked={autoRotate}
                  onChange={() => setAutoRotate((on) => !on)}
                />
                {locale === "is" ? "Snúa sjálfkrafa" : "Auto-rotate"}
              </label>
            </div>
          </div>
        </section>
      ) : null}
    </div>
  );
}
