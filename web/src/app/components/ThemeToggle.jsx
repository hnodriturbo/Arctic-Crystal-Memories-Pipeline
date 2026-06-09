// src/app/components/ThemeToggle.jsx
// Button that switches between light and dark mode via AppContext.

"use client";

import { useApp } from "@/app/context/AppContext";

export default function ThemeToggle() {
  const { theme, toggleTheme } = useApp();

  return (
    <button
      onClick={toggleTheme}
      aria-label="Toggle theme"
      className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium border border-slate-600 dark:border-slate-500 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors duration-200"
    >
      {theme === "dark" ? (
        <>
          <span>☀</span>
          <span>Light</span>
        </>
      ) : (
        <>
          <span>🌙</span>
          <span>Dark</span>
        </>
      )}
    </button>
  );
}
