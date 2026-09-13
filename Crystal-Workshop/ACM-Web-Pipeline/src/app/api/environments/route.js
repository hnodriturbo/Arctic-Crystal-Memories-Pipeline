/*
 * ══════════════════════════════════════════════════════════════
 * Environments Route
 * ══════════════════════════════════════════════════════════════
 * Path: src/app/api/environments/route.js
 * Purpose: Report what each Python environment on this machine can do.
 */

import { readEnvironments } from "@/lib/environments";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 120;

export async function GET() {
  return Response.json(await readEnvironments());
}
