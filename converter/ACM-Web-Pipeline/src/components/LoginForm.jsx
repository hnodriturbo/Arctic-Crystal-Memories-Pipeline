"use client";

/*
 * ═══════════════════════════════════════════════════════════════
 * Login Form
 * ═══════════════════════════════════════════════════════════════
 * Path: src/components/LoginForm.jsx
 * Purpose: Sign in with the same email and password as acm_bookkeeping.
 */

import { useRouter } from "next/navigation";
import { useState } from "react";
import { useLanguage } from "@/components/LanguageProvider";

const CONTROL =
  "mt-1 w-full rounded-md border border-input-border bg-input-background px-3 py-2 " +
  "text-sm text-foreground outline-none transition focus:border-accent";

export default function LoginForm({ initialError = null }) {
  const { locale } = useLanguage();
  const router = useRouter();
  const [error, setError] = useState(initialError);
  const [busy, setBusy] = useState(false);

  /*
   * Posted straight to Auth.js's credentials endpoint with redirect off, so a
   * wrong password re-renders this form with a message instead of bouncing
   * through /api/auth/error and losing what was typed.
   */
  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError(null);

    const form = new FormData(event.currentTarget);

    try {
      const csrfResponse = await fetch("/api/auth/csrf");
      const { csrfToken } = await csrfResponse.json();

      const response = await fetch("/api/auth/callback/credentials", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({
          csrfToken,
          email: form.get("email"),
          password: form.get("password"),
          redirect: "false",
        }),
      });

      // Auth.js answers a failed credentials check by redirecting to its error
      // page; a success lands anywhere else.
      if (!response.ok || response.url.includes("error")) {
        setError("Wrong email or password.");
        return;
      }

      router.replace("/");
      router.refresh();
    } catch {
      setError("Could not reach the server.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form
      onSubmit={submit}
      className="space-y-4 rounded-xl border border-surface-border bg-surface p-6"
    >
      {error ? (
        <p className="rounded-md border border-danger-border bg-danger-soft px-3 py-2 text-sm text-danger-text">
          {error}
        </p>
      ) : null}

      <div>
        <label className="block text-sm font-medium" htmlFor="email">
          {locale === "is" ? "Netfang" : "Email"}
        </label>
        <input
          id="email"
          name="email"
          type="email"
          required
          autoComplete="username"
          autoFocus
          className={CONTROL}
        />
      </div>

      <div>
        <label className="block text-sm font-medium" htmlFor="password">
          {locale === "is" ? "Lykilorð" : "Password"}
        </label>
        <input
          id="password"
          name="password"
          type="password"
          required
          autoComplete="current-password"
          className={CONTROL}
        />
      </div>

      <button
        type="submit"
        disabled={busy}
        className="w-full rounded-lg bg-accent px-4 py-2.5 text-sm font-medium text-accent-foreground transition hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-40"
      >
        {busy
          ? locale === "is"
            ? "Skrái inn…"
            : "Signing in…"
          : locale === "is"
            ? "Skrá inn"
            : "Sign in"}
      </button>

      <p className="text-center text-xs text-muted">
        {locale === "is" ? "Sömu innskráningarupplýsingar og í bókhaldskerfinu." : "Same details as the bookkeeping app."}
      </p>
    </form>
  );
}
