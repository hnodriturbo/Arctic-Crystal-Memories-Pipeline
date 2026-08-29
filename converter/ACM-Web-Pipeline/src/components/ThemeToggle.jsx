"use client";

/*
 * ═══════════════════════════════════════════════════════════════
 * Theme Toggle
 * ═══════════════════════════════════════════════════════════════
 * Path: src/components/ThemeToggle.jsx
 * Purpose: Three-state theme picker - follow the system, or force
 *          light or dark - persisted per browser.
 *
 * The DOM and localStorage writes live in an effect rather than the click
 * handler: the document is an external system, which is exactly what
 * effects are for, and the React Compiler enforces it.
 */

import { useEffect, useState } from "react";
import { useLanguage } from "@/components/LanguageProvider";

export const THEME_STORAGE_KEY = "converter-theme";

const CHOICES = [
  { id: "system", label: "Auto", glyph: "◐" },
  { id: "light", label: "Light", glyph: "☀" },
  { id: "dark", label: "Dark", glyph: "☾" },
];

/** Read what the pre-paint script already applied, so the button starts in sync. */
function readInitialChoice() {
  if (typeof document === "undefined") return "system";
  try {
    const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
    if (stored === "light" || stored === "dark") return stored;
  } catch {
    // Private windows and blocked site data both land here; Auto is a fine answer.
  }
  return "system";
}

export default function ThemeToggle() {
  const { t } = useLanguage();
  const [choice, setChoice] = useState(readInitialChoice);

  useEffect(() => {
    const root = document.documentElement;
    if (choice === "system") {
      delete root.dataset.theme;
    } else {
      root.dataset.theme = choice;
    }

    try {
      if (choice === "system") window.localStorage.removeItem(THEME_STORAGE_KEY);
      else window.localStorage.setItem(THEME_STORAGE_KEY, choice);
    } catch {
      // Not being able to remember the choice is not worth surfacing.
    }
  }, [choice]);

  return (
    <div
      className="inline-flex shrink-0 items-center gap-0.5 rounded-lg border border-surface-border bg-surface p-0.5"
      role="group"
      aria-label={t("Colour theme")}
    >
      {CHOICES.map((item) => {
        const active = item.id === choice;
        return (
          <button
            key={item.id}
            type="button"
            onClick={() => setChoice(item.id)}
            aria-pressed={active}
            title={t(item.label)}
            className={`rounded-md px-2.5 py-1 text-xs transition ${
              active
                ? "bg-accent text-accent-foreground"
                : "text-muted hover:bg-surface-hover hover:text-foreground"
            }`}
          >
            <span aria-hidden="true">{item.glyph}</span>
            <span className="ml-1.5 hidden sm:inline">{t(item.label)}</span>
          </button>
        );
      })}
    </div>
  );
}
