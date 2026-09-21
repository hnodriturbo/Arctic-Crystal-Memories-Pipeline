/*
 * ═══════════════════════════════════════════════════════════════
 * Seed Agent
 * ═══════════════════════════════════════════════════════════════
 * Path: scripts/seed-agent.mjs
 * Purpose: Create or reset the AI review account from the environment.
 *
 *   npm run db:seed:agent
 *
 * A separate account from the owner's, deliberately. Sign-ins land in the auth
 * log under their own address, so it is always clear whether a person or an
 * agent did something, and the account can be switched off on its own without
 * touching the owner's access.
 *
 * ADMIN rather than OWNER: of the two roles this schema has, it is the lesser,
 * and nothing an agent does to review the workshop needs more.
 *
 * Idempotent, and it never prints the password - run it again to rotate one.
 */

import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { PrismaPg } from "@prisma/adapter-pg";
import { PrismaClient } from "@prisma/client";
import argon2 from "argon2";

// Runs outside Next, so nothing has loaded the env files yet. Same precedence
// Next itself uses, and the same list seed-admin.mjs walks.
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

const username = (process.env.AGENT_USERNAME || "ClaudeCodexCLI").trim();
const password = process.env.AGENT_PASSWORD;

/*
 * The User model authenticates on email and has no username column, so the
 * name carries AGENT_USERNAME and the address is derived from it. Setting
 * AGENT_EMAIL to a real address overrides that.
 */
const email = (process.env.AGENT_EMAIL || `${username.toLowerCase()}@acm.is`)
  .toLowerCase()
  .trim();

async function main() {
  if (!password) {
    throw new Error("Set AGENT_PASSWORD in the environment file before running this.");
  }
  if (password.length < 24) {
    throw new Error("AGENT_PASSWORD is shorter than 24 characters. Use a generated value.");
  }

  const passwordHash = await argon2.hash(password, { type: argon2.argon2id });

  const user = await prisma.user.upsert({
    where: { email },
    create: { email, name: username, passwordHash, role: "ADMIN", isActive: true },
    // The role is set on update too, so an account promoted by hand does not
    // quietly stay that way across a rotation.
    update: { name: username, passwordHash, role: "ADMIN", isActive: true, mustChangePassword: false },
  });

  console.log(`Agent account ready: ${user.email} (${user.role})`);
  console.log(`  name     : ${user.name}`);
  console.log("  password : set from AGENT_PASSWORD, not printed");
}

main()
  .catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
  })
  .finally(() => prisma.$disconnect());
