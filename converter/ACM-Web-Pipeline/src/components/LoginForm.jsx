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
   * Posted straight to Auth.js's credentials endpoint, and the redirect it
   * answers with is deliberately never followed.
   *
   * `redirect: "manual"` matters more than it looks. Auth.js replies to a form
   * POST with a 302, and following it hands control of where we land to the
   * browser - which on localhost has usually also been serving ACM-Web-Main,
   * a next-intl app that rewrites bare paths to /en/... . That cached rewrite
   * turned a successful sign-in into `GET /en/login 404`, a route this app
   * does not have, which looked exactly like a rejected password. The
   * Set-Cookie still lands, because the browser stores it whether or not the
   * redirect is followed - so the session is asked directly instead.
   */
  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError(null);

    const form = new FormData(event.currentTarget);

    try {
      const csrfResponse = await fetch("/api/auth/csrf");
      const { csrfToken } = await csrfResponse.json();

      await fetch("/api/auth/callback/credentials", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({
          csrfToken,
          email: form.get("email"),
          password: form.get("password"),
          // Same-origin and explicit, so nothing has to guess a destination.
          callbackUrl: new URL("/", window.location.origin).toString(),
        }),
        redirect: "manual",
      });

      // The session cookie is the only trustworthy signal here: an opaque
      // redirect exposes neither a status nor a Location to read.
      const session = await fetch("/api/auth/session", { cache: "no-store" }).then(
        (response) => response.json(),
      );

      if (!session?.user) {
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
