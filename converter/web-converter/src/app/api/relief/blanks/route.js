/*
 * ═══════════════════════════════════════════════════════════════
 * Relief Blanks Route
 * ═══════════════════════════════════════════════════════════════
 * Path: src/app/api/relief/blanks/route.js
 * Purpose: List the real crystal blanks imported from a local Cockpit 3D
 *          installation, so the viewer can frame a model in the actual shape
 *          rather than a generic box.
 *
 * Empty until `python code/import_blanks.py` has been run in 2.5D-pipeline/.
 * That is not an error - the viewer falls back to its RoundedBoxGeometry.
 */

import { readFile } from "node:fs/promises";
import path from "node:path";

import { RELIEF_BLANKS_DIR } from "@/lib/paths";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const manifest = await readFile(path.join(RELIEF_BLANKS_DIR, "blanks.json"), "utf-8");
    return Response.json({ imported: true, ...JSON.parse(manifest) });
  } catch {
    return Response.json({ imported: false, blanks: [] });
  }
}
