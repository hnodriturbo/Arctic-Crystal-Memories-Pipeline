// src/app/process/page.jsx
// Processing page — preview selected image, choose operation, run pipeline,
// view live terminal output, approve or deny the result.

"use client";

import { useState, useCallback, useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { AppProvider, useApp } from "@/app/context/AppContext";
import Navbar from "@/app/components/Navbar";
import ProcessingPanel from "@/app/components/ProcessingPanel";
import Terminal from "@/app/components/Terminal";
import ImageModal from "@/app/components/ImageModal";

const OUTPUT_FOLDER_MAP = {
  upscale:    "upscaled",
  enhance:    "enhanced",
  remove_bg:  "bg_removed",
};

const OUTPUT_SUFFIX_MAP = {
  upscale:   "-upscaled",
  enhance:   "-enhanced",
  remove_bg: "-bg-removed",
};

function imgSrc(folder, filename) {
  return `/api/image/${folder}/${encodeURIComponent(filename)}`;
}

function ProcessPageInner() {
  const params = useSearchParams();
  const router = useRouter();
  const { theme, openModal } = useApp();

  const file = params.get("file") || "";
  const folder = params.get("folder") || "input";

  const [running, setRunning] = useState(false);
  const [lines, setLines] = useState([]);
  const [done, setDone] = useState(false);
  const [exitCode, setExitCode] = useState(null);
  const [lastOperation, setLastOperation] = useState(null);
  const [outputFile, setOutputFile] = useState(null); // filename in output folder
  const [outputTs, setOutputTs] = useState(0);        // cache-bust timestamp, set once on completion
  const [approvalVisible, setApprovalVisible] = useState(false);
  const [approved, setApproved] = useState(false);
  const [denied, setDenied] = useState(false);

  // Apply theme
  useEffect(() => {
    const html = document.documentElement;
    theme === "dark" ? html.classList.add("dark") : html.classList.remove("dark");
  }, [theme]);

  const handleRun = useCallback(async (config) => {
    setRunning(true);
    setLines([]);
    setDone(false);
    setExitCode(null);
    setOutputFile(null);
    setApprovalVisible(false);
    setApproved(false);
    setDenied(false);
    setLastOperation(config.operation);

    const resp = await fetch("/api/process", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(config),
    });

    if (!resp.ok || !resp.body) {
      setLines([{ type: "error", message: "Failed to start process" }]);
      setRunning(false);
      return;
    }

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buf = "";

    while (true) {
      const { value, done: streamDone } = await reader.read();
      if (streamDone) break;
      buf += decoder.decode(value, { stream: true });
      const parts = buf.split("\n\n");
      buf = parts.pop();
      for (const part of parts) {
        if (!part.startsWith("data: ")) continue;
        try {
          const evt = JSON.parse(part.slice(6));
          setLines((prev) => [...prev, evt]);
          if (evt.type === "done") {
            setExitCode(evt.code);
            setDone(true);
            setRunning(false);
            if (evt.code === 0) {
              const stem = file.replace(/\.[^.]+$/, "");
              const suffix = OUTPUT_SUFFIX_MAP[config.operation] || "";
              setOutputFile(`${stem}${suffix}.png`);
              setOutputTs(Date.now());
              setApprovalVisible(true);
            }
          }
        } catch {
          /* ignore parse errors */
        }
      }
    }
    setRunning(false);
  }, [file]);

  async function handleDeny() {
    if (!outputFile || !lastOperation) return;
    const outFolder = OUTPUT_FOLDER_MAP[lastOperation];
    await fetch("/api/run", {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filePath: `output/${outFolder}/${outputFile}` }),
    });
    setApproved(false);
    setDenied(true);
    setApprovalVisible(false);
    setOutputFile(null);
  }

  function handleApprove() {
    setApproved(true);
    setApprovalVisible(false);
  }

  const inputSrc = imgSrc(folder, file);
  const outFolder = lastOperation ? OUTPUT_FOLDER_MAP[lastOperation] : null;
  const outputSrc = outputFile && outFolder ? imgSrc(outFolder, outputFile) : null;

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 transition-colors duration-200">
      <Navbar />

      <main className="mx-auto max-w-screen-xl px-4 md:px-6 py-6 flex flex-col gap-6">

        {/* Back link + title */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => router.push("/")}
            className="text-sm text-slate-500 dark:text-slate-400 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors"
          >
            ← Back
          </button>
          <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100 truncate">
            {file}
          </h2>
        </div>

        {/* Top: input preview */}
        <div className="rounded-2xl border border-slate-200 dark:border-slate-700
          bg-white dark:bg-slate-900 overflow-hidden">
          <div className="px-4 py-3 border-b border-slate-200 dark:border-slate-700 flex items-center gap-2">
            <span className="text-xs font-semibold px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800
              text-slate-600 dark:text-slate-300">
              {folder}
            </span>
            <span className="text-sm text-slate-600 dark:text-slate-300 truncate">{file}</span>
          </div>
          <div className="p-4 bg-[#f0f0f0] dark:bg-slate-950 flex justify-center">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={inputSrc}
              alt={file}
              onClick={() => openModal({ name: file, folder, relativePath: `${folder}/${file}` })}
              className="max-h-64 md:max-h-96 max-w-full object-contain rounded-lg cursor-pointer
                hover:scale-[1.02] transition-transform duration-200"
            />
          </div>
        </div>

        {/* Two-column: controls (left) + terminal (right) */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <ProcessingPanel file={file} folder={folder} onRun={handleRun} running={running} />
          <Terminal lines={lines} running={running} />
        </div>

        {/* Output preview + approval — only after successful run */}
        {outputSrc && (
          <div className="rounded-2xl border border-slate-200 dark:border-slate-700
            bg-white dark:bg-slate-900 overflow-hidden">
            <div className="px-4 py-3 border-b border-slate-200 dark:border-slate-700 flex items-center gap-2">
              <span className="text-xs font-semibold px-2 py-0.5 rounded
                bg-emerald-100 dark:bg-emerald-900 text-emerald-700 dark:text-emerald-300">
                Output
              </span>
              <span className="text-sm text-slate-600 dark:text-slate-300 truncate">{outputFile}</span>
            </div>
            <div className="p-4 bg-[#f0f0f0] dark:bg-slate-950 flex justify-center">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={`${outputSrc}?t=${outputTs}`}
                alt={outputFile}
                onClick={() => openModal({ name: outputFile, folder: outFolder, relativePath: `${outFolder}/${outputFile}` })}
                className="max-h-64 md:max-h-96 max-w-full object-contain rounded-lg cursor-pointer
                  hover:scale-[1.02] transition-transform duration-200"
              />
            </div>

            {/* Approval row */}
            {approvalVisible && (
              <div className="px-4 py-4 border-t border-slate-200 dark:border-slate-700
                bg-slate-50 dark:bg-slate-800/50 flex items-center justify-center gap-4">
                <p className="text-sm text-slate-600 dark:text-slate-300 mr-2">
                  Accept this result?
                </p>
                <button
                  onClick={handleApprove}
                  className="px-5 py-2.5 rounded-xl font-semibold text-white
                    bg-emerald-600 hover:bg-emerald-700 active:scale-95
                    shadow-md shadow-emerald-600/20 transition-all duration-150"
                >
                  ✓ Approve
                </button>
                <button
                  onClick={handleDeny}
                  className="px-5 py-2.5 rounded-xl font-semibold
                    bg-rose-100 dark:bg-rose-950 hover:bg-rose-200 dark:hover:bg-rose-900
                    text-rose-700 dark:text-rose-300 border border-rose-300 dark:border-rose-700
                    active:scale-95 transition-all duration-150"
                >
                  ✕ Deny & Delete
                </button>
              </div>
            )}

            {approved && (
              <div className="px-4 py-3 bg-emerald-50 dark:bg-emerald-950/30
                border-t border-emerald-200 dark:border-emerald-800
                text-emerald-700 dark:text-emerald-300 text-sm text-center">
                ✓ Result approved — saved to pipeline output folder.
              </div>
            )}
            {denied && (
              <div className="px-4 py-3 bg-rose-50 dark:bg-rose-950/30
                border-t border-rose-200 dark:border-rose-800
                text-rose-700 dark:text-rose-300 text-sm text-center">
                Output file deleted. Run again with different settings.
              </div>
            )}
          </div>
        )}
      </main>

      <ImageModal />
    </div>
  );
}

export default function ProcessPage() {
  return (
    <AppProvider>
      <ProcessPageInner />
    </AppProvider>
  );
}
