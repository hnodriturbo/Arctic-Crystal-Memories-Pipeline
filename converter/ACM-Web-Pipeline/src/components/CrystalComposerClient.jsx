"use client";

/*
 * ═══════════════════════════════════════════════════════════════
 * Crystal Composer Client — Leið A
 * ═══════════════════════════════════════════════════════════════
 * Path: src/components/CrystalComposerClient.jsx
 * Purpose: Crop a customer photograph into a local Cockpit3D blank and hand
 *          the finished PNG directly to the 2.5D pipeline.
 */

import { useEffect, useMemo, useRef, useState } from "react";
import Cropper from "cropperjs";
import "cropperjs/dist/cropper.css";
import {
  Download,
  ImagePlus,
  Maximize2,
  Minus,
  MoveRight,
  Plus,
  RotateCcw,
  RotateCw,
  Type,
  Upload,
} from "lucide-react";

import { useLanguage } from "@/components/LanguageProvider";
import { renderComposedImage } from "@/lib/relief/render-composed-image";

const CARD = "overflow-hidden rounded-xl border border-surface-border bg-surface";
const FAMILY_ORDER = ["rectangle", "heart", "prestige", "ornament", "diamond", "special"];
const VISUAL_BEVEL_SCALE = 0.64;

const FALLBACK = [
  {
    id: "2d-rectangle-medium-80x50",
    name: "2D Rectangle Medium 80x50",
    width: 50,
    height: 80,
    depth: 50,
    border: [3, 3, 3],
    bevel: 3,
    family: "rectangle",
    maskPoints: null,
  },
];

function words(locale) {
  return locale === "is"
    ? {
        title: "Leið A · Undirbúa mynd",
        subtitle: "Klippa myndina í valið Cockpit3D kristalform áður en 2.5D vinnslan hefst.",
        made: "Gert úr þinni mynd",
        family: "Veldu kristalfjölskyldu",
        template: "Cockpit3D sniðmát og stærð",
        dimensions: "Stærð",
        border: "Rammi",
        bevel: "Fasi",
        upload: "Hladdu upp mynd til að byrja",
        hint: "JPG, PNG, WebP eða önnur mynd sem vafrinn styður.",
        add: "Bæta við mynd",
        replace: "Skipta um mynd",
        startOver: "Byrja upp á nýtt",
        text: "Texti",
        background: "Bakgrunnur",
        download: "Sækja PNG",
        continue: "Senda í 2.5D",
        uploading: "Vista staðbundið…",
        ready: "Myndin er tilbúin fyrir 2.5D vinnslu.",
        failed: "Ekki tókst að útbúa myndina.",
      }
    : {
        title: "Model A · Prepare the image",
        subtitle: "Crop the photograph into its Cockpit3D blank before the 2.5D conversion starts.",
        made: "Made from your photo",
        family: "Choose crystal family",
        template: "Cockpit3D template and size",
        dimensions: "Size",
        border: "Border",
        bevel: "Bevel",
        upload: "Upload a photo to begin",
        hint: "JPG, PNG, WebP, or another browser-supported image.",
        add: "Add photo",
        replace: "Replace photo",
        startOver: "Start over",
        text: "Text",
        background: "Background",
        download: "Download PNG",
        continue: "Send to 2.5D",
        uploading: "Saving locally…",
        ready: "The image is ready for the 2.5D pipeline.",
        failed: "The image could not be prepared.",
      };
}

function clipPath(blank) {
  if (blank.maskPoints?.length >= 3) {
    return `polygon(${blank.maskPoints
      .map(([x, y]) => `${(x * 100).toFixed(2)}% ${(y * 100).toFixed(2)}%`)
      .join(",")})`;
  }
  if (blank.family === "ornament") return "circle(49% at 50% 50%)";
  if (blank.family === "diamond") return "polygon(10% 0,90% 0,100% 10%,100% 90%,90% 100%,10% 100%,0 90%,0 10%)";
  const name = blank.name.toLowerCase();
  if (name.includes("notched")) return "polygon(7% 0,93% 0,100% 7%,100% 88%,88% 100%,12% 100%,0 88%,0 7%)";
  if (name.includes("urn")) return "polygon(8% 0,92% 0,100% 8%,96% 100%,4% 100%,0 8%)";
  return "polygon(3% 0,97% 0,100% 3%,100% 97%,97% 100%,3% 100%,0 97%,0 3%)";
}

