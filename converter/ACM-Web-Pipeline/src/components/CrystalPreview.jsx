"use client";

/*
 * ═══════════════════════════════════════════════════════════════
 * Crystal Preview
 * ═══════════════════════════════════════════════════════════════
 * Path: src/components/CrystalPreview.jsx
 * Purpose: Show anything that can end up inside a K9 blank - a relief GLB, a
 *          POINT DXF, or a plain photograph - lit like real glass.
 *
 * Why not <model-viewer> like ModelViewer.jsx: it CAN do refraction - it
 * bundles three and the KHR_materials_transmission/_volume/_ior/_dispersion
 * extensions - but only from a material baked into the GLB. Two things rule it
 * out here. The glass needs live tuning, and a Blender re-export per parameter
 * makes that impossible. And the engraving must be additive points: each laser
 * dot is a microfracture scattering light outward, so dots stacking along the
 * view axis genuinely get brighter, which is the mechanism behind toning.
 * glTF cannot express that blend mode.
 *
 * This component is the prototype for the customer-facing viewer on acm.is.
 * Keep it dependency-light and framework-free inside the effect, so porting
 * it is a copy rather than a rewrite - see
 * ../../../own_3d_preview_plan.md.
 *
 * Scene units are millimetres, deliberately. `thickness`,
 * `attenuationDistance` and the dot size are physical quantities, so keeping
 * world space in the blank's own units means the numbers mean what they say.
 */

import { useEffect, useRef, useState } from "react";

const FRAME =
  "relative aspect-[4/3] w-full overflow-hidden rounded-lg border border-surface-border bg-black";

// The laser preview uses the production dot diameter everywhere. Sampling
// distance is configured by the 2.5D pipeline; it is a different quantity.
export const PREVIEW_DOT_SIZE_MM = 0.08;

// K9 blanks carry a small chamfer rather than a sharp arris. Barely visible
// head-on, and it completely dominates the silhouette at the three-quarter
// angle a preview idles at. Cockpit 3D's own templates carry the real value in
// their BEVEL field, so this is only the fallback for blanks that omit it.
const CHAMFER_MM = 1.6;

/** What kind of thing a URL is, when the caller has not said. */
function inferKind(url) {
  const clean = String(url || "").split("?")[0].toLowerCase();
  if (clean.endsWith(".dxf")) return "dxf";
  if (/\.(png|jpe?g|webp|bmp)$/.test(clean)) return "photo";
  return "glb";
}

/**
 * Parse POINT entities out of a DXF.
 *
 * The printer format is POINT-only on layer VWX, so this is the same trick
 * parse_dxf_points_fast() uses in Python: scan for group codes 10/20/30 and
 * ignore everything else. No DXF library, and it copes with the 40 MB files a
 * 750k-dot cloud produces.
 *
 * The ENTITIES gate is not optional. The HEADER section's $EXTMIN and $EXTMAX
 * carry group codes 10/20/30 too, so scanning the whole file yields two
 * phantom points at the origin - dead centre of the crystal, which is the most
 * visible place a stray dot could possibly land.
 */
function parseDxfPoints(text, maxPoints) {
  const lines = text.split(/\r?\n/);
  const xs = [];
  const ys = [];
  const zs = [];

  let inEntities = false;
  let pendingX = null;
  let pendingY = null;

  for (let index = 0; index < lines.length - 1; index += 2) {
    const code = lines[index].trim();
    const value = lines[index + 1];

    // Section bookkeeping: "2 / ENTITIES" opens, "0 / ENDSEC" closes.
    if (code === "2") {
      inEntities = value.trim() === "ENTITIES";
      continue;
    }
    if (code === "0" && value.trim() === "ENDSEC") {
      inEntities = false;
      continue;
    }
    if (!inEntities) continue;

    if (code === "10") pendingX = parseFloat(value);
    else if (code === "20") pendingY = parseFloat(value);
    else if (code === "30" && pendingX !== null && pendingY !== null) {
      xs.push(pendingX);
      ys.push(pendingY);
      zs.push(parseFloat(value));
      pendingX = null;
      pendingY = null;
    }
  }

  // Even stride rather than a head slice, so a decimated preview still shows
  // the whole subject instead of whichever corner was written first.
  const stride = maxPoints > 0 ? Math.max(1, Math.ceil(xs.length / maxPoints)) : 1;
  const kept = Math.ceil(xs.length / stride);
  const positions = new Float32Array(kept * 3);

  for (let source = 0, target = 0; source < xs.length; source += stride, target += 1) {
    positions[target * 3] = xs[source];
    positions[target * 3 + 1] = ys[source];
    positions[target * 3 + 2] = zs[source];
  }

  return { positions, total: xs.length, shown: kept };
}

