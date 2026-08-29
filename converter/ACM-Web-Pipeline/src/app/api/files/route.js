/*
 * ══════════════════════════════════════════════════════════════
 * File Listing Route
 * ══════════════════════════════════════════════════════════════
 * Path: src/app/api/files/route.js
 * Purpose: Refresh the input and output listings after a conversion.
 */

import { listConverterFiles } from "@/lib/list-files";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  return Response.json(await listConverterFiles());
}
