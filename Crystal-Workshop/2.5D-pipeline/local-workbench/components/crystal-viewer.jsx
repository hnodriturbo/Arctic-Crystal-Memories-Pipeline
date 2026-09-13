/**
 * File: local-workbench/components/crystal-viewer.jsx
 * Purpose:
 *  - Display every mesh from a pipeline GLB inside a rotatable K9 glass blank.
 */

'use client';

import { useEffect, useRef, useState } from 'react';
import { Box, CircleDot, Glasses, Pause, Play, Rotate3D } from 'lucide-react';

const API_ROOT = 'http://127.0.0.1:8425';
const POINT_SIZE_MM = 0.09;
const DEFAULT_DEPTH_PERCENT = 18;

// Adds a white vertex-color buffer when an imported geometry has none.
function ensureColors(THREE, geometry) {
  if (geometry.getAttribute('color')) return;
  const count = geometry.getAttribute('position').count;
  geometry.setAttribute('color', new THREE.BufferAttribute(new Float32Array(count * 3).fill(1), 3));
}

// Collects every GLB mesh and applies its scene transform before crystal fitting.
function collectGeometries(THREE, root) {
  const geometries = [];
  root.updateMatrixWorld(true);
  root.traverse((child) => {
    if (!child.isMesh || !child.geometry?.getAttribute('position')) return;
    const geometry = child.geometry.clone();
    geometry.applyMatrix4(child.matrixWorld);
    ensureColors(THREE, geometry);
    if (!geometry.getAttribute('normal')) geometry.computeVertexNormals();
    geometries.push(geometry);
  });
  return geometries;
}

// Fits the image plane while leaving Z available for a separate physical-depth control.
function fitGeometries(THREE, geometries, blank) {
  const bounds = new THREE.Box3();
  geometries.forEach((geometry) => {
    geometry.computeBoundingBox();
    bounds.union(geometry.boundingBox);
  });
  const center = bounds.getCenter(new THREE.Vector3());
  const size = bounds.getSize(new THREE.Vector3());
  const usable = { width: blank.width * 0.82, height: blank.height * 0.82 };
  const planarScale = Math.min(
    usable.width / Math.max(size.x, 0.001),
    usable.height / Math.max(size.y, 0.001),
  );
  geometries.forEach((geometry) => {
    geometry.translate(-center.x, -center.y, -center.z);
    geometry.scale(planarScale, planarScale, 1);
  });
  return Math.max(size.z, 0.001);
}

// Uses the optical values already proven in the ACM admin viewer.
function createGlassMaterial(THREE, depth) {
  return new THREE.MeshPhysicalMaterial({
    color: 0xf4fbff,
    metalness: 0,
    roughness: 0.025,
    transmission: 1,
    thickness: depth,
    ior: 1.5168,
    dispersion: 0.28,
    clearcoat: 1,
    clearcoatRoughness: 0.018,
    attenuationColor: new THREE.Color(0xcfe5ef),
    attenuationDistance: depth * 14,
    envMapIntensity: 1.2,
    transparent: true,
    depthWrite: false,
    side: THREE.FrontSide,
  });
}

