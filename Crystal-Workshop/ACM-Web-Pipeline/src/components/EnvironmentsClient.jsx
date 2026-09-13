"use client";

/*
 * ═══════════════════════════════════════════════════════════════
 * Environments Client
 * ═══════════════════════════════════════════════════════════════
 * Path: src/components/EnvironmentsClient.jsx
 * Purpose: What each of the three Python environments actually is, and
 *          what that means for the options the other steps offer.
 *
 * Worth its own screen because machines differ in ways that silently
 * change results: the same "auto" engine is Real-ESRGAN on the workstation
 * and lanczos on the VPS. Better to say so here than to leave someone
 * wondering why an upscale looks softer than it did yesterday.
 */

import { useCallback, useState } from "react";

const CARD = "rounded-xl border border-surface-border bg-surface p-6";
const SECTION_TITLE = "text-xs font-semibold uppercase tracking-wide text-muted-strong";

/** Human-readable byte size, because "103948887" tells nobody anything. */
function formatBytes(bytes) {
  if (!bytes) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / 1024 ** index).toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

/** Green when a capability is really there, amber when it degraded gracefully. */
function StatusPill({ ready, readyText = "ready", downText = "fallback" }) {
  return (
    <span
      className={`shrink-0 rounded-full px-2 py-0.5 font-mono text-[10px] ${
        ready
          ? "border border-surface-border bg-surface-sunken text-success-text"
          : "border border-warning-border bg-warning-soft text-warning-text"
      }`}
    >
      {ready ? `✓ ${readyText}` : `~ ${downText}`}
    </span>
  );
}

export default function EnvironmentsClient({ initial }) {
  const [data, setData] = useState(initial);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    setBusy(true);
    try {
      const response = await fetch("/api/environments", { cache: "no-store" });
      setData(await response.json());
    } catch {
      // Leave the last known state on screen rather than blanking it.
    } finally {
      setBusy(false);
    }
  }, []);

  return (
    <div className="space-y-8">
      <header className="flex items-start justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold">🐍 Python environments</h1>
          <p className="max-w-3xl text-sm text-muted">
            Three Python 3.11 environments, kept separate on purpose. What is installed in each decides
            which engines the other steps can actually offer — an option that says
            <span className="font-mono"> auto</span> resolves differently depending on what you see
            here.
          </p>
        </div>
        <button
          type="button"
          onClick={refresh}
          disabled={busy}
          className="shrink-0 rounded-lg border border-surface-border px-3 py-1.5 text-xs transition hover:border-accent disabled:opacity-40"
        >
          {busy ? "checking…" : "re-check"}
        </button>
      </header>

      {data.environments.map((environment) => {
        const probe = environment.probe || {};

        return (
          <section key={environment.id} className={`${CARD} space-y-5`}>
            {/* Identity */}
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <h2 className="flex items-center gap-2 text-lg font-semibold">
                  <span aria-hidden="true">{environment.emoji}</span>
                  {environment.name}
                </h2>
                <p className="mt-0.5 text-sm text-muted">{environment.purpose}</p>
              </div>
              <StatusPill
                ready={probe.ok}
                readyText={probe.python ? `Python ${probe.python}` : "ready"}
                downText="not installed"
              />
            </div>

            {!probe.ok ? (
              <div className="space-y-2 rounded-lg border border-danger-border bg-danger-soft px-4 py-3 text-sm text-danger-text">
                <p>{probe.error}</p>
                <pre className="overflow-x-auto font-mono text-xs">
                  uv venv --python 3.11 {environment.root}/.venv
                  {"\n"}uv pip install --python {environment.root}/.venv/bin/python -r requirements.txt
                </pre>
              </div>
            ) : null}

            {/* What this environment can actually do */}
            <div>
              <h3 className={SECTION_TITLE}>What it can do here</h3>
              <ul className="mt-3 space-y-2">
                {environment.capabilities.map((capability) => (
                  <li
                    key={capability.label}
                    className="flex items-start gap-3 rounded-lg border border-surface-border bg-surface-sunken px-3 py-2"
                  >
                    <span aria-hidden="true" className="text-base leading-tight">
                      {capability.emoji}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block text-sm font-medium">{capability.label}</span>
                      <span className="block text-xs leading-relaxed text-muted">
                        {capability.detail}
                      </span>
                    </span>
                    <StatusPill ready={capability.ready} readyText="full" downText="degraded" />
                  </li>
                ))}
              </ul>
            </div>

            {/* Packages that decide the above */}
            {probe.packages ? (
              <div>
                <h3 className={SECTION_TITLE}>📦 Packages</h3>
                <div className="mt-3 flex flex-wrap gap-2">
                  {Object.entries(probe.packages).map(([name, version]) => (
                    <span
                      key={name}
                      title={version ? `${name} ${version}` : `${name} is not installed here`}
                      className={`rounded-md border px-2 py-1 font-mono text-[11px] ${
                        version
                          ? "border-surface-border bg-surface-sunken text-foreground"
                          : "border-input-border text-muted line-through opacity-60"
                      }`}
                    >
                      {name}
                      {version && version !== "installed" ? ` ${version}` : ""}
                    </span>
                  ))}
                </div>
                {probe.cuda ? (
                  <p className="mt-2 text-xs text-muted">
                    🎮 CUDA:{" "}
                    {probe.cuda.available ? probe.cuda.device : "CPU-only Torch; no CUDA device"}
                  </p>
                ) : (
                  <p className="mt-2 text-xs text-muted">
                    🎮 No torch here, so the GPU engines are unavailable by design.
                  </p>
                )}
              </div>
            ) : null}

            {/* Where it lives and what is in its folders */}
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <h3 className={SECTION_TITLE}>📂 Folders</h3>
                <ul className="mt-2 space-y-1">
                  {environment.folders.map((folder) => (
                    <li
                      key={folder.label}
                      className="flex items-center justify-between gap-3 text-xs"
                    >
                      <span>
                        <span aria-hidden="true">{folder.emoji}</span> {folder.label}
                      </span>
                      <span className="font-mono text-muted">
                        {folder.exists
                          ? `${folder.files} file(s) · ${formatBytes(folder.bytes)}`
                          : "missing"}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="min-w-0">
                <h3 className={SECTION_TITLE}>🔧 Paths</h3>
                <p className="mt-2 break-all font-mono text-[11px] leading-relaxed text-muted">
                  {environment.root}
                  <br />
                  {environment.interpreter}
                </p>
              </div>
            </div>
          </section>
        );
      })}

      {/* Cut-out models, which are large and download on first use */}
      <section className={`${CARD} space-y-3`}>
        <h2 className={SECTION_TITLE}>🧠 Cached cut-out models</h2>
        <p className="text-xs text-muted">
          rembg downloads these on first use, not at install time. A cold first run therefore looks
          like a hang — it is a download. {data.models.directory}
        </p>
        {data.models.models.length === 0 ? (
          <p className="text-sm text-warning-text">
            None cached yet. The first background removal will pull one (birefnet-portrait is
            ~900&nbsp;MB).
          </p>
        ) : (
          <ul className="space-y-1">
            {data.models.models.map((model) => (
              <li key={model.name} className="flex items-center justify-between gap-3 text-xs">
                <span className="font-mono">{model.name}</span>
                <span className="font-mono text-muted">{formatBytes(model.bytes)}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
