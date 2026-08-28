/*
 * ═══════════════════════════════════════════════════════════════
 * Prisma 7 Configuration
 * ═══════════════════════════════════════════════════════════════
 * Path: prisma.config.mjs
 * Purpose: Tell the Prisma CLI where the schema and the database are.
 *
 * .mjs rather than .ts because this project has no TypeScript, and the
 * package has no "type": "module" so the extension has to say so explicitly.
 *
 * Prisma 7 does not load .env files on its own, and this app keeps its
 * settings in Next's .env.local / .env.production rather than a plain .env -
 * so the loader below reads them in Next's own precedence order. Without it
 * every CLI command fails with "environment variable not found:
 * DATABASE_URL" while the running app connects perfectly well.
 */

import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { defineConfig, env } from "prisma/config";

// Lowest priority first; the first file to define a key wins, matching how
// Next.js layers .env.local over .env.production over .env.
const ENV_FILES = [".env.local", ".env.production", ".env.development", ".env"];

for (const file of ENV_FILES) {
  let contents;
  try {
    contents = readFileSync(resolve(process.cwd(), file), "utf8");
  } catch {
    continue;
  }

  for (const line of contents.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;

    const separator = trimmed.indexOf("=");
    if (separator === -1) continue;

    const key = trimmed.slice(0, separator).trim();
    let value = trimmed.slice(separator + 1).trim();

    // A quoted value keeps any trailing spaces or '#' it was protecting.
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    if (key && !process.env[key]) process.env[key] = value;
  }
}

export default defineConfig({
  schema: "prisma/schema.prisma",
  migrations: {
    path: "prisma/migrations",
  },
  datasource: {
    url: env("DATABASE_URL"),
  },
});
