"use client";

/*
 * ═══════════════════════════════════════════════════════════════
 * Photo Library
 * ═══════════════════════════════════════════════════════════════
 * Path: src/components/PhotoLibrary.jsx
 * Purpose: Step 1 - everything the pipeline has to work with, and the one
 *          place new photographs come in.
 *
 * Three folders, shown side by side because the difference matters: what was
 * uploaded, what the image pipeline made of it, and what is queued for Meshy.
 * A photograph can be pushed from any of them to the next step without going
 * through the step in between.
 */

import { useCallback, useState } from "react";
import { useLanguage } from "@/components/LanguageProvider";

const CARD = "rounded-xl border border-surface-border bg-surface p-6";
const SECTION_TITLE = "text-xs font-semibold uppercase tracking-wide text-muted-strong";
const PHOTO_TYPES = [".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"];

/** Human-readable byte size, because "103948887" tells nobody anything. */
function formatBytes(bytes) {
  if (!bytes) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / 1024 ** index).toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

const fileUrl = (path, root) => `/api/file?root=${root}&path=${encodeURIComponent(path)}`;

export default function PhotoLibrary({ image, meshy, onRefresh, onGoTo }) {
  const { t, locale } = useLanguage();
  const [uploading, setUploading] = useState(false);
  const [notice, setNotice] = useState(null);
  const [target, setTarget] = useState("image");

  const refresh = useCallback(() => onRefresh?.(), [onRefresh]);

  async function upload(fileList) {
    setNotice(null);
    setUploading(true);
    try {
      for (const file of fileList) {
        const response = await fetch("/api/upload", {
          method: "POST",
          headers: { "x-filename": encodeURIComponent(file.name), "x-target": target },
          body: file,
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Upload failed");
      }
      setNotice({
        tone: "ok",
        text:
          target === "image"
            ? "Uploaded. Open Prepare image when you are ready to clean it."
            : "Uploaded straight to Meshy's own input folder and ready for generation.",
      });
      refresh();
    } catch (error) {
      setNotice({ tone: "error", text: error.message });
    } finally {
      setUploading(false);
    }
  }

  /** Copy one file between two pipeline folders. */
  async function send(from, to, path) {
    setNotice(null);
    try {
      const response = await fetch("/api/handoff", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ from, to, path }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Could not move that file");
      setNotice({ tone: "ok", text: `${data.file.name} copied.` });
      refresh();
    } catch (error) {
      setNotice({ tone: "error", text: error.message });
    }
  }

  const shelf = (title, blurb, items, root, action) => (
    <section className={`${CARD} space-y-3`}>
      <div className="flex items-baseline justify-between gap-4">
        <div>
          <h2 className={SECTION_TITLE}>{t(title)}</h2>
          <p className="mt-0.5 text-xs text-muted">{t(blurb)}</p>
        </div>
        <span className="shrink-0 font-mono text-xs text-muted">{items.length}</span>
      </div>

      {items.length === 0 ? (
        <p className="text-sm text-muted">{locale === "is" ? "Tómt." : "Empty."}</p>
      ) : (
        <div className="grid max-h-96 grid-cols-2 gap-3 overflow-y-auto sm:grid-cols-4">
          {items.slice(0, 40).map((item) => (
            <figure key={item.path} className="space-y-1">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={fileUrl(item.path, root)}
                alt={item.name}
                title={`${item.name} · ${formatBytes(item.bytes)}`}
                className="aspect-square w-full rounded-md border border-surface-border object-cover"
              />
              <figcaption className="space-y-1">
                <p className="truncate font-mono text-[10px] text-muted">{item.name}</p>
                {action ? (
                  <button
                    type="button"
                    onClick={() => action.run(item)}
                    className="w-full rounded-md border border-surface-border px-2 py-0.5 text-[10px] transition hover:border-accent hover:text-accent"
                  >
                    {t(action.label)}
                  </button>
                ) : null}
              </figcaption>
            </figure>
          ))}
        </div>
      )}
    </section>
  );

  return (
    <div className="space-y-8">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold">{locale === "is" ? "Myndasafn" : "Photo library"}</h1>
        <p className="max-w-3xl text-sm text-muted">
          {locale === "is"
            ? "Allar myndir sem vinnslulínurnar geta notað. Hladdu upp hér og sendu mynd áfram í rétta vinnslu; myndahreinsun og beint Meshy-inntak eru aðskilin."
            : "Everything the pipeline can work with. Upload here, then move a photograph on to whichever pipeline you actually need — image cleanup and direct Meshy uploads stay separate."}
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

      {/* Upload, with a choice of which folder it lands in */}
      <section className={`${CARD} space-y-4`}>
        <h2 className={SECTION_TITLE}>{locale === "is" ? "Bæta við ljósmyndum" : "Add photographs"}</h2>

        <div className="flex flex-wrap gap-2">
          {[
            { id: "image", label: "For the Image pipeline" },
            { id: "meshy", label: "Directly to Meshy" },
          ].map((option) => (
            <button
              key={option.id}
              type="button"
              onClick={() => setTarget(option.id)}
              className={`rounded-md border px-3 py-1.5 text-sm transition ${
                target === option.id
                  ? "border-accent bg-accent-soft text-accent-soft-text"
                  : "border-input-border bg-input-background text-muted hover:border-accent"
              }`}
            >
              {locale === "is"
                ? option.id === "image"
                  ? "Í myndavinnslu"
                  : "Beint í Meshy"
                : option.label}
            </button>
          ))}
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
          <span className="text-sm">{uploading ? "Uploading…" : locale === "is" ? "Smelltu til að velja ljósmyndir" : "Click to choose photographs"}</span>
          <span className="text-xs text-muted">
            Streamed straight to disk &middot; {PHOTO_TYPES.join(" ")}
          </span>
        </label>
      </section>

      {shelf(
        "Uploaded",
        "Waiting in the image pipeline's input folder.",
        image.photos || [],
        "image-input",
        {
          label: locale === "is" ? "senda í Meshy →" : "send to Meshy →",
          run: (item) => send("image-input", "meshy-input", item.path),
        },
      )}

      {shelf(
        "Cleaned",
        "What the Image pipeline produced. Every stage is kept, so pick the one that looks right.",
        image.results || [],
        "image-output",
        {
          label: locale === "is" ? "senda í Meshy →" : "send to Meshy →",
          run: (item) => send("image-output", "meshy-input", item.path),
        },
      )}

      {shelf(
        "Ready for Meshy",
        "Meshy generation screens pick from this dedicated folder.",
        meshy.photos || [],
        "meshy-input",
        { label: locale === "is" ? "opna Mynd → 3D" : "open Image → 3D", run: () => onGoTo?.("meshy:image_to_3d") },
      )}
    </div>
  );
}
