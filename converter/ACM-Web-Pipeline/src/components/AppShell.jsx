"use client";

/*
 * ═══════════════════════════════════════════════════════════════
 * App Shell
 * ═══════════════════════════════════════════════════════════════
 * Path: src/components/AppShell.jsx
 * Purpose: Hold the three independent pipelines side by side and carry files
 *          between them without another download and upload.
 *
 * The long-running steps stay mounted and are hidden with CSS rather than
 * unmounted. A Meshy generation runs for minutes, and switching to the
 * converter to look at an earlier result must not abandon it.
 */

import { useCallback, useEffect, useRef, useState } from "react";

import ConverterClient from "@/components/ConverterClient";
import CrystalComposerClient from "@/components/CrystalComposerClient";
import CrystalViewerClient from "@/components/CrystalViewerClient";
import EnvironmentsClient from "@/components/EnvironmentsClient";
import ImageClient from "@/components/ImageClient";
import LanguageToggle from "@/components/LanguageToggle";
import { useLanguage } from "@/components/LanguageProvider";
import MeshyClient from "@/components/MeshyClient";
import PhotoLibrary from "@/components/PhotoLibrary";
import PipelineSidebar from "@/components/PipelineSidebar";
import ReliefClient from "@/components/ReliefClient";
import ReviewClient from "@/components/ReviewClient";
import ThemeToggle from "@/components/ThemeToggle";
import {
  NAV_ITEMS,
  NAVIGATION_QUERY_PARAM,
  meshyModeFor,
  navIdForSlug,
  navSlugFor,
} from "@/lib/navigation";

