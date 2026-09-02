/*
 * ═══════════════════════════════════════════════════════════════
 * R2 Converter Import Route
 * ═══════════════════════════════════════════════════════════════
 * Path: src/app/api/r2/import/route.js
 * Purpose: Materialize one durable R2 model inside the converter workspace.
 */

import { stat } from "node:fs/promises";
import path from "node:path";

import { availableFileName, safeFileName, UPLOAD_DIR } from "@/lib/paths";
import { downloadObject, r2Configured } from "@/lib/storage/r2";

export const runtime = "nodejs";
export const maxDuration = 3600;

const ALLOWED_PREFIXES = ["jobs/", "uploads/"];
const CONVERTER_EXTENSIONS = new Set([
  ".blend", ".obj", ".dxf", ".cad", ".xyz", ".ply", ".stl", ".cockpit",
  ".glb", ".gltf", ".fbx", ".dae", ".usd", ".usda", ".usdc", ".usdz",
]);

export async function POST(request) {
  if (!r2Configured()) {
    return Response.json({ error: "R2 is not configured on this server." }, { status: 503 });
  }

  const { key } = await request.json();
  const normalized = typeof key === "string" ? path.posix.normalize(key) : "";
  if (
    !normalized ||
    normalized !== key ||
    normalized.includes("..") ||
    !ALLOWED_PREFIXES.some((prefix) => normalized.startsWith(prefix))
  ) {
    return Response.json({ error: "That R2 object is outside the converter library." }, { status: 400 });
  }

  const fileName = safeFileName(path.posix.basename(normalized));
  const extension = path.extname(fileName).toLowerCase();
  if (!CONVERTER_EXTENSIONS.has(extension)) {
    return Response.json(
      { error: `The converter cannot import ${extension || "that file type"} from R2.` },
      { status: 400 },
    );
  }

  const availableName = await availableFileName(UPLOAD_DIR, fileName);
  const destination = path.join(UPLOAD_DIR, availableName);

  try {
    await downloadObject(normalized, destination);
    const info = await stat(destination);
    return Response.json({
      file: {
        path: `uploads/${availableName}`,
        name: availableName,
        extension,
        bytes: info.size,
        r2Key: normalized,
      },
    });
  } catch (error) {
    return Response.json({ error: `Could not import from R2: ${error.message}` }, { status: 502 });
  }
}
