// src/app/api/auth/[...nextauth]/route.js
// NextAuth v5 route handler — handles all /api/auth/* requests.

import { handlers } from "@/auth";
export const { GET, POST } = handlers;
