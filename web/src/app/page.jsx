// src/app/page.jsx
// Main dashboard — shows all pipeline images as thumbnails with folder filtering.
// Protected by middleware; requires authenticated session.

import { auth } from "@/auth";
import { redirect } from "next/navigation";
import ClientShell from "./components/ClientShell";

export default async function HomePage() {
  const session = await auth();
  if (!session) redirect("/login");

  return <ClientShell user={session.user} />;
}
