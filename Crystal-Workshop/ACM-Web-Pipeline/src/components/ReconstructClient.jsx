"use client";

/**
 * Purpose: A dedicated operator workspace for exported Cockpit reliefs.
 * Reuses the operation fields, streaming log and GLB viewer used by the pipelines.
 */
import { useEffect, useRef, useState } from "react";
import ModelViewer from "@/components/ModelViewer";
import OptionFields from "@/components/OptionFields";
import ConsoleLog from "@/components/ConsoleLog";
import SceneLibrary from "@/components/SceneLibrary";
import { RECONSTRUCT } from "@/lib/operations";
import { readSse } from "@/lib/read-sse";
import { readResponseJson } from "@/lib/response-json";

const CARD = "rounded-2xl border border-surface-border bg-surface p-5 sm:p-6";
const GROUPS = [
  {id:"pose",label:"Cockpit projection pose",hint:"Saved scene values are used automatically. Overrides describe the DXF export pose, not an extra viewer rotation."},
  { id: "density", label: "Surface detail", hint: "The approved defaults use every point in the export." },
  { id: "output", label: "Shape and color", hint: "A paired photo adds color. Preview the alignment before keeping a result." },
];
const fileUrl = (file, download = false) => `/api/file?root=converter-output&path=${encodeURIComponent(file)}${download ? "&download=1" : ""}`;
const mb = (bytes) => `${(bytes / 1048576).toFixed(1)} MB`;

