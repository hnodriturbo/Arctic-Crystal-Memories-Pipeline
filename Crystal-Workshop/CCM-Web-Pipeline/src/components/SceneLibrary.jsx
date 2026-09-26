"use client";
/** Purpose: A compact folder and file chooser for the private Cockpit scene library. */
import { useEffect, useState } from 'react';

export default function SceneLibrary({ disabled, onPair, onSelectionChange }) {
  const [folders, setFolders] = useState([]);
  const [folder, setFolder] = useState('');
  const [exportKey, setExportKey] = useState('');
  const [sceneKey, setSceneKey] = useState('');
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');
  async function refresh() {
    onSelectionChange?.();
    setBusy(true);
    try {
      const response = await fetch('/api/reconstruct/scenes');
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Sign in to load scenes.');
      setFolders(data.folders); setNotice('');
    } catch (error) { setNotice(error.message); }
    finally { setBusy(false); }
  }
  useEffect(() => {
    const controller = new AbortController();
    fetch('/api/reconstruct/scenes', { signal: controller.signal })
      .then(async (response) => { const data = await response.json(); if (!response.ok) throw new Error(data.error || 'Sign in to load scenes.'); return data; })
      .then((data) => setFolders(data.folders))
      .catch((error) => { if (error.name !== 'AbortError') setNotice(error.message); });
    return () => controller.abort();
  }, []);
  async function loadPair() {
    setBusy(true); setNotice('Loading the selected pair from R2…');
    try {
      const response = await fetch('/api/reconstruct/scenes', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ exportKey, sceneKey }) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Could not load scene.');
      await onPair(data); setNotice('Scene pair ready. Every DXF point will be used with the approved defaults.');
    } catch (error) { setNotice(error.message); }
    finally { setBusy(false); }
  }
  const selected = folders.find((item) => item.id === folder);
  return <section className="space-y-4 rounded-2xl border border-accent/25 bg-gradient-to-br from-accent-soft/40 to-surface p-5">
    <div className="flex items-center justify-between gap-3"><div><h2 className="font-semibold">Scene library</h2><p className="mt-1 text-xs text-muted">Private R2 · Cockpit3D-Files</p></div><button type="button" aria-label="Refresh scene folders" disabled={busy || disabled} onClick={refresh} className="rounded-lg border border-surface-border p-2 hover:border-accent">↻</button></div>
    <div className="flex gap-2 overflow-x-auto pb-2">{folders.map((item) => <button type="button" disabled={disabled || busy} aria-pressed={folder === item.id} key={item.id} onClick={() => { onSelectionChange?.(); setFolder(item.id); setExportKey(''); setSceneKey(''); setNotice(''); }} className={`flex min-w-40 flex-col gap-2 rounded-xl border p-3 text-left text-xs transition ${folder === item.id ? 'border-accent bg-accent-soft text-accent-soft-text' : 'border-surface-border bg-surface hover:border-accent/60'}`}><span aria-hidden="true" className="text-xl">▱</span><span className="font-medium">{item.id}</span><span className="text-muted">{item.files.length} files</span></button>)}</div>
    {selected && <div className="grid gap-5 md:grid-cols-2">
      <label className="space-y-2 text-sm font-medium"><span>01 · Cockpit scene</span><select className="w-full rounded-xl border border-input-border bg-input-background p-3" value={sceneKey} disabled={disabled || busy} onChange={event => { onSelectionChange?.(); setSceneKey(event.target.value); setExportKey(''); }}><option value="">Choose the saved Cockpit scene…</option>{selected.files.filter(file => file.extension === '.cockpit').map(file => <option key={file.key} value={file.key}>{file.relative}</option>)}</select></label>
      <label className="space-y-2 text-sm font-medium"><span>02 · Matching DXF / CAD</span><select className="w-full rounded-xl border border-input-border bg-input-background p-3 disabled:opacity-40" value={exportKey} disabled={disabled || busy || !sceneKey} onChange={event => { onSelectionChange?.(); setExportKey(event.target.value); }}><option value="">{sceneKey ? 'Choose the matching export…' : 'Choose a Cockpit scene first'}</option>{selected.files.filter(file => ['.dxf','.cad'].includes(file.extension)).map(file => <option key={file.key} value={file.key}>{file.relative} · {(file.bytes/1048576).toFixed(1)} MB</option>)}</select></label>
    </div>}
    <p className="text-xs leading-5 text-muted">Choose the saved scene first, then its exact export. Run the desktop R2 sync shortcut after editing files, then refresh this library.</p>
    <button type="button" disabled={disabled || busy || !exportKey || !sceneKey} onClick={loadPair} className="w-full rounded-xl bg-accent px-4 py-3 text-sm font-semibold text-accent-foreground disabled:opacity-40">{busy ? 'Loading…' : 'Use selected scene pair'}</button>
    {notice && <p role="status" className="text-xs leading-5 text-muted-strong">{notice}</p>}
  </section>;
}
