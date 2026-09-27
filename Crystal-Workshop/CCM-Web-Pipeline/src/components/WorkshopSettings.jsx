/** Purpose: Keep account, language and appearance controls in one compact header disclosure. */
"use client";

import { useEffect, useRef } from "react";
import CreateUser from "@/components/CreateUser";
import LanguageToggle from "@/components/LanguageToggle";
import ThemeToggle from "@/components/ThemeToggle";
import { useLanguage } from "@/components/LanguageProvider";

export default function WorkshopSettings() {
  const disclosure = useRef(null);
  const { locale } = useLanguage();
  const label = locale === "en" ? "Settings" : "Stillingar";

  useEffect(() => {
    const closeOutside = (event) => {
      if (!disclosure.current?.contains(event.target)) disclosure.current?.removeAttribute("open");
    };
    const closeOnEscape = (event) => {
      // Leave the account dialog's native Escape handling intact.
      if (event.key !== "Escape" || event.target.closest("dialog")) return;
      if (disclosure.current?.open) {
        disclosure.current.removeAttribute("open");
        disclosure.current.querySelector("summary")?.focus();
      }
    };
    document.addEventListener("pointerdown", closeOutside);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOutside);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, []);

  return (
    <details ref={disclosure} className="relative justify-self-end">
      <summary aria-label={label} title={label} className="flex h-11 w-11 cursor-pointer list-none items-center justify-center rounded-xl border border-surface-border bg-surface text-xl hover:bg-surface-hover focus-visible:outline-2 focus-visible:outline-accent [&::-webkit-details-marker]:hidden">
        <span aria-hidden="true">⚙️</span>
      </summary>
      <div className="absolute right-0 top-full mt-2 flex w-max max-w-[calc(100vw-2rem)] flex-col items-start gap-4 rounded-xl border border-surface-border bg-background p-4 shadow-xl">
        <LanguageToggle />
        <ThemeToggle />
        <CreateUser en={locale === "en"} />
      </div>
    </details>
  );
}
