// middleware.js
// Protects all routes except /login and /api/auth/*.
// Unauthenticated requests are redirected to /login.

import { auth } from "@/auth";

export default auth((req) => {
  const { pathname } = req.nextUrl;
  const isLoggedIn = !!req.auth;

  const isPublic =
    pathname.startsWith("/login") ||
    pathname.startsWith("/api/auth");

  if (!isLoggedIn && !isPublic) {
    const loginUrl = new URL("/login", req.url);
    loginUrl.searchParams.set("callbackUrl", req.url);
    return Response.redirect(loginUrl);
  }
});

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
