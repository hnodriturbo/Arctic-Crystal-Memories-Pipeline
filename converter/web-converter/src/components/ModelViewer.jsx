"use client";

/*
 * ═══════════════════════════════════════════════════════════════
 * Model Viewer
 * ═══════════════════════════════════════════════════════════════
 * Path: src/components/ModelViewer.jsx
 * Purpose: Turn a finished GLB in the page so a bad generation is obvious
 *          before anyone spends an hour sampling it into a point cloud.
 *
 * <model-viewer> is a custom element that touches window on import, so it is
 * loaded in an effect rather than at module scope, where the server render
 * would fail on it.
 */

import { useEffect, useRef, useState } from "react";

export default function ModelViewer({ src, poster, alt = "Generated 3D model", className = "" }) {
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(null);
  const hostRef = useRef(null);

  // Registering the element twice is harmless - the import is cached - so this
  // runs per mount rather than being hoisted into a module-level singleton.
  useEffect(() => {
    let cancelled = false;
    import("@google/model-viewer")
      .then(() => !cancelled && setReady(true))
      .catch((error) => !cancelled && setFailed(error.message));
    return () => {
      cancelled = true;
    };
  }, []);

  // The element reports load failures as events, not as a thrown import error.
  useEffect(() => {
    const host = hostRef.current;
    if (!host) return undefined;
    const onError = () => setFailed("The viewer could not read that model file.");
    host.addEventListener("error", onError);
    return () => host.removeEventListener("error", onError);
  }, [ready, src]);

  const frame =
    "relative aspect-square w-full overflow-hidden rounded-lg border border-surface-border bg-console-background";

  if (failed) {
    return (
      <div className={`${frame} ${className} flex items-center justify-center p-6`}>
        <p className="text-center text-xs text-warning-text">{failed}</p>
      </div>
    );
  }

  if (!ready) {
    return (
      <div className={`${frame} ${className} flex items-center justify-center`}>
        <p className="font-mono text-xs text-console-muted">loading viewer…</p>
      </div>
    );
  }

  return (
    <div className={`${frame} ${className}`}>
      <model-viewer
        ref={hostRef}
        src={src}
        poster={poster}
        alt={alt}
        camera-controls=""
        auto-rotate=""
        rotation-per-second="12deg"
        shadow-intensity="1"
        exposure="1.1"
        environment-image="neutral"
        touch-action="pan-y"
        style={{ width: "100%", height: "100%", backgroundColor: "transparent" }}
      />
      <p className="pointer-events-none absolute bottom-2 left-3 font-mono text-[10px] text-console-muted">
        drag to orbit · scroll to zoom
      </p>
    </div>
  );
}