// Owns the Three.js lifecycle while React owns only the visible review controls.
export default function CrystalViewer({ modelUrl, blank }) {
  const hostRef = useRef(null);
  const settingsRef = useRef({ mode: 'surface', autoRotate: true, showGlass: true, depthPercent: DEFAULT_DEPTH_PERCENT });
  const [mode, setMode] = useState('surface');
  const [autoRotate, setAutoRotate] = useState(true);
  const [showGlass, setShowGlass] = useState(true);
  const [depthPercent, setDepthPercent] = useState(DEFAULT_DEPTH_PERCENT);
  const [status, setStatus] = useState(modelUrl ? 'Hleð GLB…' : 'Veldu eða búðu til GLB');

  useEffect(() => {
    settingsRef.current = { mode, autoRotate, showGlass, depthPercent };
  }, [mode, autoRotate, showGlass, depthPercent]);

  useEffect(() => {
    const host = hostRef.current;
    if (!host || !blank) return undefined;
    let disposed = false;
    let frame = 0;
    const cleanups = [];

    (async () => {
      const THREE = await import('three');
      const { OrbitControls } = await import('three/examples/jsm/controls/OrbitControls.js');
      const { RoomEnvironment } = await import('three/examples/jsm/environments/RoomEnvironment.js');
      const { RoundedBoxGeometry } = await import('three/examples/jsm/geometries/RoundedBoxGeometry.js');
      const { GLTFLoader } = await import('three/examples/jsm/loaders/GLTFLoader.js');
      if (disposed) return;

      const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
      renderer.toneMapping = THREE.ACESFilmicToneMapping;
      renderer.toneMappingExposure = 1.08;
      renderer.outputColorSpace = THREE.SRGBColorSpace;
      renderer.domElement.className = 'viewer-canvas';
      host.appendChild(renderer.domElement);
      cleanups.push(() => { renderer.dispose(); renderer.domElement.remove(); });

      const scene = new THREE.Scene();
      scene.background = new THREE.Color(0x03080d);
      const pmrem = new THREE.PMREMGenerator(renderer);
      const environment = pmrem.fromScene(new RoomEnvironment(), 0.035);
      scene.environment = environment.texture;
      cleanups.push(() => { environment.texture.dispose(); pmrem.dispose(); });

      const keyLight = new THREE.DirectionalLight(0xffffff, 2.4);
      keyLight.position.set(1.2, 1.5, 1.4);
      const rimLight = new THREE.DirectionalLight(0x9be7ff, 1.4);
      rimLight.position.set(-1.4, 0.7, -1.1);
      scene.add(keyLight, rimLight);

      const diagonal = Math.hypot(blank.width, blank.height, blank.depth);
      const camera = new THREE.PerspectiveCamera(31, 1, diagonal * 0.04, diagonal * 45);
      camera.position.set(diagonal * 0.36, diagonal * 0.18, diagonal * 1.08);
      const controls = new OrbitControls(camera, renderer.domElement);
      controls.enableDamping = true;
      controls.dampingFactor = 0.065;
      controls.minDistance = diagonal * 0.58;
      controls.maxDistance = diagonal * 4;
      controls.autoRotateSpeed = 0.9;
      controls.addEventListener('start', () => setAutoRotate(false));
      cleanups.push(() => controls.dispose());

      let glass = null;
      if (!blank.noCrystal) {
        let glassGeometry;
        if (blank.hasModel) {
          try {
            const blankGltf = await new GLTFLoader().loadAsync(`${API_ROOT}/api/blanks/${blank.id}/model`);
            const [loaded] = collectGeometries(THREE, blankGltf.scene);
            glassGeometry = loaded;
          } catch {
            glassGeometry = null;
          }
        }
        if (!glassGeometry) {
          const bevel = Math.min(blank.bevel || 3, blank.width / 2, blank.height / 2, blank.depth / 2);
          glassGeometry = new RoundedBoxGeometry(blank.width, blank.height, blank.depth, 2, bevel);
        }
        glass = new THREE.Mesh(glassGeometry, createGlassMaterial(THREE, blank.depth));
        glass.renderOrder = 1;
        scene.add(glass);
        cleanups.push(() => { glassGeometry.dispose(); glass.material.dispose(); });
      }

      const surfaceGroup = new THREE.Group();
      const pointsGroup = new THREE.Group();
      let sourceDepth = 1;
      scene.add(surfaceGroup, pointsGroup);
      if (modelUrl) {
        try {
          const gltf = await new GLTFLoader().loadAsync(modelUrl);
          if (disposed) return;
          const geometries = collectGeometries(THREE, gltf.scene);
          if (!geometries.length) throw new Error('GLB inniheldur enga mesh geometry');
          sourceDepth = fitGeometries(THREE, geometries, blank);
          let vertexCount = 0;
          geometries.forEach((geometry) => {
            vertexCount += geometry.getAttribute('position').count;
            const surfaceMaterial = new THREE.MeshStandardMaterial({
              color: 0xffffff,
              vertexColors: true,
              side: THREE.DoubleSide,
              metalness: 0.01,
              roughness: 0.38,
              emissive: 0x07121a,
              emissiveIntensity: 0.16,
            });
            const pointMaterial = new THREE.PointsMaterial({
              color: 0xffffff,
              vertexColors: true,
              size: POINT_SIZE_MM,
              sizeAttenuation: true,
              blending: THREE.AdditiveBlending,
              depthWrite: false,
              transparent: true,
              opacity: 0.9,
            });
            const surface = new THREE.Mesh(geometry, surfaceMaterial);
            const points = new THREE.Points(geometry, pointMaterial);
            surface.renderOrder = 2;
            points.renderOrder = 3;
            surfaceGroup.add(surface);
            pointsGroup.add(points);
            cleanups.push(() => { geometry.dispose(); surfaceMaterial.dispose(); pointMaterial.dispose(); });
          });
          setStatus(`${vertexCount.toLocaleString('is-IS')} vertices · ${geometries.length} lög`);
        } catch (error) {
          setStatus(`GLB villa: ${error.message}`);
        }
      } else {
        setStatus('Veldu eða búðu til GLB');
      }

      const resizeObserver = new ResizeObserver(() => {
        const width = Math.max(1, host.clientWidth);
        const height = Math.max(1, host.clientHeight);
        renderer.setSize(width, height, false);
        camera.aspect = width / height;
        camera.updateProjectionMatrix();
      });
      resizeObserver.observe(host);
      cleanups.push(() => resizeObserver.disconnect());

      const render = () => {
        if (disposed) return;
        const settings = settingsRef.current;
        controls.autoRotate = settings.autoRotate;
        if (glass) glass.visible = settings.showGlass;
        surfaceGroup.visible = settings.mode === 'surface';
        pointsGroup.visible = settings.mode === 'points';
        const depthScale = blank.depth * (settings.depthPercent / 100) / sourceDepth;
        surfaceGroup.scale.z = depthScale;
        pointsGroup.scale.z = depthScale;
        controls.update();
        renderer.render(scene, camera);
        frame = window.requestAnimationFrame(render);
      };
      render();
    })().catch((error) => setStatus(`Viewer villa: ${error.message}`));

    return () => {
      disposed = true;
      window.cancelAnimationFrame(frame);
      cleanups.reverse().forEach((cleanup) => cleanup());
      host.replaceChildren();
    };
  }, [modelUrl, blank]);

  return (
    <section className="viewer-shell" aria-label="Skref 4 GLB output viewer">
      <div ref={hostRef} className="viewer-host" />
      <div className="viewer-badge"><Rotate3D size={15} /> Dragðu til að snúa · skrollaðu til að zooma</div>
      <div className="viewer-toolbar" aria-label="Viewer controls">
        <button type="button" className={mode === 'surface' ? 'tool-button active' : 'tool-button'} onClick={() => setMode('surface')}><Box size={15} /> Flötur</button>
        <button type="button" className={mode === 'points' ? 'tool-button active' : 'tool-button'} onClick={() => setMode('points')}><CircleDot size={15} /> Laser dots</button>
        {!blank.noCrystal && <button type="button" className={showGlass ? 'tool-button active' : 'tool-button'} onClick={() => setShowGlass((value) => !value)}><Glasses size={15} /> Kristall</button>}
        <button type="button" className={autoRotate ? 'tool-button active' : 'tool-button'} onClick={() => setAutoRotate((value) => !value)}>{autoRotate ? <Pause size={15} /> : <Play size={15} />} Snúningur</button>
        <label className="depth-control">Dýpt {depthPercent}%<input aria-label="Dýpt 2.5D módels" type="range" min="8" max="35" step="1" value={depthPercent} onChange={(event) => setDepthPercent(Number(event.target.value))} /></label>
      </div>
      <p className="viewer-status">{status}</p>
    </section>
  );
}