/**
 * The engraving material, matched to what the laser actually does.
 *
 * Each dot is a microfracture that scatters light outward, so the right model
 * is additive emission, not a lit surface. Additive also composites correctly
 * when dots stack along the view axis - denser regions genuinely get
 * brighter, which is the whole mechanism behind toning.
 */
function engravingMaterial(THREE, mode, pointSize) {
  const shared = {
    vertexColors: true,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
    transparent: true,
  };
  return mode === "surface"
    ? new THREE.MeshBasicMaterial({ ...shared, side: THREE.DoubleSide })
    : new THREE.PointsMaterial({ ...shared, size: pointSize, sizeAttenuation: true });
}

/**
 * The blank itself.
 *
 * ior 1.5168 is K9 optical glass; `dispersion` splits that index across
 * wavelengths and puts the faint rainbow on the chamfers. Without an
 * environment map every one of these numbers renders as flat black, which is
 * the single most common way this material gets misconfigured.
 */
function glassMaterial(THREE, depthMm) {
  return new THREE.MeshPhysicalMaterial({
    color: 0xffffff,
    metalness: 0,
    roughness: 0.02,
    transmission: 1,
    thickness: depthMm,
    ior: 1.5168,
    dispersion: 0.28,
    clearcoat: 1,
    clearcoatRoughness: 0.02,
    // A very slight cool cast over a long distance. Real K9 is close to
    // colourless; anything stronger reads as acrylic.
    attenuationColor: new THREE.Color(0xdceaf2),
    attenuationDistance: depthMm * 14,
    specularIntensity: 1,
    envMapIntensity: 1.15,
    side: THREE.FrontSide,
  });
}

/** White vertex colours, so additive blending has something to blend. */
function whiteColors(THREE, geometry) {
  if (geometry.getAttribute("color")) return;
  const count = geometry.getAttribute("position").count;
  geometry.setAttribute("color", new THREE.BufferAttribute(new Float32Array(count * 3).fill(1), 3));
}

