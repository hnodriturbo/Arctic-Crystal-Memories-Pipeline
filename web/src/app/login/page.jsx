// src/app/login/page.jsx
// Login page — username + password form using NextAuth v5 credentials provider.
// Redirects to / on success; shows inline error on failure.

"use client";

import { useState } from "react";
import { signIn } from "next-auth/react";
import { useRouter, useSearchParams } from "next/navigation";
import { Inter } from "next/font/google";

const inter = Inter({ subsets: ["latin"], display: "swap" });

export default function LoginPage() {
  const router = useRouter();
  const params = useSearchParams();
  const callbackUrl = params.get("callbackUrl") || "/";

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);

    const result = await signIn("credentials", {
      username,
      password,
      redirect: false,
    });

    setLoading(false);

    if (result?.error) {
      setError("Invalid username or password.");
    } else {
      router.push(callbackUrl);
      router.refresh();
    }
  }

  return (
    <div className={`${inter.className} min-h-screen flex items-center justify-center
      bg-gradient-to-br from-slate-950 via-slate-900 to-indigo-950 p-4`}>
      <div className="w-full max-w-sm">

        {/* Logo card */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl
            bg-indigo-600 text-white font-bold text-2xl shadow-lg shadow-indigo-600/40 mb-4">
            K9
          </div>
          <h1 className="text-2xl font-bold text-white">Crystal Pipeline</h1>
          <p className="text-slate-400 text-sm mt-1">Sign in to continue</p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit}
          className="bg-white dark:bg-slate-900 rounded-2xl p-8 shadow-2xl
            border border-slate-200 dark:border-slate-700 flex flex-col gap-5">

          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-slate-700 dark:text-slate-300">
              Username
            </label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              autoFocus
              placeholder="hnodri"
              className="
                rounded-xl px-4 py-3 text-sm
                bg-slate-50 dark:bg-slate-800
                border border-slate-300 dark:border-slate-600
                text-slate-800 dark:text-slate-200
                placeholder:text-slate-400 dark:placeholder:text-slate-600
                focus:outline-none focus:ring-2 focus:ring-indigo-500
              "
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-slate-700 dark:text-slate-300">
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              placeholder="••••••••"
              className="
                rounded-xl px-4 py-3 text-sm
                bg-slate-50 dark:bg-slate-800
                border border-slate-300 dark:border-slate-600
                text-slate-800 dark:text-slate-200
                placeholder:text-slate-400
                focus:outline-none focus:ring-2 focus:ring-indigo-500
              "
            />
          </div>

          {error && (
            <div className="px-4 py-3 rounded-xl bg-rose-50 dark:bg-rose-950
              border border-rose-200 dark:border-rose-800
              text-rose-700 dark:text-rose-300 text-sm">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="
              w-full py-3 rounded-xl font-semibold text-white
              bg-indigo-600 hover:bg-indigo-700 active:scale-95
              disabled:opacity-60 disabled:cursor-not-allowed
              shadow-lg shadow-indigo-600/30
              transition-all duration-150
            "
          >
            {loading ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
