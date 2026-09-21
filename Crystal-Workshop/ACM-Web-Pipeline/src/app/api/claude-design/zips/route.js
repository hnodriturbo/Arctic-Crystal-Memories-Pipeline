/*
 * ═══════════════════════════════════════════════════════════════
 * Claude Design Zips Route
 * ═══════════════════════════════════════════════════════════════
 * Path: src/app/api/claude-design/zips/route.js
 * Purpose: The zip shelf, read and unpacked on its own.
 *
 * GET  -> every archive, and whether a folder already exists for it
 * POST -> unpack one archive into its own new folder
 *
 * Its own route rather than part of the library, because a zip is the one
 * thing here that cannot be previewed, played or rendered until it has been
 * opened. Keeping the two readers apart is what makes a sealed archive
 * obvious at a glance.
 */

import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

import { auth } from "@/auth";
import { DESIGN_ROOT, ZIP_DIR, safeJoin } from "@/lib/claude-design/paths";
import { listZips } from "@/lib/claude-design/scan";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  if (!(await auth())?.user) return new Response(null, { status: 401 });
  return Response.json(
    { zips: listZips(), zipDir: ZIP_DIR },
    { headers: { "Cache-Control": "private, no-store" } },
  );
}

/** Run one command and resolve with its outcome rather than throwing. */
function runCommand(command, args) {
  return new Promise((resolve) => {
    const child = spawn(command, args, { windowsHide: true });
    let stderr = "";
    child.stderr.on("data", (chunk) => {
      stderr += chunk;
    });
    child.on("error", (error) => resolve({ ok: false, message: String(error.message) }));
    child.on("close", (code) => resolve({ ok: code === 0, message: stderr.slice(-2000) }));
  });
}

export async function POST(request) {
  if (!(await auth())?.user) return new Response(null, { status: 401 });

  const { name } = await request.json();
  if (!name || !/\.zip$/i.test(name) || name.includes("/") || name.includes("\\")) {
    return Response.json({ error: "That is not a zip file name." }, { status: 400 });
  }

  const zipPath = safeJoin(ZIP_DIR, name);
  if (!zipPath || !fs.existsSync(zipPath)) {
    return Response.json({ error: "No such archive." }, { status: 404 });
  }

  // The folder takes the archive's name. If one is already there nothing
  // happens - overwriting a design the operator may have edited since is worse
  // than making them rename something by hand.
  const targetDir = safeJoin(DESIGN_ROOT, path.basename(name, path.extname(name)));
  if (!targetDir) return Response.json({ error: "Invalid destination." }, { status: 400 });
  if (fs.existsSync(targetDir)) {
    return Response.json(
      { error: `The folder "${path.basename(targetDir)}" already exists.` },
      { status: 409 },
    );
  }

  // PowerShell is already on the Windows box and unzip on the VPS, so neither
  // needs a dependency added for one operation.
  const result =
    process.platform === "win32"
      ? await runCommand("powershell.exe", [
          "-NoProfile",
          "-NonInteractive",
          "-Command",
          `Expand-Archive -LiteralPath "${zipPath}" -DestinationPath "${targetDir}" -Force`,
        ])
      : await runCommand("unzip", ["-q", zipPath, "-d", targetDir]);

  if (!result.ok) {
    return Response.json({ error: result.message || "Unpacking failed." }, { status: 500 });
  }
  return Response.json({ ok: true, folder: path.basename(targetDir) });
}
