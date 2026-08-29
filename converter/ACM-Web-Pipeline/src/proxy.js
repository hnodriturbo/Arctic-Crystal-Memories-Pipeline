/*
 * ═══════════════════════════════════════════════════════════════
 * Access Guard
 * ═══════════════════════════════════════════════════════════════
 * Path: src/proxy.js
 * Purpose: Keep the pipeline behind a sign-in now that it is on a public
 *          domain.
 *
 * `proxy.js`, not `middleware.js` - Next 16 renamed the convention and warns
 * on the old name.
 *
 * This app spawns Python, serves three workspace folders and spends Meshy
 * credits, so every route is closed unless the request carries a valid
 * session cookie. The rules live in auth.config.js because this runs on the
 * Edge runtime, where the Prisma and argon2 half of the Auth.js setup cannot
 * load.
 */

import NextAuth from "next-auth";

import { authConfig } from "@/auth.config";

// Destructured separately: Next resolves the exported function by static
// analysis, and a destructured `export const { auth: proxy }` is not something
// it recognises as a function export.
const { auth } = NextAuth(authConfig);

export default function proxy(request, event) {
  return auth(request, event);
}

export const config = {
  /*
   * Everything except Next's own static output.
   *
   * /login, /api/auth and /webhooks are still matched here and then let
   * through by the `authorized` callback, which keeps the whole public list in
   * one place rather than splitting it between a regex and a callback.
   */
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
