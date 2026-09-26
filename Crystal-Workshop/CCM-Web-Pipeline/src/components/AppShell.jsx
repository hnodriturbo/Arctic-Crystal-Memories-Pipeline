"use client";

/*
 * ═══════════════════════════════════════════════════════════════
 * App Shell
 * ═══════════════════════════════════════════════════════════════
 * Path: src/components/AppShell.jsx
 * Purpose: Hold the image, Meshy, and converter pipelines side by side and carry files
 *          between them without another download and upload.
 *
 * The long-running steps stay mounted and are hidden with CSS rather than
 * unmounted. A Meshy generation runs for minutes, and switching to the
 * converter to look at an earlier result must not abandon it.
 */

import { useCallback, useEffect, useRef, useState } from "react";

import R2FileBrowser from "@/components/R2FileBrowser";
import ClaudeDesignClient from "@/components/ClaudeDesignClient";
import ClaudeDesignZips from "@/components/ClaudeDesignZips";
import ConverterClient from "@/components/ConverterClient";
import WorkshopHome from "@/components/WorkshopHome";
import ReconstructClient from "@/components/ReconstructClient";
import EnvironmentsClient from "@/components/EnvironmentsClient";
import ImageClient from "@/components/ImageClient";
import LanguageToggle from "@/components/LanguageToggle";
import { useLanguage } from "@/components/LanguageProvider";
import MeshyClient from "@/components/MeshyClient";
import PhotoLibrary from "@/components/PhotoLibrary";
import PipelineSidebar from "@/components/PipelineSidebar";
import ReviewClient from "@/components/ReviewClient";
import CreateUser from "@/components/CreateUser";
import ThemeToggle from "@/components/ThemeToggle";
import {
  NAV_ITEMS,
  SECTION_VIEWS,
  sectionNavId,
  NAVIGATION_QUERY_PARAM,
  meshyModeFor,
  navIdForSlug,
  navSlugFor,
} from "@/lib/navigation";

export default function AppShell({
  converter,
  meshy,
  image,
  environments,
  initialView,
}) {
  const { t, locale } = useLanguage();
  const [active, setActive] = useState(initialView);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  // Unpacking an archive creates a collection, so the animations panel is
  // re-keyed to pick it up rather than being left showing a stale library.
  const [designReload, setDesignReload] = useState(0);

  const [imageState, setImageState] = useState(image);
  const [meshyState, setMeshyState] = useState(meshy);

  // The handoff carries the file plus whatever context came with it. Its
  // timestamp is what re-keys the converter, so handing the same file over
  // twice still lands.
  const [converterHandoff, setConverterHandoff] = useState(null);

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
      url.hash = "";
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
      const [imageResponse, meshyResponse] = await Promise.all([
        fetch("/api/image/state", { cache: "no-store" }),
        fetch("/api/meshy/state", { cache: "no-store" }),
      ]);
      setImageState(await imageResponse.json());
      setMeshyState(await meshyResponse.json());
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

  return (
    <div className="min-h-screen lg:flex">
      <PipelineSidebar
        collapsed={sidebarCollapsed}
        onCollapse={() => setSidebarCollapsed(true)}
        active={active}
        onSelect={selectView}
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      <div className="min-w-0 flex-1">
        {/* Top bar - which step you are on, and the theme control */}
        <header className="sticky top-0 z-20 flex items-center justify-between gap-4 border-b border-surface-border bg-background/95 px-4 py-4 backdrop-blur sm:px-8">
          <div className="flex min-w-0 items-center gap-3">
            {sidebarCollapsed && <button type="button" onClick={() => setSidebarCollapsed(false)} aria-label="Expand navigation" className="hidden rounded-md border border-surface-border px-3 py-2 lg:block">→</button>}
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
              {t(current?.section?.label)} · Crystal Workshop
            </p>
            <p className="truncate text-sm text-muted-strong">{t(current?.blurb)}</p>
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <CreateUser en={locale === "en"} />
            <LanguageToggle />
            <ThemeToggle />
          </div>
        </header>

        <main className="mx-auto w-full max-w-[1600px] px-4 py-6 sm:px-8 sm:py-8">
          {active === "r2-browser" && <R2FileBrowser onUse={receiveIntoConverter} />}
          {active === 'home' && <WorkshopHome onSelect={selectView} />}
          {SECTION_VIEWS[active] && <WorkshopHome section={SECTION_VIEWS[active]} onSelect={selectView} />}
          {active !== 'home' && !SECTION_VIEWS[active] && current?.section?.id && (
            <button type="button" onClick={() => selectView(sectionNavId(current.section.id))} className="mb-5 rounded-lg px-3 py-2 text-sm text-accent hover:bg-accent-soft">← {t(current.section.label)}</button>
          )}
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

          {/*
           * Claude Design. The animations panel stays mounted like the other
           * long-running ones - a render runs for tens of minutes and its
           * console must survive a look at the archives and back.
           */}
          <div className={active === "claude-design-animations" ? "" : "hidden"}>
            <ClaudeDesignClient key={designReload} />
          </div>

          {active === "claude-design-zips" ? (
            <ClaudeDesignZips onUnpacked={() => setDesignReload((value) => value + 1)} />
          ) : null}

          {active === "environments" ? (
            <EnvironmentsClient initial={environments} />
          ) : null}
          <div className={active === "cockpit-reconstruct" ? "" : "hidden"}>
            <ReconstructClient onSendToConverter={receiveIntoConverter} />
          </div>
        </main>
      </div>
    </div>
  );
}
