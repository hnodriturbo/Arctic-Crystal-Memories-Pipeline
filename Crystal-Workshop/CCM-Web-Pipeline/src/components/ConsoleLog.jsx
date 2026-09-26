"use client";

/*
 * ═══════════════════════════════════════════════════════════════
 * Console Log
 * ═══════════════════════════════════════════════════════════════
 * Path: src/components/ConsoleLog.jsx
 * Purpose: Show live script output, pinned to the newest line.
 *
 * The console keeps a dark ground in both themes on purpose - terminal
 * output is easier to scan against one, and it marks the panel as machine
 * output rather than part of the form.
 */

import { useEffect, useRef } from "react";
import { useLanguage } from "@/components/LanguageProvider";

const LINE_COLOURS = {
  cmd: "text-console-accent",
  stdout: "text-console-foreground",
  stderr: "text-console-warn",
  error: "text-console-error",
  done: "text-console-done",
};

export default function ConsoleLog({ lines, running }) {
  const endRef = useRef(null);
  const { t } = useLanguage();

  // Follow the tail while a script is talking, so progress stays visible.
  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [lines]);

  return (
    <div className="overflow-hidden rounded-lg border border-surface-border bg-console-background">
      <div className="flex items-center gap-2 border-b border-white/10 px-4 py-2">
        <span
          className={`inline-block h-2 w-2 rounded-full ${
            running ? "animate-pulse bg-console-done" : "bg-console-muted"
          }`}
        />
        <span className="font-mono text-xs text-console-muted">
          {running ? t("running") : t("idle")}
        </span>
        {lines.length ? (
          <span className="ml-auto font-mono text-xs text-console-muted">
            {lines.length} {t("lines")}
          </span>
        ) : null}
      </div>

      <div className="max-h-96 overflow-y-auto px-4 py-3">
        {lines.length === 0 ? (
          <p className="font-mono text-xs text-console-muted">
            {t("Output appears here once a conversion starts.")}
          </p>
        ) : (
          lines.map((entry, index) => (
            <pre
              key={index}
              className={`whitespace-pre-wrap break-words font-mono text-xs leading-relaxed ${
                LINE_COLOURS[entry.type] || "text-console-foreground"
              }`}
            >
              {entry.text}
            </pre>
          ))
        )}
        <div ref={endRef} />
      </div>
    </div>
  );
}
