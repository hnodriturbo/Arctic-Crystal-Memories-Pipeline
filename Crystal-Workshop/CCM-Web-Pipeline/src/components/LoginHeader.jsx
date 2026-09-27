"use client";

/*
 * File: src/components/LoginHeader.jsx
 * Purpose: Bilingual heading and language control for the public login page.
 */

import LanguageToggle from "@/components/LanguageToggle";
import Image from "next/image";
import { useLanguage } from "@/components/LanguageProvider";

export default function LoginHeader() {
  const { locale } = useLanguage();
  return (
    <header className="space-y-3 text-center">
      <Image src="/logo/ccm-crystal-workshop-v1.png" alt="CCM Crystal Workshop" width={2172} height={724} preload unoptimized className="h-auto w-full" />
      <div className="flex justify-center">
        <LanguageToggle />
      </div>
      <div>
        <h1 className="text-2xl font-semibold">Crystal Workshop</h1>
        <p className="text-sm text-muted">
          {locale === "is"
            ? "Ljósmynd í þrívítt model og grafinn kristal."
            : "Photograph to 3D model to engraved crystal."}
        </p>
      </div>
    </header>
  );
}