export default function CrystalPreview({
  src,
  kind,
  blank = { width: 60, height: 80, depth: 40 },
  // A GLB of the real blank, imported from Cockpit 3D by import_blanks.py.
  // Hearts, ornaments and the Prestige shapes are not boxes at all, so the
  // chamfered-box fallback below is only right for the rectangular sizes.
  blankModel = null,
  // Millimetres, from the blank's own BEVEL field when it documents one.
  bevel = CHAMFER_MM,
  border = 1,
  mode = "points",
  pointSize = PREVIEW_DOT_SIZE_MM,
  maxPoints = 400000,
  autoRotate = true,
  showGlass = true,
  className = "",
}) {
  const hostRef = useRef(null);
  const [status, setStatus] = useState("loading");
  const [error, setError] = useState(null);
  const [detail, setDetail] = useState(null);

  // Live controls must not tear the WebGL context down and rebuild it, so the
  // render loop reads them from a ref the effect below keeps current.
  const settings = useRef({ mode, pointSize, autoRotate, showGlass });
  useEffect(() => {
    settings.current = { mode, pointSize, autoRotate, showGlass };
  }, [mode, pointSize, autoRotate, showGlass]);

  useEffect(() => {
    const host = hostRef.current;
    if (!host || !src) return undefined;

    const resolvedKind = kind || inferKind(src);
    let disposed = false;
    const cleanups = [];

    setStatus("loading");
    setError(null);
    setDetail(null);

    // three and its example modules all touch `window`, so they are imported
    // inside the effect rather than at module scope where the server render
    // would fail on them - the same reason ModelViewer.jsx defers its import.
    (async () => {
      const THREE = await import("three");
      const { OrbitControls } = await import("three/examples/jsm/controls/OrbitControls.js");
      const { RoomEnvironment } = await import("three/examples/jsm/environments/RoomEnvironment.js");
      const { RoundedBoxGeometry } = await import("three/examples/jsm/geometries/RoundedBoxGeometry.js");
      if (disposed) return;

      // ── Renderer ─────────────────────────────────────────────────────────
      const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
      renderer.toneMapping = THREE.ACESFilmicToneMapping;
      renderer.toneMappingExposure = 1.15;
      renderer.outputColorSpace = THREE.SRGBColorSpace;
      host.appendChild(renderer.domElement);
      cleanups.push(() => {
        renderer.dispose();
        renderer.domElement.remove();
      });

      const scene = new THREE.Scene();
      scene.background = new THREE.Color(0x05070a);

      // ── Lighting ─────────────────────────────────────────────────────────
      // Transmission samples the environment, so an env map is not optional
      // decoration here - it is what the glass is made of.
      const pmrem = new THREE.PMREMGenerator(renderer);
      const environment = pmrem.fromScene(new RoomEnvironment(), 0.04);
      scene.environment = environment.texture;
      cleanups.push(() => {
        environment.texture.dispose();
        pmrem.dispose();
      });

      // One hard key light over the soft room, for the specular streak along
      // the chamfer that says "polished" rather than "frosted".
      const key = new THREE.DirectionalLight(0xffffff, 2.2);
      key.position.set(1, 1.4, 1.2);
      scene.add(key);

      // ── Camera and controls ──────────────────────────────────────────────
      const diagonal = Math.hypot(blank.width, blank.height, blank.depth);
      const camera = new THREE.PerspectiveCamera(32, 1, diagonal * 0.05, diagonal * 40);
      camera.position.set(diagonal * 0.38, diagonal * 0.22, diagonal * 1.12);

      const controls = new OrbitControls(camera, renderer.domElement);
      controls.enableDamping = true;
      controls.dampingFactor = 0.06;
      controls.minDistance = diagonal * 0.62;
      controls.maxDistance = diagonal * 4;
      controls.autoRotateSpeed = 1.1;
      // Touch: one finger orbits, two pinch-zoom and pan. Vertical page
      // scrolling is deliberately given up inside the canvas, because a
      // one-finger drag has to mean rotate for the gesture to be discoverable.
      controls.touches = { ONE: THREE.TOUCH.ROTATE, TWO: THREE.TOUCH.DOLLY_PAN };
      controls.target.set(0, 0, 0);
      cleanups.push(() => controls.dispose());

      // ── The blank ────────────────────────────────────────────────────────
      /*
       * A real imported shape when one exists, otherwise a chamfered box.
       * import_blanks.py has already fitted the mesh to the template's
       * millimetres and centred it, so it drops straight in with no transform.
       */
      let glassGeometry = null;
      if (blankModel) {
        try {
          const { GLTFLoader } = await import("three/examples/jsm/loaders/GLTFLoader.js");
          const shape = await new GLTFLoader().loadAsync(blankModel);
          if (disposed) return;
          shape.scene.traverse((child) => {
            if (!glassGeometry && child.isMesh) glassGeometry = child.geometry;
          });
        } catch {
          // A missing or unreadable blank must not take the whole preview
          // down - the box below is a perfectly usable stand-in.
        }
      }
      if (!glassGeometry) {
        glassGeometry = new RoundedBoxGeometry(
          blank.width,
          blank.height,
          blank.depth,
          1, // one segment turns the rounding into a flat chamfer
          Math.min(bevel, blank.width / 2, blank.height / 2, blank.depth / 2),
        );
      }
      const glass = new THREE.Mesh(glassGeometry, glassMaterial(THREE, blank.depth));
      scene.add(glass);
      cleanups.push(() => {
        glassGeometry.dispose();
        glass.material.dispose();
      });

      // ── The contents ─────────────────────────────────────────────────────
      let engraving = null;
      let swappable = false; // only geometry with faces can switch to surface

      try {
        if (resolvedKind === "glb") {
          const { GLTFLoader } = await import("three/examples/jsm/loaders/GLTFLoader.js");
          const gltf = await new GLTFLoader().loadAsync(src);
          if (disposed) return;

          let geometry = null;
          gltf.scene.traverse((child) => {
            if (!geometry && child.isMesh) geometry = child.geometry;
          });
          if (!geometry) throw new Error("That GLB contains no mesh.");

          /*
           * Points and surface share one BufferGeometry on purpose. A relief
           * is already a dense regular grid, so its vertices ARE the dot
           * field - no resampling, and switching modes cannot drift the two
           * views out of agreement about where the geometry is.
           */
          whiteColors(THREE, geometry);
          swappable = true;
          engraving = new THREE.Points(
            geometry,
            engravingMaterial(THREE, settings.current.mode, settings.current.pointSize),
          );
          setDetail(`${geometry.getAttribute("position").count.toLocaleString()} vertices`);
        } else if (resolvedKind === "dxf") {
          const response = await fetch(src);
          if (!response.ok) throw new Error(`Could not fetch that DXF (${response.status}).`);
          const { positions, total, shown } = parseDxfPoints(await response.text(), maxPoints);
          if (disposed) return;
          if (!total) throw new Error("That DXF contains no POINT entities.");

          const geometry = new THREE.BufferGeometry();
          geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
          // The cloud is already centred on the origin in millimetres by
          // printer_dxf.py, so it needs no transform - it lands in the blank
          // exactly where the engraver will put it.
          whiteColors(THREE, geometry);
          engraving = new THREE.Points(
            geometry,
            engravingMaterial(THREE, "points", settings.current.pointSize),
          );
          setDetail(
            shown < total
              ? `${shown.toLocaleString()} of ${total.toLocaleString()} dots`
              : `${total.toLocaleString()} dots`,
          );
        } else {
          // A flat photograph suspended mid-glass: the plain 2D engraving, and
          // what the customer sees before any depth work has happened.
          const texture = await new THREE.TextureLoader().loadAsync(src);
          if (disposed) return;
          texture.colorSpace = THREE.SRGBColorSpace;

          const usableWidth = blank.width - 2 * border;
          const usableHeight = blank.height - 2 * border;
          const aspect = texture.image.width / texture.image.height;
          const [planeWidth, planeHeight] =
            usableWidth / usableHeight > aspect
              ? [usableHeight * aspect, usableHeight]
              : [usableWidth, usableWidth / aspect];

          const geometry = new THREE.PlaneGeometry(planeWidth, planeHeight);
          engraving = new THREE.Mesh(
            geometry,
            new THREE.MeshBasicMaterial({
              map: texture,
              blending: THREE.AdditiveBlending,
              depthWrite: false,
              transparent: true,
              side: THREE.DoubleSide,
            }),
          );
          cleanups.push(() => texture.dispose());
          setDetail(`${planeWidth.toFixed(1)} × ${planeHeight.toFixed(1)} mm`);
        }

        scene.add(engraving);
        cleanups.push(() => {
          engraving?.geometry.dispose();
          engraving?.material.dispose();
        });
        setStatus("ready");
      } catch (loadError) {
        setError(loadError?.message || "That file could not be read.");
        setStatus("failed");
      }

      // ── Sizing ───────────────────────────────────────────────────────────
      const resize = () => {
        const { clientWidth, clientHeight } = host;
        if (!clientWidth || !clientHeight) return;
        renderer.setSize(clientWidth, clientHeight, false);
        camera.aspect = clientWidth / clientHeight;
        camera.updateProjectionMatrix();
      };
      resize();
      const observer = new ResizeObserver(resize);
      observer.observe(host);
      cleanups.push(() => observer.disconnect());

      // ── Loop ─────────────────────────────────────────────────────────────
      let frame = 0;
      let renderedMode = settings.current.mode;

      const tick = () => {
        frame = requestAnimationFrame(tick);
        const current = settings.current;

        controls.autoRotate = current.autoRotate;
        glass.visible = current.showGlass;

        if (engraving && swappable && current.mode !== renderedMode) {
          // Rebuilding only the wrapper keeps the geometry and its GPU
          // buffers exactly where they are.
          const geometry = engraving.geometry;
          scene.remove(engraving);
          engraving.material.dispose();
          engraving =
            current.mode === "surface"
              ? new THREE.Mesh(geometry, engravingMaterial(THREE, "surface", 0))
              : new THREE.Points(geometry, engravingMaterial(THREE, "points", current.pointSize));
          scene.add(engraving);
          renderedMode = current.mode;
        } else if (engraving?.material.isPointsMaterial) {
          engraving.material.size = current.pointSize;
        }

        controls.update();
        renderer.render(scene, camera);
      };
      tick();
      cleanups.push(() => cancelAnimationFrame(frame));
    })().catch((setupError) => {
      if (disposed) return;
      setError(setupError?.message || "The 3D viewer could not start.");
      setStatus("failed");
    });

    return () => {
      disposed = true;
      // Reverse order, so the loop stops before the things it renders go away.
      for (const cleanup of cleanups.reverse()) {
        try {
          cleanup();
        } catch {
          // A context already lost to a tab switch throws here; nothing to do.
        }
      }
    };
    // blank is read once when the scene is built; changing it rebuilds, which
    // is correct - a different blank is a different scene.
  }, [src, kind, blank.width, blank.height, blank.depth, blankModel, bevel, border, maxPoints]);

  return (
    <div className={`${FRAME} ${className}`}>
      <div ref={hostRef} className="absolute inset-0" />

      {status !== "ready" ? (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center p-6">
          <p
            className={`text-center font-mono text-xs ${
              status === "failed" ? "text-warning-text" : "text-console-muted"
            }`}
          >
            {status === "failed" ? error : "building the crystal…"}
          </p>
        </div>
      ) : null}

      <p className="pointer-events-none absolute bottom-2 left-3 font-mono text-[10px] text-console-muted">
        drag to orbit · scroll to zoom{detail ? ` · ${detail}` : ""}
      </p>
    </div>
  );
}
