// src/core/prisma.js
// Singleton Prisma 7 client using @prisma/adapter-pg.
// DATABASE_URL is read as a plain string so special characters in the
// password (!, @, #) survive without URL-encoding issues.

import { PrismaClient } from "@prisma/client";
import { PrismaPg } from "@prisma/adapter-pg";
import { buildSafePgUrl } from "./pgUrl.js";

function buildClient() {
  const connectionString = buildSafePgUrl(process.env.DATABASE_URL || "");
  const adapter = new PrismaPg({ connectionString });
  return new PrismaClient({ adapter });
}

const globalForPrisma = globalThis;

const prisma = globalForPrisma.prisma ?? buildClient();

if (process.env.NODE_ENV !== "production") {
  globalForPrisma.prisma = prisma;
}

export default prisma;
