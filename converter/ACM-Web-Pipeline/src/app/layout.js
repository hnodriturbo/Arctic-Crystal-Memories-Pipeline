/*
 * ═══════════════════════════════════════════════════════════════
 * Root Layout
 * ═══════════════════════════════════════════════════════════════
 * Path: src/app/layout.js
 * Purpose: Fonts, metadata, and applying the saved theme before first paint.
 */

import { Geist, Geist_Mono } from "next/font/google";
import { LanguageProvider } from "@/components/LanguageProvider";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata = {
  title: "Crystal Converter",
  description: "Convert 3D models into printable point clouds for the SSLE crystal engraver.",
};

// Runs before the first paint so a forced theme never flashes the other one.
// No stored value means "follow the system", which the CSS already handles.
const THEME_BOOTSTRAP = [
  "(function(){try{",
  "var t=localStorage.getItem('converter-theme');",
  "if(t==='dark'||t==='light'){document.documentElement.dataset.theme=t;}",
  "}catch(e){}})();",
].join("");

const LANGUAGE_BOOTSTRAP = [
  "(function(){try{",
  "var l=localStorage.getItem('acm-pipeline-language');",
  "document.documentElement.lang=l==='en'?'en':'is';",
  "}catch(e){document.documentElement.lang='is';}})();",
].join("");

export default function RootLayout({ children }) {
  return (
    <html
      lang="is"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_BOOTSTRAP }} />
        <script dangerouslySetInnerHTML={{ __html: LANGUAGE_BOOTSTRAP }} />
      </head>
      <body className="min-h-full flex flex-col bg-background text-foreground">
        <LanguageProvider>{children}</LanguageProvider>
      </body>
    </html>
  );
}