export default function ReconstructClient({ onSendToConverter }) {
  const inputs = [];
  const [source, setSource] = useState("");
  const [values, setValues] = useState(() => Object.fromEntries(RECONSTRUCT.fields.map((field) => [field.name, field.default])));
  const [running, setRunning] = useState(false);
  const uploading = false;
  const [notice, setNotice] = useState(null);
  const [publishing, setPublishing] = useState(false);
  const [sceneFolder, setSceneFolder] = useState('');
  const [resultSceneFolder, setResultSceneFolder] = useState('');
  const [lines, setLines] = useState([]);
  const [job, setJob] = useState(null);
  const [preview, setPreview] = useState(null);
  const [savedKey, setSavedKey] = useState(null);
  const abortRef = useRef(null);
  useEffect(() => () => abortRef.current?.abort(), []);

  async function run() {
    const controller = new AbortController();
    abortRef.current = controller;
    setRunning(true);
    setLines([]);
    setNotice(null);
    try {
      const response = await fetch("/api/reconstruct", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ file: source, values }), signal: controller.signal });
      if (!response.ok) throw new Error((await readResponseJson(response)).error || "Reconstruction failed.");
      await readSse(response, (event) => {
        if (event.type === "result") {
          setJob(event.job);
          setResultSceneFolder(sceneFolder);
          setPreview(event.job.files.glb);
          setSavedKey(null);
          setNotice("GLB is ready in the working area. Download it, save it to R2, or send it to the converter.");
        } else {
          setLines((current) => [...current.slice(-499), { type: event.type, text: event.line ?? event.message ?? (event.code === 0 ? "Finished." : "Reconstruction failed.") }]);
          if (event.type === "error") setNotice(event.message);
        }
      });
    } catch (error) { setNotice(error.name === "AbortError" ? "Reconstruction stopped." : error.message); }
    finally { setRunning(false); abortRef.current = null; }
  }

  // Publish into the private library; publishing never automatically exposes a customer exhibit.
  async function publish() {
    setPublishing(true);
    try {
      const response = await fetch('/api/reconstruct/publish', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({file:preview, sceneFolder: job?.files.glb === preview ? resultSceneFolder : sceneFolder})});
      const result = await readResponseJson(response);
      if (!response.ok) throw new Error(result.error || 'R2 publication failed.');
      setSavedKey(result.key);
      setNotice('Vistað á R2: ' + result.key + '. Veldu módelið í showroom-admin til að birta það.');
    } catch (error) {setNotice(error.message);} finally {setPublishing(false);}
  }
  async function sendToConverter() {
    setPublishing(true);
    try {
      const response = await fetch('/api/handoff', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({from:'converter-output',to:'converter-input',path:preview})});
      const data = await readResponseJson(response);
      if (!response.ok) throw new Error(data.error || 'Handoff failed.');
      onSendToConverter?.(data);
    } catch(error) { setNotice(error.message); } finally { setPublishing(false); }
  }
  return (
    <div className="space-y-6">
      <header className="relative overflow-hidden rounded-2xl border border-accent/25 bg-gradient-to-br from-accent-soft via-surface to-surface p-6 sm:p-8">
        <p className="mb-3 text-xs font-semibold uppercase tracking-[0.2em] text-accent-soft-text">Cockpit exports → surfaces</p>
        <h1 className="text-3xl font-semibold tracking-tight">Cockpit Reconstruct</h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-muted-strong">Choose your point export and its original Cockpit scene, then create a textured GLB.</p>
        <div className="mt-5 flex flex-wrap gap-2 text-xs text-muted-strong">{["01 · Choose Cockpit scene", "02 · Choose matching DXF", "03 · Create GLB"].map((label) => <span key={label} className="rounded-full border border-surface-border bg-surface/80 px-3 py-1.5">{label}</span>)}</div>
      </header>
      {notice && <p role="status" className="rounded-xl border border-surface-border bg-surface px-5 py-4 text-sm">{notice}</p>}
      <div className="space-y-6">
        <div className="min-w-0 space-y-5">
          <SceneLibrary onSelectionChange={() => { setSource(''); setNotice('Selection changed. Load the selected scene pair before creating a GLB.'); }} disabled={running || uploading} onPair={async (pair) => {
            setSource(pair.file);
            setSceneFolder(pair.sceneFolder);
            setValues((current) => ({ ...current, texture_from: pair.texture, pose_override:false, ...Object.fromEntries(["rotation", "position"].flatMap(kind => [..."xyz"].map((axis, index) => [`pose_${kind}_${axis}`, pair.pose?.[kind === "rotation" ? "Eulers" : "Position"]?.[index] || 0]))) }));
            setNotice('R2 scene pair loaded. Saved rotation: ' + (pair.pose?.Eulers || [0,0,0]).join(', ') + ' degrees; position: ' + (pair.pose?.Position || [0,0,0]).join(', ') + ' mm.');
          }} />
          <section className={CARD}>
            <h2 className="text-base font-semibold">Create GLB</h2>
            <p className="mt-2 text-xs leading-5 text-muted">Original relief settings · full photo texture · no lower-body repair</p>
            <details className="mt-4 rounded-xl border border-surface-border p-4">
              <summary className="cursor-pointer text-sm font-medium">Advanced settings</summary>
              <fieldset disabled={running || uploading} className="mt-5 min-w-0 disabled:opacity-60"><OptionFields fields={RECONSTRUCT.fields.filter((field) => !["texture_from", "repair_lower", "lower_repair_strength"].includes(field.name)).map(field => ({...field, helpHref: "#help-" + field.name}))} groups={GROUPS} values={values} onChange={setValues} inputs={inputs} /></fieldset>
            </details>
            <div className="mt-6 flex gap-3 border-t border-surface-border pt-5">
              <button disabled={!source || !values.texture_from || running || uploading} onClick={run} className="flex-1 rounded-xl bg-accent px-5 py-3 text-sm font-semibold text-accent-foreground transition hover:bg-accent-hover disabled:opacity-40">{running ? "Creating GLB…" : "Create GLB"}</button>
              {running && <button onClick={() => abortRef.current?.abort()} className="rounded-xl border border-surface-border px-4 text-sm">Stop</button>}
            </div>
          </section>
        </div>
        <div className="min-w-0 space-y-5">
          <section className={`${CARD} space-y-4`}>
            <div className="flex items-center justify-between"><h2 className="text-base font-semibold">03 · 2.5D Model Preview</h2><span className="rounded-full bg-accent-soft px-3 py-1 text-xs text-accent-soft-text">{running ? "Building…" : preview ? "Ready to review" : "Awaiting export"}</span></div>
            {preview ? <ModelViewer key={preview} src={fileUrl(preview)} alt="Reconstructed Cockpit relief surface" aspectClassName="h-[min(65vh,680px)] min-h-80" /> : <div className="flex h-[min(65vh,680px)] min-h-80 flex-col items-center justify-center rounded-xl border border-surface-border bg-gradient-to-b from-surface-sunken to-surface p-8 text-center"><div aria-hidden="true" className="mb-6 flex h-24 w-24 rotate-12 items-center justify-center rounded-3xl border border-accent/30 bg-accent-soft text-4xl text-accent-soft-text shadow-lg">◇</div><h3 className="text-lg font-medium">Your piece, reconstructed</h3><p className="mt-2 max-w-xs text-sm leading-6 text-muted">Choose an exported point cloud and build a surface. The rotating model will appear here.</p></div>}
            {job && preview === job.files.glb && <div className="grid grid-cols-3 gap-3">{[[job.vertices.toLocaleString(), "vertices"], [job.triangles.toLocaleString(), "triangles"], [mb(job.glbBytes), "GLB size"]].map(([value, label]) => <div key={label} className="rounded-lg bg-surface-sunken p-3"><p className="text-sm font-semibold sm:text-lg">{value}</p><p className="text-xs text-muted">{label}</p></div>)}</div>}
            {preview && <div className="flex flex-wrap gap-2"><a className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-foreground" href={savedKey ? "/api/r2/browser?download=" + encodeURIComponent(savedKey) : fileUrl(preview, true)}>Download GLB</a><button disabled={publishing || running} onClick={publish} className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-foreground disabled:opacity-40">{publishing ? "Vista á R2…" : "Vista á R2 Cloudflare"}</button><button disabled={publishing || running} onClick={sendToConverter} className="rounded-lg border border-accent/40 px-4 py-2 text-sm disabled:opacity-40">Send to converter</button>{job && preview === job.files.glb && ["stl", "report"].map((kind) => <a key={kind} className="rounded-lg border border-surface-border px-4 py-2 text-sm hover:border-accent" href={fileUrl(job.files[kind], true)}>Download {kind.toUpperCase()}</a>)}</div>}
            <p className="text-xs leading-5 text-muted">Temporary working files expire after seven days when the workspace next creates a job. Save to R2 to keep the result. Review the silhouette, depth and photo alignment. Continuous relief estimates the surface before laser sampling; it does not recover the original hidden mesh.</p>
          </section>
          <details className={CARD}><summary className="cursor-pointer text-sm font-medium">Processing log{running ? " · running" : ""}</summary><div className="mt-4"><ConsoleLog lines={lines} running={running} /></div></details>
        </div>
      </div>
      <section className={CARD}><h2 className="text-lg font-semibold">Advanced settings explained</h2><div className="mt-5 grid gap-5 md:grid-cols-2">{RECONSTRUCT.fields.filter(field => !['texture_from','repair_lower','lower_repair_strength'].includes(field.name)).map(field => <article key={field.name} id={'help-' + field.name} tabIndex={-1} className="scroll-mt-28 rounded-xl bg-surface-sunken p-4"><h3 className="font-medium">{field.label}</h3><p className="mt-2 text-sm text-muted-strong">{field.help || field.label}</p><p className="mt-2 text-xs text-accent">Recommended: {field.name.startsWith("pose_") && field.name !== "pose_override" ? "Use the saved scene value" : String(field.default)}</p></article>)}</div></section>
    </div>
  );
}
