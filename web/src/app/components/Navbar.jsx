// src/app/components/Navbar.jsx
// Top navigation bar — logo, pipeline title, theme toggle, and sign-out button.
// Collapses to icon-only on mobile (below md).

"use client";

import { signOut } from "next-auth/react";
import ThemeToggle from "./ThemeToggle";

export default function Navbar({ user }) {
  return (
    <header className="
      sticky top-0 z-50 w-full
      bg-white dark:bg-slate-900
      border-b border-slate-200 dark:border-slate-700
      shadow-sm
    ">
      <div className="mx-auto max-w-screen-2xl px-4 md:px-6 h-14 flex items-center justify-between gap-4">

        {/* Logo + Title */}
        <div className="flex items-center gap-3 min-w-0">
          <div className="
            w-8 h-8 rounded-lg flex items-center justify-center shrink-0
            bg-indigo-600 dark:bg-indigo-500 text-white font-bold text-sm
          ">
            K9
          </div>
          <span className="hidden md:block font-semibold text-slate-800 dark:text-slate-100 truncate">
            Crystal Pipeline
          </span>
        </div>

        {/* Right side */}
        <div className="flex items-center gap-3">
          <ThemeToggle />

          {user && (
            <div className="flex items-center gap-3">
              <span className="hidden md:block text-sm text-slate-500 dark:text-slate-400">
                {user.name}
              </span>
              <button
                onClick={() => signOut({ callbackUrl: "/login" })}
                className="
                  px-3 py-1.5 rounded-lg text-sm font-medium
                  bg-rose-600 hover:bg-rose-700
                  text-white transition-colors duration-200
                "
              >
                Sign out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
