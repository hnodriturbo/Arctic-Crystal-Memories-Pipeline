// src/app/components/Sidebar.jsx
// Left sidebar — folder navigation (input / upscaled / enhanced / bg_removed).
// Hidden below md; shown as a top filter bar on small screens.

"use client";

import { useApp } from "@/app/context/AppContext";

const FOLDERS = [
  { key: "all",       label: "All Images",        icon: "⊞" },
  { key: "input",     label: "Input",             icon: "📥" },
  { key: "upscaled",  label: "Upscaled",          icon: "⬆" },
  { key: "enhanced",  label: "Enhanced",          icon: "✦" },
  { key: "bg_removed",label: "BG Removed",        icon: "◻" },
];

export default function Sidebar({ activeFolder, onFolderChange }) {
  return (
    <>
      {/* Desktop sidebar */}
      <aside className="hidden md:flex flex-col w-52 shrink-0">
        <nav className="
          sticky top-16 rounded-xl overflow-hidden
          border border-slate-200 dark:border-slate-700
          bg-white dark:bg-slate-900
        ">
          <div className="px-3 py-2 text-xs font-semibold tracking-wider uppercase
            text-slate-400 dark:text-slate-500 border-b border-slate-100 dark:border-slate-800">
            Folders
          </div>
          {FOLDERS.map(({ key, label, icon }) => (
            <button
              key={key}
              onClick={() => onFolderChange(key)}
              className={`
                w-full flex items-center gap-2.5 px-4 py-2.5 text-sm text-left
                transition-colors duration-150
                ${activeFolder === key
                  ? "bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 font-medium"
                  : "text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800"}
              `}
            >
              <span className="text-base leading-none">{icon}</span>
              <span>{label}</span>
            </button>
          ))}
        </nav>
      </aside>

      {/* Mobile horizontal filter pills */}
      <div className="md:hidden flex gap-2 overflow-x-auto pb-1 px-0.5">
        {FOLDERS.map(({ key, label, icon }) => (
          <button
            key={key}
            onClick={() => onFolderChange(key)}
            className={`
              shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm
              border transition-colors duration-150
              ${activeFolder === key
                ? "bg-indigo-600 border-indigo-600 text-white"
                : "border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"}
            `}
          >
            <span>{icon}</span>
            <span>{label}</span>
          </button>
        ))}
      </div>
    </>
  );
}
