/*
 * ═══════════════════════════════════════════════════════════════
 * Auth.js Configuration
 * ═══════════════════════════════════════════════════════════════
 * Path: src/auth.js
 * Purpose: Credentials sign-in for the one operator who drives this.
 *
 * Same shape as acm_bookkeeping's setup on purpose - email plus an argon2id
 * hash, JWT sessions, no adapter and no Session table - so the same person
 * signs in with the same details in both places. To invalidate every session
 * at once, rotate AUTH_SECRET.
 */

import { randomBytes } from "node:crypto";

import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";
import argon2 from "argon2";

import { authConfig } from "@/auth.config";
import { prisma } from "@/lib/prisma";

/*
 * A hash of a random secret, computed once and reused.
 *
 * Verifying against this when the email is unknown makes a wrong email cost
 * the same as a wrong password, so the form cannot be used to work out which
 * addresses have accounts. Built at first use rather than hard-coded, because
 * a hard-coded hash that turns out to be malformed silently skips the delay
 * it exists to create.
 */
let dummyHash = null;
async function timingDecoy() {
  dummyHash ||= await argon2.hash(randomBytes(32).toString("hex"), { type: argon2.argon2id });
  return dummyHash;
}

export const { auth, handlers, signIn, signOut } = NextAuth({
  ...authConfig,
  providers: [
    Credentials({
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" },
      },

      authorize: async (credentials) => {
        if (!credentials?.email || !credentials?.password) return null;

        const user = await prisma.user.findUnique({
          where: { email: String(credentials.email).toLowerCase().trim() },
        });

        const hash = user?.passwordHash || (await timingDecoy());
        let valid = false;
        try {
          valid = await argon2.verify(hash, String(credentials.password));
        } catch {
          valid = false;
        }

        if (!user || !user.isActive || !valid) {
          console.log("[auth] Sign-in failed");
          return null;
        }

        console.log(`[auth] Signed in: ${user.email} (${user.role})`);
        return {
          id: user.id,
          email: user.email,
          name: user.name ?? null,
          role: user.role,
          mustChangePassword: user.mustChangePassword,
        };
      },
    }),
  ],
});
