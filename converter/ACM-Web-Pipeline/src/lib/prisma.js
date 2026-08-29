/*
 * ═══════════════════════════════════════════════════════════════
 * Prisma Client
 * ═══════════════════════════════════════════════════════════════
 * Path: src/lib/prisma.js
 * Purpose: One database client for the process.
 *
 * Prisma 7 has no binary engine any more - a driver adapter is required, and
 * PrismaPg is the one that wraps `pg`. The client is cached on globalThis
 * because next dev re-evaluates modules on every edit, and a fresh
 * PrismaClient per reload exhausts the connection pool within minutes.
 */

import { PrismaPg } from "@prisma/adapter-pg";
import { PrismaClient } from "@prisma/client";

const globalForPrisma = globalThis;

function createClient() {
  const connectionString = process.env.DATABASE_URL;
  if (!connectionString) {
    throw new Error("DATABASE_URL is not set. Add it to .env.local and restart the server.");
  }

  return new PrismaClient({
    adapter: new PrismaPg({ connectionString }),
    log: process.env.NODE_ENV === "development" ? ["warn", "error"] : ["error"],
  });
}

export const prisma = globalForPrisma.acmPipelinePrisma ?? createClient();

if (process.env.NODE_ENV !== "production") {
  globalForPrisma.acmPipelinePrisma = prisma;
}
