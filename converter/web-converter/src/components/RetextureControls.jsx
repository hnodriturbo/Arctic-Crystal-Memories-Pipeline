"use client";

/*
 * ═══════════════════════════════════════════════════════════════
 * Retexture Controls
 * ═══════════════════════════════════════════════════════════════
 * Path: src/components/RetextureControls.jsx
 * Purpose: Apply one or more non-destructive Meshy texture variants while a
 *          generated model is still open for local review.
 */

import { useState } from "react";

import { useLanguage } from "@/components/LanguageProvider";
import { readSse } from "@/lib/read-sse";
import { readResponseJson } from "@/lib/response-json";

const FORMAT_OPTIONS = ["glb", "obj", "fbx", "stl", "usdz", "3mf"];

export default function RetextureControls({ job, onJobUpdated, onNotice }) {
  const { locale } = useLanguage();
  const isIcelandic = locale === "is";
  const initialPrompt = String(job.values?.texture_prompt || "").slice(0, 600);

  const [prompt, setPrompt] = useState(initialPrompt);
  const [aiModel, setAiModel] = useState("latest");
  const [textureResolution, setTextureResolution] = useState("4k");
  const [enableOriginalUv, setEnableOriginalUv] = useState(true);
  const [enablePbr, setEnablePbr] = useState(true);
  const [removeLighting, setRemoveLighting] = useState(true);
  const [targetFormats, setTargetFormats] = useState(["glb", "obj"]);
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState(null);
  const [statusLine, setStatusLine] = useState("");

  const estimatedCredits = textureResolution === "8k" ? 15 : 10;

  function toggleFormat(format) {
    if (format === "glb") return;
    setTargetFormats((current) =>
      current.includes(format)
        ? current.filter((item) => item !== format)
        : [...current, format],
    );
  }

  async function runRetexture() {
    const trimmedPrompt = prompt.trim();
    if (!trimmedPrompt) {
      onNotice?.({
        tone: "error",
        text: isIcelandic ? "Skrifaðu texture prompt fyrst." : "Enter a texture prompt first.",
      });
      return;
    }

    setRunning(true);
    setProgress(0);
    setStatusLine(isIcelandic ? "Sendi í Meshy…" : "Sending to Meshy…");
    onNotice?.(null);
    let streamError = null;
    let completedJob = null;

    try {
      const response = await fetch("/api/meshy/retexture", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          jobId: job.id,
          values: {
            textStylePrompt: trimmedPrompt,
            aiModel,
            textureResolution,
            enableOriginalUv,
            enablePbr,
            removeLighting,
            targetFormats,
          },
        }),
      });

      if (!response.ok) {
        const data = await readResponseJson(response);
        throw new Error(data.error || `Server returned ${response.status}`);
      }

      await readSse(response, (event) => {
        if (event.type === "job") {
          completedJob = event.job;
          onJobUpdated?.(event.job);
        } else if (event.type === "progress") {
          setProgress(Number(event.percent || 0));
          setStatusLine(event.line || event.status || "Retexture");
        } else if (event.type === "step" || event.type === "stdout") {
          setStatusLine(event.line || "");
        } else if (event.type === "error") {
          streamError = new Error(event.message || "Retexture failed.");
          setStatusLine(event.message || "Retexture failed.");
        }
      });

      if (streamError) throw streamError;
      setProgress(100);
      onNotice?.({
        tone: "ok",
        text: isIcelandic
          ? `Nýr ${textureResolution.toUpperCase()} textúr er tilbúinn. GLB-preview sýnir nýjustu útgáfuna.`
          : `The new ${textureResolution.toUpperCase()} texture is ready. The GLB preview now shows the latest version.`,
      });
      if (completedJob) onJobUpdated?.(completedJob);
    } catch (error) {
      if (error.name !== "AbortError") {
        onNotice?.({ tone: "error", text: error.message });
      }
    } finally {
      setRunning(false);
    }
  }

  return (
      <div className="space-y-4 rounded-lg border border-accent/40 bg-accent-soft/30 p-4">
      <div className="space-y-1">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-sm font-semibold">
            {isIcelandic ? "Nýr textúr á sama módel" : "New texture on the same model"}
          </h3>
          <span className="font-mono text-xs text-muted">
            {estimatedCredits} {isIcelandic ? "credits" : "credits"}
          </span>
        </div>
        <p className="text-xs leading-relaxed text-muted">
          {isIcelandic
            ? "Retexture varðveitir rúmfræðina. Þú getur prófað fleiri en einn textúr áður en projectið er vistað í R2 eða því hent."
            : "Retexture preserves the geometry. You can try multiple texture variants before keeping the project in R2 or discarding it."}
        </p>
      </div>

      {job.retextureError ? (
        <p className="rounded-md border border-danger-border bg-danger-soft px-3 py-2 text-xs text-danger-text">
          {job.retextureError}
        </p>
      ) : null}

      <label className="block space-y-1.5">
        <span className="flex items-center justify-between gap-3 text-xs font-medium">
          <span>Texture prompt</span>
          <span className="font-mono text-muted">{prompt.length}/600</span>
        </span>
        <textarea
          value={prompt}
          maxLength={600}
          rows={5}
          onChange={(event) => setPrompt(event.target.value)}
          placeholder={
            isIcelandic
              ? "Lýstu efnum, litum, sliti og yfirborðsáferð…"
              : "Describe materials, colours, wear and surface finish…"
          }
          className="w-full rounded-lg border border-input-border bg-input-background px-3 py-2 text-sm outline-none transition focus:border-accent"
        />
      </label>

      <div className="grid gap-3 sm:grid-cols-2">
        <label className="space-y-1 text-xs font-medium">
          <span>AI model</span>
          <select
            value={aiModel}
            onChange={(event) => {
              const next = event.target.value;
              setAiModel(next);
              if (next === "meshy-5") setTextureResolution("2k");
            }}
            className="block w-full rounded-lg border border-input-border bg-input-background px-3 py-2 text-sm"
          >
            <option value="latest">Latest (Meshy 7)</option>
            <option value="meshy-7">Meshy 7</option>
            <option value="meshy-6">Meshy 6</option>
            <option value="meshy-5">Meshy 5</option>
          </select>
        </label>
        <label className="space-y-1 text-xs font-medium">
          <span>{isIcelandic ? "Textúrupplausn" : "Texture resolution"}</span>
          <select
            value={textureResolution}
            onChange={(event) => setTextureResolution(event.target.value)}
            className="block w-full rounded-lg border border-input-border bg-input-background px-3 py-2 text-sm"
          >
            <option value="2k">2K · 10 credits</option>
            <option value="4k" disabled={aiModel === "meshy-5"}>4K · 10 credits</option>
            <option value="8k" disabled={aiModel === "meshy-5"}>8K · 15 credits</option>
          </select>
        </label>
      </div>

      <div className="space-y-2">
        <p className="text-xs font-medium">{isIcelandic ? "Niðurhalssnið" : "Output formats"}</p>
        <div className="flex flex-wrap gap-2">
          {FORMAT_OPTIONS.map((format) => {
            const checked = targetFormats.includes(format);
            return (
              <label
                key={format}
                className={`flex items-center gap-1.5 rounded-md border px-2.5 py-1.5 font-mono text-xs ${
                  checked ? "border-accent bg-accent-soft text-accent-soft-text" : "border-input-border"
                }`}
              >
                <input
                  type="checkbox"
                  checked={checked}
                  disabled={format === "glb"}
                  onChange={() => toggleFormat(format)}
                  className="accent-[var(--accent)]"
                />
                {format}
              </label>
            );
          })}
        </div>
      </div>

      <div className="grid gap-3 text-xs sm:grid-cols-2">
        <label className="flex items-start gap-2 rounded-md border border-surface-border p-3">
          <input
            type="checkbox"
            checked={enableOriginalUv}
            onChange={(event) => setEnableOriginalUv(event.target.checked)}
            className="mt-0.5 accent-[var(--accent)]"
          />
          <span>
            <span className="block font-medium">
              {isIcelandic ? "Endurnota UV-layout" : "Reuse UV layout"}
            </span>
            <span className="mt-1 block leading-relaxed text-muted">
              {isIcelandic
                ? "Mælt með fyrir Meshy-módel: heldur sömu 2D-uppröðun yfirborðsins og minnkar hættu á nýjum saumum."
                : "Recommended for Meshy models: keeps the same 2D surface layout and reduces the chance of new seams."}
            </span>
          </span>
        </label>

        <label className="flex items-start gap-2 rounded-md border border-surface-border p-3">
          <input
            type="checkbox"
            checked={enablePbr}
            onChange={(event) => setEnablePbr(event.target.checked)}
            className="mt-0.5 accent-[var(--accent)]"
          />
          <span>
            <span className="block font-medium">PBR maps</span>
            <span className="mt-1 block leading-relaxed text-muted">
              {isIcelandic
                ? "Býr einnig til metallic, roughness og normal maps fyrir raunverulegri efnisáferð."
                : "Also creates metallic, roughness and normal maps for more realistic materials."}
            </span>
          </span>
        </label>
      </div>

      {aiModel === "meshy-6" ? (
        <label className="flex items-center gap-2 text-xs">
          <input
            type="checkbox"
            checked={removeLighting}
            onChange={(event) => setRemoveLighting(event.target.checked)}
            className="accent-[var(--accent)]"
          />
          {isIcelandic
            ? "Fjarlægja innbakað ljós og skugga úr grunnlit"
            : "Remove baked lighting and shadows from the base colour"}
        </label>
      ) : null}

      {running ? (
        <div className="space-y-1.5">
          <div className="h-2 overflow-hidden rounded-full bg-surface-sunken">
            <div
              className="h-full bg-accent transition-[width]"
              style={{ width: `${Math.max(2, Number(progress || 0))}%` }}
            />
          </div>
          <p className="truncate font-mono text-[10px] text-muted">{statusLine}</p>
        </div>
      ) : null}

      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={runRetexture}
          disabled={running || !prompt.trim()}
          className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-foreground transition hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-40"
        >
          {running
            ? isIcelandic
              ? "Textúra…"
              : "Texturing…"
            : isIcelandic
              ? "Búa til nýjan textúr"
              : "Generate new texture"}
        </button>
      </div>

      {job.retextures?.length ? (
        <div className="border-t border-surface-border pt-3">
          <p className="text-xs font-medium">
            {isIcelandic ? "Textúruútgáfur" : "Texture variants"} · {job.retextures.length}
          </p>
          <ul className="mt-2 space-y-1 font-mono text-[10px] text-muted">
            {[...job.retextures].reverse().map((item) => (
              <li key={item.taskId}>
                #{item.version} · {item.aiModel} · {item.textureResolution} · {item.consumedCredits} credits
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
