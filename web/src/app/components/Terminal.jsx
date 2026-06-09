// src/app/components/Terminal.jsx
// Live SSE terminal output viewer.
// cmd (cyan) = command run, stdout (white), stderr (amber), error (red), done (green).

"use client";

import { useEffect, useRef } from "react";

export default function Terminal({ lines = [], running = false }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [lines]);

  return (
    <div className="rounded-xl border border-slate-700 dark:border-slate-600 bg-slate-950 overflow-hidden flex flex-col font-mono text-xs">
      {/* Terminal header bar */}
      <div className="flex items-center gap-2 px-4 py-2.5 bg-slate-900 border-b border-slate-700">
        <span className="w-3 h-3 rounded-full bg-rose-500" />
        <span className="w-3 h-3 rounded-full bg-amber-400" />
        <span className="w-3 h-3 rounded-full bg-emerald-500" />
        <span className="ml-3 text-slate-400 text-[11px]">Pipeline Output</span>
        {running && (
          <span className="ml-auto flex items-center gap-1.5 text-emerald-400">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            Running
          </span>
        )}
      </div>

      {/* Output lines */}
      <div className="p-4 min-h-[200px] max-h-[400px] overflow-y-auto">
        {lines.length === 0 ? (
          <p className="text-slate-600">Waiting for output...</p>
        ) : (
          lines.map((item, i) => {
            if (item.type === "cmd") {
              return (
                <div key={i} className="text-cyan-400 mb-2 break-all">
                  <span className="text-slate-500">$ </span>{item.line}
                </div>
              );
            }
            if (item.type === "done") {
              return (
                <div key={i} className="text-emerald-400">
                  <span>✓ Process exited with code {item.code}</span>
                </div>
              );
            }
            return (
              <div
                key={i}
                className={item.type === "stderr" ? "text-amber-400" : item.type === "error" ? "text-rose-400" : "text-slate-200"}
              >
                <span>{">"} {item.line || item.message}</span>
              </div>
            );
          })
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
