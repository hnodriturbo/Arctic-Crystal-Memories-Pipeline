/*
 * ══════════════════════════════════════════════════════════════
 * Pipeline Page
 * ══════════════════════════════════════════════════════════════
 * Path: src/app/page.jsx
 * Purpose: Entry point. Reads all three pipelines' state on the server so
 *          the shell renders complete on first paint.
 */

import AppShell from "@/components/AppShell";
import { readEnvironments } from "@/lib/environments";
import { readImageState } from "@/lib/image/state";
import { listConverterFiles } from "@/lib/list-files";
import { readMeshyState } from "@/lib/meshy/state";
import { NAVIGATION_QUERY_PARAM, navIdForSlug } from "@/lib/navigation";

export const dynamic = "force-dynamic";

export default async function Page({ searchParams }) {
  const resolvedSearchParams = (await searchParams) || {};
  const requestedView = resolvedSearchParams[NAVIGATION_QUERY_PARAM];
  const initialView = navIdForSlug(Array.isArray(requestedView) ? requestedView[0] : requestedView);

  // In parallel: a Meshy balance lookup is a network round trip, and there is
  // no reason the two disk walks should wait behind it.
  const [converter, meshy, image, environments] = await Promise.all([
    listConverterFiles(),
    readMeshyState(),
    readImageState(),
    readEnvironments(),
  ]);

  return (
    <AppShell
      converter={converter}
      meshy={meshy}
      image={image}
      environments={environments}
      initialView={initialView}
    />
  );
}
