// src/app/layout.js
// Root layout — sets Inter font, metadata, and base HTML structure.
// Dark/light mode class is toggled by ClientShell via AppContext.

import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
  display: "swap",
});

export const metadata = {
  title: "K9 Crystal Pipeline",
  description: "Image preparation pipeline — upscale, enhance, background removal",
};

export default function RootLayout({ children }) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${jetbrainsMono.variable} dark`}
    >
      <body className="min-h-full antialiased">{children}</body>
    </html>
  );
}
