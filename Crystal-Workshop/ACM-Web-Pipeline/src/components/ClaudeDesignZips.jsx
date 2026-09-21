"use client";

/*
 * ═══════════════════════════════════════════════════════════════
 * Claude Design Zips
 * ═══════════════════════════════════════════════════════════════
 * Path: src/components/ClaudeDesignZips.jsx
 * Purpose: The zip shelf on its own - which exports have been opened, and
 *          which are still sealed.
 *
 * A separate screen from the animations, because a zip is the one thing in
 * this folder that cannot be previewed, played or rendered until it has been
 * unpacked. Mixed into the same list, a sealed archive looked like a
 * collection with no designs in it, which is the opposite of what it is.
 */

import { useCallback, useEffect, useState } from "react";

import { useLanguage } from "@/components/LanguageProvider";

/** Bytes as something readable at a glance rather than exact. */
function megabytes(bytes) {
  if (!bytes) return "—";
  return `${(bytes / 1048576).toFixed(1)} MB`;
}

/** DD-MM-YYYY, the way dates are written everywhere else in this project. */
function shortDate(milliseconds) {
  if (!milliseconds) return "—";
  const date = new Date(milliseconds);
  const pad = (value) => String(value).padStart(2, "0");
  return `${pad(date.getDate())}-${pad(date.getMonth() + 1)}-${date.getFullYear()}`;
}

export default function ClaudeDesignZips({ onUnpacked }) {
  const { t } = useLanguage();

  const [zips, setZips] = useState(null);
  const [zipDir, setZipDir] = useState("");
  const [notice, setNotice] = useState("");
  const [busyName, setBusyName] = useState("");

  // A counter rather than a call, so the effect below owns the state and a
  // refresh does not set it from an effect body. Same pattern as the
  // animations panel next door.
  const [reloadCount, setReloadCount] = useState(0);
  const load = useCallback(() => setReloadCount((value) => value + 1), []);

  useEffect(() => {
    const controller = new AbortController();

    fetch("/api/claude-design/zips", { cache: "no-store", signal: controller.signal })
      .then(async (response) => {
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || t("Could not read the archive folder."));
        return data;
      })
      .then((data) => {
        setZips(data.zips);
        setZipDir(data.zipDir);
      })
      .catch((error) => {
        if (error.name === "AbortError") return;
        setNotice(error.message);
        setZips([]);
      });

    return () => controller.abort();
  }, [reloadCount, t]);

  async function unpack(name) {
    setBusyName(name);
    setNotice("");
    try {
      const response = await fetch("/api/claude-design/zips", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || t("Unpacking failed."));

      setNotice(`${t("Unpacked into")} ${data.folder}`);
      load();
      // The animations list has a new collection in it now.
      onUnpacked?.();
    } catch (error) {
      setNotice(error.message);
    } finally {
      setBusyName("");
    }
  }

  if (!zips) {
    return <p className="p-5 text-sm text-muted">{t("Reading the archive folder…")}</p>;
  }

  const sealed = zips.filter((zip) => !zip.unpacked);

  return (
    <section className="space-y-4 rounded-2xl border border-surface-border bg-surface p-5">
      {/* Header - where the archives are, and how many still need opening */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <h2 className="text-lg font-semibold">{t("Design archives")}</h2>
          <p className="mt-1 break-all font-mono text-xs text-muted">{zipDir}</p>
        </div>
        <button
          type="button"
          onClick={load}
          className="rounded-lg border border-surface-border px-4 py-2 text-sm hover:bg-surface-hover"
        >
          ↻ {t("Refresh")}
        </button>
      </div>

      <p className="text-sm text-muted">
        {sealed.length
          ? `${sealed.length} ${t("of")} ${zips.length} ${t("archives have no folder behind them yet.")}`
          : t("Every archive here has already been unpacked.")}
      </p>

      {zips.length === 0 ? (
        <p className="rounded-lg border border-dashed border-surface-border p-6 text-center text-sm text-muted">
          {t("No zip files in this folder.")}
        </p>
      ) : (
        <ul className="space-y-2">
          {zips.map((zip) => (
            <li
              key={zip.name}
              className="flex flex-wrap items-center gap-3 rounded-lg bg-surface-sunken p-3"
            >
              <span className="min-w-0 flex-1">
                <span className="block break-all text-sm">{zip.name}</span>
                <span className="block text-[10px] text-muted">
                  {megabytes(zip.bytes)} · {shortDate(zip.modified)}
                </span>
              </span>

              {zip.unpacked ? (
                <span className="shrink-0 rounded-full bg-surface-hover px-3 py-1 text-[10px] text-muted-strong">
                  {t("unpacked")}
                </span>
              ) : (
                <>
                  <span className="shrink-0 rounded-full bg-warning-soft px-3 py-1 text-[10px] text-warning-text">
                    {t("not unpacked")}
                  </span>
                  <button
                    type="button"
                    disabled={Boolean(busyName)}
                    onClick={() => unpack(zip.name)}
                    className="shrink-0 rounded-lg bg-accent px-4 py-2 text-xs text-accent-foreground hover:bg-accent-hover disabled:opacity-40"
                  >
                    {busyName === zip.name ? t("Unpacking…") : t("Unpack")}
                  </button>
                </>
              )}
            </li>
          ))}
        </ul>
      )}

      <p role="status" className="text-sm text-muted">
        {notice ||
          t("Unpacking creates a folder named after the archive. An existing folder is never overwritten.")}
      </p>
    </section>
  );
}
