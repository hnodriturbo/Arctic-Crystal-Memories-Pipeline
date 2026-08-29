/*
 * ══════════════════════════════════════════════════════════════
 * Auth Route
 * ══════════════════════════════════════════════════════════════
 * Path: src/app/api/auth/[...nextauth]/route.js
 * Purpose: Auth.js sign-in, sign-out and session endpoints.
 */

import { handlers } from "@/auth";

export const runtime = "nodejs";

export const { GET, POST } = handlers;
