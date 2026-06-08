// src/app/components/ClientShell.jsx
// Client-side shell that wraps the entire app with AppProvider, Navbar,
// Sidebar, ImageGrid, and ImageModal. Master container with mx-auto boundaries.

"use client";

import { useState, useEffect } from "react";
import { AppProvider, useApp } from "@/app/context/AppContext";
import Navbar from "./Navbar";
import Sidebar from "./Sidebar";
import ImageGrid from "./ImageGrid";
import ImageModal from "./ImageModal";

function AppShellInner({ user }) {
  const { theme } = useApp();
  const [folder, setFolder] = useState("all");

  // Apply dark/light class to <html>
  useEffect(() => {
    const html = document.documentElement;
    if (theme === "dark") {
      html.classList.add("dark");
    } else {
      html.classList.remove("dark");
    }
  }, [theme]);

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 transition-colors duration-200">
      <Navbar user={user} />

      {/* Master container */}
      <main className="mx-auto max-w-screen-2xl px-4 md:px-6 py-6">
        {/* Page header */}
        <div className="mb-6">
          <h2 className="text-xl font-semibold text-slate-800 dark:text-slate-100">
            Image Pipeline
          </h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
            Select an image to upscale, enhance, or remove its background.
            Single-click to select, double-click to preview.
          </p>
        </div>

        {/* Two-column layout: sidebar + main content */}
        <div className="flex flex-col md:flex-row gap-6">
          <Sidebar activeFolder={folder} onFolderChange={setFolder} />

          <div className="flex-1 min-w-0">
            <ImageGrid folder={folder} />
          </div>
        </div>
      </main>

      <ImageModal />
    </div>
  );
}

export default function ClientShell({ user }) {
  return (
    <AppProvider>
      <AppShellInner user={user} />
    </AppProvider>
  );
}
