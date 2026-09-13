/*
 * ═══════════════════════════════════════════════════════════════
 * Seed Admin
 * ═══════════════════════════════════════════════════════════════
 * Path: scripts/seed-admin.mjs
 * Purpose: Create or update the single operator account.
 *
 * Two ways to give it a password, in order of preference:
 *
 *   PIPELINE_ADMIN_PASSWORD_HASH  an argon2id hash copied from another
 *                                 system - the same password then works in
 *                                 both places and nothing here ever sees the
 *                                 plaintext.
 *   PIPELINE_ADMIN_PASSWORD       a plaintext password, hashed on the way in.
 *
 * Idempotent: run it again to reset the password or re-activate the account.
 * It never prints either value.
 */

import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { PrismaPg } from "@prisma/adapter-pg";
import { PrismaClient } from "@prisma/client";
import argon2 from "argon2";

// Run outside Next, so nothing has loaded the env files yet. Same precedence
// Next itself uses, and the same list prisma.config.mjs walks.
for (const file of [".env.local", ".env.production", ".env.development", ".env"]) {
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
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    if (key && !process.env[key]) process.env[key] = value;
  }
}

const prisma = new PrismaClient({
  adapter: new PrismaPg({ connectionString: process.env.DATABASE_URL }),
});

const email = (process.env.PIPELINE_ADMIN_EMAIL || "hreidar@acm.is").toLowerCase().trim();
const name = process.env.PIPELINE_ADMIN_NAME || "Hreiðar";
const providedHash = process.env.PIPELINE_ADMIN_PASSWORD_HASH;
const plaintext = process.env.PIPELINE_ADMIN_PASSWORD;

async function main() {
  if (!providedHash && !plaintext) {
    throw new Error(
      "Set PIPELINE_ADMIN_PASSWORD_HASH (preferred) or PIPELINE_ADMIN_PASSWORD before running this.",
    );
  }

  // A copied hash has to be a real argon2 hash, or every sign-in would fail
  // with a confusing "wrong password" long after this script said it worked.
  if (providedHash && !providedHash.startsWith("$argon2")) {
    throw new Error("PIPELINE_ADMIN_PASSWORD_HASH is not an argon2 hash.");
  }

  const passwordHash =
    providedHash || (await argon2.hash(plaintext, { type: argon2.argon2id }));

  const user = await prisma.user.upsert({
    where: { email },
    create: { email, name, passwordHash, role: "OWNER", isActive: true },
    update: { name, passwordHash, isActive: true, mustChangePassword: false },
  });

  console.log(`Admin ready: ${user.email} (${user.role})`);
  console.log(providedHash ? "  password: copied hash, unchanged" : "  password: hashed from plaintext");
}

main()
  .catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
  })
  .finally(() => prisma.$disconnect());
