/*
 * ══════════════════════════════════════════════════════════════
 * Login Page
 * ══════════════════════════════════════════════════════════════
 * Path: src/app/login/page.jsx
 * Purpose: The one door into the pipeline.
 */

import LoginForm from "@/components/LoginForm";
import LoginHeader from "@/components/LoginHeader";

export const metadata = {
  title: "Sign in · ACM Pipeline",
};

export default async function LoginPage({ searchParams }) {
  const { error } = await searchParams;

  return (
    <div className="flex min-h-screen items-center justify-center px-6">
      <div className="w-full max-w-sm space-y-6">
        <LoginHeader />

        <LoginForm initialError={error ? "Wrong email or password." : null} />
      </div>
    </div>
  );
}