export default function AppShell({
  converter,
  meshy,
  image,
  relief,
  environments,
  composerBlanks,
  initialView,
}) {
  const { t } = useLanguage();
  const [active, setActive] = useState(initialView);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const [imageState, setImageState] = useState(image);
  const [meshyState, setMeshyState] = useState(meshy);
  const [reliefState, setReliefState] = useState(relief);

  // The handoff carries the file plus whatever context came with it. Its
  // timestamp is what re-keys the converter, so handing the same file over
  // twice still lands.
  const [converterHandoff, setConverterHandoff] = useState(null);
  const [reliefHandoff, setReliefHandoff] = useState(null);
  const [viewerHandoff, setViewerHandoff] = useState(null);

  // The Meshy panel publishes its own refresh here, so a file dropped into
  // its input folder can be picked up without remounting a running job.
  const meshyRefresh = useRef(null);

  const meshyMode = meshyModeFor(active);
  const current = NAV_ITEMS[active];

  /**
   * Keep browser Back/Forward in sync and replace missing or legacy values
   * with the canonical bookmarkable slug without adding a history entry.
   */
  useEffect(() => {
    const syncFromUrl = () => {
      const url = new URL(window.location.href);
      const nextActive = navIdForSlug(url.searchParams.get(NAVIGATION_QUERY_PARAM));
      const canonicalSlug = navSlugFor(nextActive);

      if (url.searchParams.get(NAVIGATION_QUERY_PARAM) !== canonicalSlug) {
        url.searchParams.set(NAVIGATION_QUERY_PARAM, canonicalSlug);
        window.history.replaceState(null, "", `${url.pathname}${url.search}${url.hash}`);
      }

      setActive(nextActive);
      setSidebarOpen(false);
    };

    syncFromUrl();
    window.addEventListener("popstate", syncFromUrl);
    return () => window.removeEventListener("popstate", syncFromUrl);
  }, []);

  /**
   * Move every pipeline navigation to the top of the shared document.
   * The panels deliberately share one page scroll position because long-running
   * jobs remain mounted, so changing the visible panel must reset it explicitly.
   */
  const selectView = useCallback((nextActive) => {
    if (!NAV_ITEMS[nextActive]) return;

    const url = new URL(window.location.href);
    const nextSlug = navSlugFor(nextActive);
    if (url.searchParams.get(NAVIGATION_QUERY_PARAM) !== nextSlug) {
      url.searchParams.set(NAVIGATION_QUERY_PARAM, nextSlug);
      window.history.pushState(null, "", `${url.pathname}${url.search}${url.hash}`);
    }

    setActive(nextActive);
    setSidebarOpen(false);

    window.requestAnimationFrame(() => {
      window.scrollTo({ top: 0, left: 0, behavior: "auto" });
    });
  }, []);

  /** Re-read both workspaces after anything moves a file between them. */
  const refreshLibrary = useCallback(async () => {
    try {
      const [imageResponse, meshyResponse, reliefResponse] = await Promise.all([
        fetch("/api/image/state", { cache: "no-store" }),
        fetch("/api/meshy/state", { cache: "no-store" }),
        fetch("/api/relief/state", { cache: "no-store" }),
      ]);
      setImageState(await imageResponse.json());
      setMeshyState(await meshyResponse.json());
      setReliefState(await reliefResponse.json());
    } catch {
      // A listing failure is not worth an error banner in the shell.
    }
    meshyRefresh.current?.();
  }, []);

  const receiveIntoConverter = (payload) => {
    setConverterHandoff({ ...payload, at: Date.now() });
    selectView("converter");
  };

  const receiveIntoMeshy = () => {
    meshyRefresh.current?.();
    selectView("meshy:image_to_3d");
  };

  /** Keep the prepared PNG on local disk and open it as the active 2.5D input. */
  const receiveIntoRelief = (payload) => {
    setReliefHandoff({ ...payload, at: Date.now() });
    selectView("relief");
  };

  /** Open the finished relief GLB in Leið B without another file picker. */
  const receiveIntoViewer = (job) => {
    const previewName = job.files?.preview || "relief.glb";
    setViewerHandoff({
      url: `/api/file?root=relief-output&path=${encodeURIComponent(`${job.jobId}/${previewName}`)}`,
      name: `${job.jobId}-${previewName}`,
      kind: "glb",
      template: job.template,
      at: Date.now(),
    });
    selectView("viewer");
  };

  return (
    <div className="min-h-screen lg:flex">
      <PipelineSidebar
        active={active}
        onSelect={selectView}
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      <div className="min-w-0 flex-1">
        {/* Top bar - which step you are on, and the theme control */}
        <header className="sticky top-0 z-20 flex items-center justify-between gap-4 border-b border-surface-border bg-background/95 px-4 py-4 backdrop-blur sm:px-8">
          <div className="flex min-w-0 items-center gap-3">
            <button
              type="button"
              onClick={() => setSidebarOpen(true)}
              aria-label="Open pipeline navigation"
              className="rounded-md border border-surface-border px-2.5 py-1.5 text-sm lg:hidden"
            >
              ☰
            </button>
            <div className="min-w-0">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-muted">
              {current?.section?.step ? `Pipeline ${current.section.step} · ` : ""}
              {t(current?.section?.label)} · ACM Pipeline
            </p>
            <p className="truncate text-sm text-muted-strong">{t(current?.blurb)}</p>
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <LanguageToggle />
            <ThemeToggle />
          </div>
        </header>

        <main className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-8 sm:py-8">
          {/* Shared image library - stateless enough to mount on demand */}
          {active === "library" ? (
            <PhotoLibrary
              image={imageState}
              meshy={meshyState}
              onRefresh={refreshLibrary}
              onGoTo={selectView}
            />
          ) : null}

          {/* Image pipeline - kept mounted because a clean-up chain can run for minutes */}
          <div className={active === "image" ? "" : "hidden"}>
            <ImageClient initialState={imageState} onSendToMeshy={receiveIntoMeshy} />
          </div>

          {/*
           * Meshy modes are keyed so each has its own
           * form state and its own selection, and remounting on a mode change
           * is exactly the reset that should happen.
           */}
          {meshyMode ? (
            <MeshyClient
              key={meshyMode}
              mode={meshyMode}
              initialState={meshyState}
              onSendToConverter={receiveIntoConverter}
              onGoTo={selectView}
              refreshRef={meshyRefresh}
            />
          ) : null}

          {/* Meshy job history and review */}
          {active === "review" ? (
            <ReviewClient
              initialJobs={meshyState.jobs || []}
              onSendToConverter={receiveIntoConverter}
            />
          ) : null}

          {/* Leið A stays independent from the long-running 2.5D panel. */}
          {active === "composer" ? (
            <CrystalComposerClient blankOptions={composerBlanks} onContinue={receiveIntoRelief} />
          ) : null}

          {/*
           * 2.5D pipeline - kept mounted, because a Marigold run with a large
           * ensemble takes minutes and switching tabs must not abandon it.
           */}
          <div className={active === "relief" ? "" : "hidden"}>
            <ReliefClient
              initialState={reliefState}
              handoff={reliefHandoff}
              onSendToConverter={receiveIntoConverter}
              onOpenViewer={receiveIntoViewer}
            />
          </div>

          {/* Standalone crystal viewer - stateless, so it mounts on demand */}
          {active === "viewer" ? <CrystalViewerClient handoff={viewerHandoff} /> : null}

          {/*
           * Converter pipeline. Re-keyed on each handoff so the incoming model is already
           * selected on first render. Losing a conversion that was running at
           * that moment is the accepted trade - a handoff is a fresh start.
           */}
          <div className={active === "converter" ? "" : "hidden"}>
            <ConverterClient
              key={converterHandoff ? `handoff-${converterHandoff.at}` : "converter"}
              initialInputs={converter.inputs}
              initialOutputs={converter.outputs}
              initialMeshyJobs={meshyState.jobs || []}
              handoff={converterHandoff}
            />
          </div>

          {active === "environments" ? (
            <EnvironmentsClient initial={environments} />
          ) : null}
        </main>
      </div>
    </div>
  );
}
