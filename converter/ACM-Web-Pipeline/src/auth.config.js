/*
 * ═══════════════════════════════════════════════════════════════
 * Auth Config (edge-safe)
 * ═══════════════════════════════════════════════════════════════
 * Path: src/auth.config.js
 * Purpose: The half of the Auth.js setup that middleware can run.
 *
 * Middleware executes on the Edge runtime, where Prisma and argon2 cannot
 * load at all. So the config splits: this file holds the session rules and
 * the route guard, and src/auth.js adds the Credentials provider that
 * actually touches the database. Middleware imports only this half and reads
 * the signed JWT cookie, which is all it needs to know whether someone is
 * signed in.
 */

// Everything the operator has no business seeing while signed out.
const PUBLIC_PREFIXES = ["/login", "/api/auth", "/webhooks"];

export const authConfig = {
  // Providers are added in src/auth.js; middleware never needs one.
  providers: [],

  session: {
    strategy: "jwt",
    maxAge: 60 * 60 * 12,
  },

  pages: {
    signIn: "/login",
  },

  callbacks: {
    // Role rides along in the token so no request has to hit the database.
    jwt({ token, user }) {
      if (user) {
        token.id = user.id;
        token.role = user.role;
        token.mustChangePassword = user.mustChangePassword;
      }
      return token;
    },

    session({ session, token }) {
      if (session.user) {
        session.user.id = token.id;
        session.user.role = token.role;
        session.user.mustChangePassword = token.mustChangePassword;
      }
      return session;
    },

    /**
     * The guard middleware runs on every request.
     *
     * /webhooks is public because Meshy cannot sign in - that route
     * authenticates each delivery by signature and task id instead.
     */
    authorized({ auth, request }) {
      const { pathname } = request.nextUrl;
      if (PUBLIC_PREFIXES.some((prefix) => pathname.startsWith(prefix))) return true;
      if (
        process.env.NODE_ENV === "development" &&
        process.env.PIPELINE_DEV_AUTH_BYPASS === "true"
      ) {
        return true;
      }
      return Boolean(auth?.user);
    },
  },
};
