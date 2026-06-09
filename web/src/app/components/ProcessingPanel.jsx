// src/app/components/ProcessingPanel.jsx
// Operation selector: Upscale / Enhance / Remove BG tabs with per-op options.

"use client";

import { useState } from "react";

const UPSCALE_ENGINES = [
  { value: "realesrgan",      label: "RealESRGAN (recommended)" },
  { value: "realesrgan_face", label: "RealESRGAN Face" },
  { value: "lanczos",         label: "Lanczos (no AI, fast)" },
];

const ENHANCE_ENGINES = [
  { value: "gfpgan",     label: "GFPGAN — face restoration" },
  { value: "codeformer", label: "CodeFormer — sharper faces" },
  { value: "pillow",     label: "Pillow — brightness/contrast" },
];

const REMBG_MODELS = [
  { value: "isnet-general-use", label: "isnet-general (recommended)" },
  { value: "birefnet-portrait", label: "BiRefNet Portrait" },
  { value: "birefnet-general", label: "BiRefNet General" },
  { value: "u2net_human_seg",   label: "U²Net Human" },
  { value: "u2net",             label: "U²Net General" },
];

const REMBG_ENGINES = [
  { value: "rembg",    label: "rembg (GPU-accelerated)" },
  { value: "carvekit", label: "CarveKit (best edges, slow)" },
];

const inputCls = "w-full rounded-lg px-3 py-2 text-sm bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-600 text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500";

function Field({ label, children }) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-xs font-medium text-slate-500 dark:text-slate-400">{label}</label>
      {children}
    </div>
  );
}

function Select({ value, onChange, options }) {
  return (
    <select value={value} onChange={(e) => onChange(e.target.value)} className={inputCls}>
      {options.map((o) => (
        <option key={o.value} value={o.value}>{o.label}</option>
      ))}
    </select>
  );
}

export default function ProcessingPanel({ file, folder, onRun, running }) {
  const [operation, setOperation] = useState("upscale");

  const [upscaleEngine, setUpscaleEngine] = useState("realesrgan");
  const [upscaleTarget, setUpscaleTarget] = useState(1800);

  const [enhanceEngine, setEnhanceEngine] = useState("gfpgan");
  const [fidelity, setFidelity] = useState(0.7);
  const [brightness, setBrightness] = useState(1.0);
  const [contrast, setContrast] = useState(1.0);
  const [sharpness, setSharpness] = useState(1.0);
  const [color, setColor] = useState(1.0);

  const [bgEngine, setBgEngine] = useState("rembg");
  const [bgModel, setBgModel] = useState("isnet-general-use");

  function handleRun() {
    const base = { operation, file };
    if (operation === "upscale") {
      onRun({ ...base, engine: upscaleEngine, target: upscaleTarget });
    } else if (operation === "enhance") {
      onRun({ ...base, engine: enhanceEngine, fidelity, brightness, contrast, sharpness, color });
    } else if (operation === "remove_bg") {
      onRun({ ...base, engine: bgEngine, model: bgModel });
    }
  }

  return (
    <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 overflow-hidden">
      {/* Operation tabs */}
      <div className="flex border-b border-slate-200 dark:border-slate-700">
        {[
          { key: "upscale",   label: "⬆ Upscale" },
          { key: "enhance",   label: "✦ Enhance" },
          { key: "remove_bg", label: "◻ Remove BG" },
        ].map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setOperation(key)}
            className={`flex-1 py-3 text-sm font-medium transition-colors duration-150 ${operation === key ? "bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 border-b-2 border-indigo-500" : "text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800"}`}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="p-5 flex flex-col gap-4">
        {operation === "upscale" && (
          <>
            <Field label="Engine">
              <Select value={upscaleEngine} onChange={setUpscaleEngine} options={UPSCALE_ENGINES} />
            </Field>
            <Field label="Target long edge (px)">
              <input
                type="number"
                value={upscaleTarget}
                onChange={(e) => setUpscaleTarget(Number(e.target.value))}
                min={800} max={8000} step={100}
                className={inputCls}
              />
            </Field>
          </>
        )}

        {operation === "enhance" && (
          <>
            <Field label="Engine">
              <Select value={enhanceEngine} onChange={setEnhanceEngine} options={ENHANCE_ENGINES} />
            </Field>
            {enhanceEngine === "codeformer" && (
              <Field label={`Fidelity: ${fidelity.toFixed(1)}`}>
                <input type="range" min={0} max={1} step={0.1} value={fidelity}
                  onChange={(e) => setFidelity(parseFloat(e.target.value))}
                  className="w-full accent-indigo-600" />
                <div className="flex justify-between text-[10px] text-slate-400 mt-0.5">
                  <span>max AI</span><span>max faithful</span>
                </div>
              </Field>
            )}
            {enhanceEngine === "pillow" && (
              <div className="grid grid-cols-2 gap-3">
                {[
                  ["Brightness", brightness, setBrightness],
                  ["Contrast", contrast, setContrast],
                  ["Sharpness", sharpness, setSharpness],
                  ["Color", color, setColor],
                ].map(([lbl, val, setter]) => (
                  <Field key={lbl} label={`${lbl}: ${Number(val).toFixed(1)}`}>
                    <input type="range" min={0.5} max={2} step={0.1} value={val}
                      onChange={(e) => setter(parseFloat(e.target.value))}
                      className="w-full accent-indigo-600" />
                  </Field>
                ))}
              </div>
            )}
          </>
        )}

        {operation === "remove_bg" && (
          <>
            <Field label="Engine">
              <Select value={bgEngine} onChange={setBgEngine} options={REMBG_ENGINES} />
            </Field>
            {bgEngine === "rembg" && (
              <Field label="Model">
                <Select value={bgModel} onChange={setBgModel} options={REMBG_MODELS} />
              </Field>
            )}
          </>
        )}

        <button
          onClick={handleRun}
          disabled={running}
          className="w-full py-3 rounded-xl font-semibold text-white bg-indigo-600 hover:bg-indigo-700 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed shadow-md shadow-indigo-600/20 transition-all duration-150 mt-2"
        >
          {running ? "Running…" : `Run ${operation.replace("_", " ")}`}
        </button>
      </div>
    </div>
  );
}