function shellStyle(blank) {
  const ratio = blank.width / blank.height;
  const maximum = 84;
  const width = ratio >= 1 ? maximum : maximum * ratio;
  const height = ratio >= 1 ? maximum / ratio : maximum;
  const fallback = Math.min(...(blank.border || [3, 3, 3]).filter((value) => value > 0)) || 3;
  const bevelMm = blank.bevel || fallback;
  const bevelPercent = Math.min(
    5.76,
    Math.max(2.88, (bevelMm / Math.min(blank.width, blank.height)) * 100 * VISUAL_BEVEL_SCALE),
  );
  return {
    left: `${(100 - width) / 2}%`,
    top: `${(100 - height) / 2}%`,
    width: `${width}%`,
    height: `${height}%`,
    padding: `${bevelPercent}%`,
    "--composer-clip": clipPath(blank),
  };
}

function cropSize(blank) {
  const ratio = blank.width / blank.height;
  return ratio >= 1
    ? { width: 1400, height: Math.max(560, Math.round(1400 / ratio)) }
    : { width: Math.max(560, Math.round(1400 * ratio)), height: 1400 };
}

function download(blob, filename) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export default function CrystalComposerClient({ blankOptions = FALLBACK, onContinue }) {
  const { locale } = useLanguage();
  const copy = words(locale);
  const blanks = blankOptions.length ? blankOptions : FALLBACK;
  const defaultBlank = blanks.find((blank) => blank.id === "2d-rectangle-xlarge-120x80") || blanks[0];
  const [blankId, setBlankId] = useState(defaultBlank.id);
  const [family, setFamily] = useState(defaultBlank.family);
  const [photoUrl, setPhotoUrl] = useState("");
  const [text, setText] = useState("");
  const [showText, setShowText] = useState(false);
  const [showBackground, setShowBackground] = useState(true);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const imageRef = useRef(null);
  const inputRef = useRef(null);
  const cropperRef = useRef(null);
  const urlRef = useRef("");

  const activeBlank = blanks.find((blank) => blank.id === blankId) || defaultBlank;
  const families = useMemo(
    () => FAMILY_ORDER.filter((candidate) => blanks.some((blank) => blank.family === candidate)),
    [blanks],
  );
  const familyBlanks = useMemo(
    () => blanks.filter((blank) => blank.family === family),
    [blanks, family],
  );

  useEffect(() => {
    const image = imageRef.current;
    if (!image || !photoUrl) return undefined;
    const frame = window.requestAnimationFrame(() => {
      cropperRef.current?.destroy();
      cropperRef.current = new Cropper(image, {
        aspectRatio: activeBlank.width / activeBlank.height,
        viewMode: 3,
        dragMode: "move",
        autoCropArea: 1,
        movable: true,
        zoomable: true,
        rotatable: true,
        cropBoxMovable: false,
        cropBoxResizable: false,
        guides: false,
        center: false,
        highlight: false,
        background: false,
        toggleDragModeOnDblclick: false,
        responsive: true,
      });
    });
    return () => {
      window.cancelAnimationFrame(frame);
      cropperRef.current?.destroy();
      cropperRef.current = null;
    };
  }, [activeBlank.width, activeBlank.height, photoUrl]);

  useEffect(
    () => () => {
      if (urlRef.current) URL.revokeObjectURL(urlRef.current);
    },
    [],
  );

  function chooseFamily(nextFamily) {
    const first = blanks.find((blank) => blank.family === nextFamily);
    if (!first) return;
    setFamily(nextFamily);
    setBlankId(first.id);
  }

  function openPhoto(file) {
    if (!file?.type.startsWith("image/")) return;
    if (urlRef.current) URL.revokeObjectURL(urlRef.current);
    const nextUrl = URL.createObjectURL(file);
    urlRef.current = nextUrl;
    setPhotoUrl(nextUrl);
    setNotice("");
  }

  function reset() {
    cropperRef.current?.destroy();
    if (urlRef.current) URL.revokeObjectURL(urlRef.current);
    urlRef.current = "";
    setPhotoUrl("");
    setText("");
    setNotice("");
    if (inputRef.current) inputRef.current.value = "";
  }

  async function makeBlob() {
    if (!cropperRef.current) throw new Error("No photograph selected.");
    const croppedCanvas = cropperRef.current.getCroppedCanvas({
      ...cropSize(activeBlank),
      imageSmoothingEnabled: true,
      imageSmoothingQuality: "high",
      fillColor: showBackground ? "#15151a" : "rgba(0,0,0,0)",
    });
    return renderComposedImage({ croppedCanvas, blank: activeBlank, textValue: text, showBackground });
  }

  async function exportPng() {
    if (!photoUrl || busy) return;
    setBusy(true);
    try {
      download(await makeBlob(), `pipeline-input--${activeBlank.id}.png`);
      setNotice(copy.ready);
    } catch {
      setNotice(copy.failed);
    } finally {
      setBusy(false);
    }
  }

  async function continueToPipeline() {
    if (!photoUrl || busy) return;
    setBusy(true);
    setNotice(copy.uploading);
    try {
      const blob = await makeBlob();
      const filename = `composer--${activeBlank.id}.png`;
      const response = await fetch("/api/upload", {
        method: "POST",
        headers: { "x-target": "relief", "x-filename": encodeURIComponent(filename) },
        body: blob,
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || "Upload failed.");
      setNotice(copy.ready);
      onContinue?.({
        path: result.path,
        name: result.name,
        blankId: activeBlank.id,
        blankName: activeBlank.name,
        template: `${activeBlank.width}x${activeBlank.height}x${activeBlank.depth}`,
        border: activeBlank.border?.[0] || 1,
        bevel: activeBlank.bevel || null,
      });
    } catch {
      setNotice(copy.failed);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-5">
      <header>
        <p className="text-xs font-semibold uppercase tracking-wider text-accent">Leið A · 2D</p>
        <h1 className="mt-1 text-2xl font-semibold text-foreground sm:text-3xl">{copy.title}</h1>
        <p className="mt-2 max-w-3xl text-sm leading-relaxed text-muted">{copy.subtitle}</p>
      </header>

      <div className="grid gap-5 lg:grid-cols-[minmax(18rem,0.82fr)_minmax(0,1.18fr)] lg:items-start">
        <aside className="space-y-4 lg:sticky lg:top-24">
          <section className={CARD}>
            <h2 className="bg-[#fb6c37] px-4 py-3 text-center text-base font-semibold uppercase text-white">
              {copy.made}
            </h2>
            <div className="space-y-5 p-4">
              <div>
                <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-strong">{copy.family}</h3>
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-2 xl:grid-cols-3">
                  {families.map((candidate) => {
                    const preview = blanks.find((blank) => blank.family === candidate);
                    return (
                      <button
                        key={candidate}
                        type="button"
                        onClick={() => chooseFamily(candidate)}
                        className={`rounded-lg border-2 p-2 transition ${
                          family === candidate ? "border-[#fb6c37] bg-[#fb6c37]/10" : "border-surface-border hover:border-[#fb6c37]/60"
                        }`}
                      >
                        <span className="flex h-12 items-center justify-center rounded-md bg-black">
                          <span
                            className="composer-mini-blank"
                            style={{ "--composer-clip": clipPath(preview), aspectRatio: `${preview.width}/${preview.height}` }}
                          />
                        </span>
                        <span className="mt-1 block text-xs capitalize text-muted-strong">{candidate}</span>
                      </button>
                    );
                  })}
                </div>
              </div>

              <label className="block">
                <span className="mb-2 block text-xs font-semibold uppercase tracking-wide text-muted-strong">{copy.template}</span>
                <select
                  value={blankId}
                  onChange={(event) => setBlankId(event.target.value)}
                  className="w-full rounded-md border border-input-border bg-input-background px-3 py-2 text-sm"
                >
                  {familyBlanks.map((blank) => (
                    <option key={blank.id} value={blank.id}>{blank.name.replace(/^2D\s+/i, "")}</option>
                  ))}
                </select>
              </label>

              <dl className="grid grid-cols-3 gap-2 rounded-lg border border-surface-border bg-surface-sunken p-3 text-center">
                <div><dt className="text-[10px] uppercase text-muted">{copy.dimensions}</dt><dd className="mt-1 text-xs font-semibold">{activeBlank.width}×{activeBlank.height}×{activeBlank.depth}</dd></div>
                <div><dt className="text-[10px] uppercase text-muted">{copy.border}</dt><dd className="mt-1 text-xs font-semibold">{activeBlank.border?.join("×") || "—"}</dd></div>
                <div><dt className="text-[10px] uppercase text-muted">{copy.bevel}</dt><dd className="mt-1 text-xs font-semibold">{activeBlank.bevel || "—"} mm</dd></div>
              </dl>
            </div>
          </section>

          <div className="grid grid-cols-[1fr_auto_1fr_auto_1fr] items-center gap-1 rounded-xl border border-surface-border bg-surface p-3 text-center text-[11px] font-semibold">
            <span className="rounded bg-surface-sunken p-2">Leið A</span><MoveRight className="h-3 w-3" /><span className="rounded bg-surface-sunken p-2">2.5D</span><MoveRight className="h-3 w-3" /><span className="rounded bg-surface-sunken p-2">Leið B</span>
          </div>
        </aside>

        <div className="min-w-0 space-y-3">
          <section className="composer-stage relative mx-auto aspect-square w-full max-w-[660px] overflow-hidden rounded-xl border-2 border-[#8b8b8b] bg-black shadow-xl">
            {photoUrl ? (
              <div className="absolute left-2 right-2 top-2 z-30 flex flex-wrap items-start justify-between gap-2">
                <button type="button" onClick={() => setShowText((visible) => !visible)} className="flex min-h-9 items-center gap-2 rounded-full bg-[#1d2731] px-3 text-xs font-medium text-white"><Type className="h-4 w-4" />{copy.text}</button>
                <div className="flex items-center rounded-xl bg-[#f3f4f6]/95 p-1 text-black shadow-xl">
                  <button type="button" onClick={() => cropperRef.current?.rotate(-5)} className="rounded p-1.5 hover:bg-black/10" aria-label="Rotate left"><RotateCcw className="h-4 w-4" /></button>
                  <button type="button" onClick={() => cropperRef.current?.rotate(5)} className="rounded p-1.5 hover:bg-black/10" aria-label="Rotate right"><RotateCw className="h-4 w-4" /></button>
                  <button type="button" onClick={() => cropperRef.current?.zoom(-0.08)} className="rounded p-1.5 hover:bg-black/10" aria-label="Zoom out"><Minus className="h-4 w-4" /></button>
                  <button type="button" onClick={() => cropperRef.current?.zoom(0.08)} className="rounded p-1.5 hover:bg-black/10" aria-label="Zoom in"><Plus className="h-4 w-4" /></button>
                  <button type="button" onClick={() => cropperRef.current?.reset()} className="rounded p-1.5 hover:bg-black/10" aria-label="Fit photo"><Maximize2 className="h-4 w-4" /></button>
                  <button type="button" onClick={() => setShowBackground((visible) => !visible)} className={`ml-1 rounded-full px-2 py-1.5 text-[10px] font-bold ${showBackground ? "bg-[#ffbf00]" : "bg-[#111827] text-white"}`}>{copy.background}</button>
                </div>
              </div>
            ) : null}

            {showText && photoUrl ? (
              <div className="absolute left-2 top-14 z-40 w-[min(20rem,calc(100%-1rem))] rounded-lg bg-[#f3f4f6] p-3 shadow-xl">
                <label className="block text-xs font-semibold uppercase text-[#4b5563]">{copy.text}</label>
                <input value={text} maxLength={40} onChange={(event) => setText(event.target.value)} className="mt-1 w-full rounded border border-gray-300 bg-white px-3 py-2 text-sm text-black" />
              </div>
            ) : null}

            <div className="composer-shell" style={shellStyle(activeBlank)}>
              <div className={`composer-face ${showBackground ? "bg-[#15151a]" : "bg-transparent"}`}>
                {photoUrl ? (
                  // CropperJS needs the real image element; the source is a browser-local Blob URL.
                  // eslint-disable-next-line @next/next/no-img-element
                  <img ref={imageRef} src={photoUrl} alt="Customer upload" className="block max-w-full" />
                ) : (
                  <button type="button" onClick={() => inputRef.current?.click()} className="flex h-full w-full flex-col items-center justify-center gap-2 bg-black/60 p-5 text-center text-white">
                    <Upload className="h-8 w-8" /><span className="text-sm font-semibold">{copy.upload}</span><span className="max-w-56 text-[11px] text-white/70">{copy.hint}</span>
                  </button>
                )}
                {photoUrl && text.trim() ? <span className="composer-text">{text.trim()}</span> : null}
              </div>
            </div>
          </section>

          <input ref={inputRef} type="file" accept="image/*" className="sr-only" onChange={(event) => openPhoto(event.target.files?.[0])} />
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
            <button type="button" onClick={() => inputRef.current?.click()} className="flex items-center justify-center gap-2 rounded-md border border-surface-border px-3 py-2 text-sm hover:border-accent"><ImagePlus className="h-4 w-4" />{photoUrl ? copy.replace : copy.add}</button>
            <button type="button" disabled={!photoUrl || busy} onClick={reset} className="flex items-center justify-center gap-2 rounded-md border border-surface-border px-3 py-2 text-sm disabled:opacity-40"><RotateCcw className="h-4 w-4" />{copy.startOver}</button>
            <button type="button" disabled={!photoUrl || busy} onClick={exportPng} className="flex items-center justify-center gap-2 rounded-md border border-surface-border px-3 py-2 text-sm disabled:opacity-40"><Download className="h-4 w-4" />{copy.download}</button>
            <button type="button" disabled={!photoUrl || busy} onClick={continueToPipeline} className="flex items-center justify-center gap-2 rounded-md bg-accent px-3 py-2 text-sm font-medium text-accent-foreground disabled:opacity-40"><MoveRight className="h-4 w-4" />{copy.continue}</button>
          </div>
          <p aria-live="polite" className="min-h-5 text-center text-xs text-muted">{notice}</p>
        </div>
      </div>

      <style jsx global>{`
        .composer-stage { background: linear-gradient(125deg, #00344f 0%, #061016 48%, #6a3400 100%); }
        .composer-mini-blank { display: block; height: 76%; max-width: 78%; min-width: 28%; background: linear-gradient(135deg,#6d6e68 0 14%,#f1f1f0 14% 82%,#aaaeb4 82% 100%); clip-path: var(--composer-clip); }
        .composer-shell { position: absolute; z-index: 10; box-sizing: border-box; background: linear-gradient(135deg,#7f8078 0 10%,#30312d 10% 42%,#111311 42% 66%,#c3c5ca 66% 84%,#5d5e58 84% 100%); clip-path: var(--composer-clip); filter: drop-shadow(0 12px 22px rgba(0,0,0,.68)); }
        .composer-face { position: relative; width: 100%; height: 100%; overflow: hidden; clip-path: var(--composer-clip); }
        .composer-face .cropper-container { width: 100% !important; height: 100% !important; filter: grayscale(1) contrast(1.08); }
        .composer-face .cropper-modal { background: #000; opacity: .15; }
        .composer-face .cropper-view-box { outline: 2px dashed #ffca00; outline-offset: -2px; }
        .composer-face .cropper-line, .composer-face .cropper-point { background-color: #ffca00; opacity: 1; }
        .composer-text { position: absolute; left: 8%; right: 8%; bottom: 6%; z-index: 25; overflow: hidden; color: white; text-align: center; font-weight: 600; font-size: clamp(12px,2.2vw,26px); line-height: 1.1; text-shadow: -1px -1px 0 #000,1px -1px 0 #000,-1px 1px 0 #000,1px 1px 0 #000; pointer-events: none; }
      `}</style>
    </div>
  );
}
