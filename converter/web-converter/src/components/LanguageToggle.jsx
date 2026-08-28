"use client";

/*
 * File: src/components/LanguageToggle.jsx
 * Purpose: Compact persistent Icelandic/English language picker.
 */

import { useLanguage } from "@/components/LanguageProvider";

export default function LanguageToggle() {
  const { locale, setLocale, t } = useLanguage();
  return (
    <div
      role="group"
      aria-label={t("Language")}
      className="inline-flex shrink-0 items-center gap-0.5 rounded-lg border border-surface-border bg-surface p-0.5"
    >
      {[
        { id: "is", label: "ÍS", title: "Icelandic" },
        { id: "en", label: "EN", title: "English" },
      ].map((item) => (
        <button
          key={item.id}
          type="button"
          onClick={() => setLocale(item.id)}
          aria-pressed={locale === item.id}
          title={t(item.title)}
          className={`rounded-md px-2.5 py-1 text-xs transition ${
            locale === item.id
              ? "bg-accent text-accent-foreground"
              : "text-muted hover:bg-surface-hover hover:text-foreground"
          }`}
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}
