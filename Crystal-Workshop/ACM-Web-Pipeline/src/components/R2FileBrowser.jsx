"use client";
/** Purpose: Shared, folder-based R2 browsing for Workshop and converter inputs. */
import { useEffect, useState } from 'react';
import { STORAGE_AREAS } from '@/lib/storage/browser-scope';
const SUPPORTED = /\.(glb|gltf|blend|obj|dxf|cad|xyz|ply|stl|cockpit|fbx|dae|usd|usda|usdc|usdz)$/i;

export default function R2FileBrowser({ onUse }) {
  const [prefix, setPrefix] = useState('Cockpit3D-Files/');
  const [listing, setListing] = useState({ folders: [], files: [] });
  const [refresh, setRefresh] = useState(0);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');
  const sceneFolder = prefix.startsWith('Cockpit3D-Files/') && /^\d+-[a-zA-Z0-9_-]+$/.test(prefix.split('/')[1]) ? prefix.split('/')[1] : '';
  useEffect(() => {
    const controller = new AbortController();
    fetch('/api/r2/browser?prefix=' + encodeURIComponent(prefix), { signal: controller.signal, cache: 'no-store' })
      .then(async response => { const data = await response.json(); if (!response.ok) throw new Error(data.error || 'Sign in to read R2.'); return data; })
      .then(data => { setListing(data); setNotice(''); })
      .catch(error => { if (error.name !== 'AbortError') setNotice(error.message); });
    return () => controller.abort();
  }, [prefix, refresh]);
  async function importFile(key) {
    setBusy(true); setNotice('Downloading a working copy from R2…');
    try {
      const response = await fetch('/api/r2/import', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ key }) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Import failed.');
      onUse?.(data); setNotice('Selected file is ready in the converter.');
    } catch (error) { setNotice(error.message); }
    finally { setBusy(false); }
  }
  async function uploadEditedModel(file) {
    if (!file || !sceneFolder) return;
    setBusy(true); setNotice('Uploading the edited GLB to its scene folder…');
    try {
      if (file.size > 64 * 1024 * 1024) throw new Error('This upload supports GLB files up to 64 MB.');
      const response = await fetch('/api/reconstruct/upload', { method: 'POST', headers: { 'Content-Type': 'model/gltf-binary', 'x-filename': encodeURIComponent(file.name), 'x-scene-folder': sceneFolder }, body: file });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Upload failed.');
      setRefresh(value => value + 1); setNotice('Saved to R2. Choose Use in converter to create DXF.');
    } catch (error) { setNotice(error.message); }
    finally { setBusy(false); }
  }
  return <section className="space-y-4 rounded-2xl border border-surface-border bg-surface p-5">
    <div className="flex flex-wrap items-center justify-between gap-3"><h2 className="text-lg font-semibold">R2 File Browser</h2><button onClick={() => setRefresh(value => value + 1)} className="rounded-lg border border-surface-border px-4 py-2">↻ Refresh</button></div>
    <select aria-label="Storage area" className="w-full rounded-lg border border-input-border bg-input-background p-3" value={STORAGE_AREAS.find(area => prefix.startsWith(area.prefix))?.prefix} onChange={event => { setListing({ folders: [], files: [] }); setPrefix(event.target.value); }}>{STORAGE_AREAS.map(area => <option key={area.prefix} value={area.prefix}>{area.label}</option>)}</select>
    <nav aria-label="R2 folder path" className="flex flex-wrap gap-2 text-sm">{prefix.split('/').filter(Boolean).map((part, index, parts) => <button key={index} className="break-all text-accent hover:underline" onClick={() => setPrefix(parts.slice(0, index + 1).join('/') + '/')}>{part} /</button>)}</nav>
    {sceneFolder ? <label className="inline-flex cursor-pointer rounded-lg border border-accent/40 bg-accent-soft px-4 py-3 text-sm">Upload GLB from Blender to R2<input type="file" accept=".glb" disabled={busy} className="sr-only" onChange={event => { uploadEditedModel(event.target.files?.[0]); event.target.value = ''; }} /></label> : <p className="text-xs text-muted">Open a numbered Cockpit scene folder to upload an edited Blender GLB into that folder.</p>}
    <div className="max-h-[32rem] space-y-2 overflow-auto">
      {listing.folders.map(folder => <button key={folder} className="block w-full rounded-lg border border-surface-border p-3 text-left" onClick={() => { setListing({ folders: [], files: [] }); setPrefix(folder); }}>▱ {folder.slice(prefix.length)}</button>)}
      {listing.files.map(file => <div key={file.key} className="flex flex-wrap items-center gap-3 rounded-lg bg-surface-sunken p-3"><span className="min-w-0 flex-1 break-all text-sm">{file.name}<small className="block text-muted">{(file.bytes / 1048576).toFixed(1)} MB</small></span><a className="text-sm text-accent" href={'/api/r2/browser?download=' + encodeURIComponent(file.key)}>Download</a>{onUse && SUPPORTED.test(file.name) && <button disabled={busy} className="rounded-lg border border-accent/40 px-3 py-2 text-sm disabled:opacity-40" onClick={() => importFile(file.key)}>Use in converter</button>}</div>)}
    </div>
    <p role="status" className="text-sm text-muted">{notice || 'R2 originals remain unchanged. Downloads are served directly from Cloudflare.'}</p>
  </section>;
}
