"use client";

/*
 * File: src/components/LoginHeader.jsx
 * Purpose: Bilingual heading and language control for the public login page.
 */

import LanguageToggle from "@/components/LanguageToggle";
import { useLanguage } from "@/components/LanguageProvider";

export default function LoginHeader() {
  const { locale } = useLanguage();
  return (
    <header className="space-y-3 text-center">
      <div className="flex justify-center">
        <LanguageToggle />
      </div>
      <div>
        <h1 className="text-2xl font-semibold">ACM Pipeline</h1>
        <p className="text-sm text-muted">
          {locale === "is"
            ? "Ljósmynd í þrívítt model og grafinn kristal."
            : "Photograph to 3D model to engraved crystal."}
        </p>
      </div>
    </header>
  );
}
