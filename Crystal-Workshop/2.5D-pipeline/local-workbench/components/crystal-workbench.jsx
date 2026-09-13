/**
 * File: local-workbench/components/crystal-workbench.jsx
 * Purpose:
 *  - Coordinate crystal selection, local 2.5D jobs and the interactive GLB result viewer.
 */

'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { Activity, Check, ChevronRight, Cpu, FileImage, FolderClock, Gem, ImagePlus, Layers3, LoaderCircle, Play, Rotate3D, Scissors, Server, Sparkles, TriangleAlert, ZoomIn } from 'lucide-react';
import CrystalViewer from '@/components/crystal-viewer';
import { Button } from '@/components/ui/button';

/* oxlint-disable next/no-img-element -- The preview is a short-lived local blob URL, not a deployable image asset. */

const API_ROOT = 'http://127.0.0.1:8425';
const DEFAULT_BLANK = { id: 'fallback', name: 'Rectangle 120×80', width: 80, height: 120, depth: 60, family: 'rectangle', bevel: 5, hasModel: false };

// Converts the selected local image to the API's bounded JSON upload format.
function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(reader.error || new Error('Ekki tókst að lesa myndina.'));
    reader.readAsDataURL(file);
  });
}

// Shows the local-only image → model → generation → output workflow.
export default function CrystalWorkbench() {
  const inputRef = useRef(null);
  const [catalog, setCatalog] = useState({ profiles: [], blanks: [], approvedV3Available: false, approvedV3Url: '', imagePreprocess: {} });
  const [apiState, setApiState] = useState('connecting');
  const [selectedBlankId, setSelectedBlankId] = useState('2d-rectangle-xlarge-120x80');
  const [selectedProfileId, setSelectedProfileId] = useState('approved-v3-reference');
  const [sourceFile, setSourceFile] = useState(null);
  const [sourceUrl, setSourceUrl] = useState('');
  const [processedAsset, setProcessedAsset] = useState(null);
  const [isPreprocessing, setIsPreprocessing] = useState(false);
  const [preprocessOptions, setPreprocessOptions] = useState({ enhance: false, upscale: true, upscaleTarget: 2048, removeBackground: true, removeBgModel: 'isnet-general-use', alphaMatting: false });
  const [activeStep, setActiveStep] = useState('source');
  const [activeJob, setActiveJob] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [modelUrl, setModelUrl] = useState('');
  const [message, setMessage] = useState('Tengist staðbundinni pipeline þjónustu…');

  const selectedBlank = useMemo(
    () => catalog.blanks.find((blank) => blank.id === selectedBlankId) || catalog.blanks[0] || DEFAULT_BLANK,
    [catalog.blanks, selectedBlankId],
  );
  const selectedProfile = useMemo(
    () => catalog.profiles.find((profile) => profile.id === selectedProfileId),
    [catalog.profiles, selectedProfileId],
  );
  const outputBlank = useMemo(
    () => activeJob?.status === 'complete' && activeJob.blank?.id === selectedBlankId ? activeJob.blank : selectedBlank,
    [activeJob, selectedBlank, selectedBlankId],
  );

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      fetch(`${API_ROOT}/api/catalog`).then((response) => {
        if (!response.ok) throw new Error('catalog');
        return response.json();
      }),
      fetch(`${API_ROOT}/api/jobs`).then((response) => response.json()),
    ])
      .then(([nextCatalog, jobPayload]) => {
        if (cancelled) return;
        setCatalog(nextCatalog);
        setJobs(jobPayload.jobs || []);
        setApiState('ready');
        setMessage('V3 viðmiðið er tilbúið. Veldu kristal eða hlaðdu inn nýrri mynd.');
        if (nextCatalog.approvedV3Available) setModelUrl(nextCatalog.approvedV3Url);
      })
      .catch(() => {
        if (cancelled) return;
        setApiState('offline');
        setMessage('Local pipeline API er ekki í gangi. Keyrðu start-local-workbench.ps1.');
      });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (!activeJob || !['queued', 'running'].includes(activeJob.status)) return undefined;
    const timer = window.setInterval(async () => {
      try {
        const response = await fetch(`${API_ROOT}/api/jobs/${activeJob.id}`);
        if (!response.ok) return;
        const nextJob = await response.json();
        setActiveJob(nextJob);
        setJobs((current) => [nextJob, ...current.filter((job) => job.id !== nextJob.id)]);
        setMessage(nextJob.stage);
        if (nextJob.status === 'complete') {
          setModelUrl(nextJob.resultUrl);
          setActiveStep('result');
        }
        if (nextJob.status === 'failed') setMessage(nextJob.error || 'Keyrslan mistókst.');
      } catch {
        setMessage('Bíð eftir local API…');
      }
    }, 1800);
    return () => window.clearInterval(timer);
  }, [activeJob]);

  // Keeps uploaded browser blobs short-lived and never stores them in browser persistence.
  function handleSourceChange(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    if (sourceUrl) URL.revokeObjectURL(sourceUrl);
    setSourceFile(file);
    setSourceUrl(URL.createObjectURL(file));
    setProcessedAsset(null);
    setActiveStep('source');
    setMessage(`${file.name} er tilbúin fyrir local keyrslu.`);
  }

  // Invalidates an older preview whenever its preparation recipe changes.
  function updatePreprocessOption(name, value) {
    setPreprocessOptions((current) => ({ ...current, [name]: value }));
    setProcessedAsset(null);
  }

  // Runs the existing converter image-pipeline and returns its local PNG preview.
  async function runImagePreprocess() {
    if (!sourceFile) {
      setMessage('Veldu fyrst mynd til að forvinna.');
      inputRef.current?.click();
      return;
    }
    try {
      setIsPreprocessing(true);
      setMessage('Image-pipeline vinnur myndina local…');
      const contentBase64 = await fileToDataUrl(sourceFile);
      const response = await fetch(`${API_ROOT}/api/preprocess`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ fileName: sourceFile.name, contentBase64, options: preprocessOptions }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || 'Image preprocessing mistókst.');
      setProcessedAsset(payload);
      setMessage(`Forvinnslu lokið: ${payload.width}×${payload.height}px · ${payload.stages.join(' → ')}.`);
    } catch (error) {
      setMessage(error.message);
    } finally {
      setIsPreprocessing(false);
    }
  }

  // Starts a new bounded local job; the immutable v3 sample stays in the sidebar.
  async function continueWorkflow() {
    if (activeStep === 'source') {
      setActiveStep('model');
      setMessage('Veldu nú 2.5D módel eða keyrslusnið.');
      return;
    }
    if (activeStep === 'model') {
      setActiveStep('generate');
      setMessage('Staðfestu valið og ræstu generation.');
      return;
    }
    if (activeStep === 'result') {
      setActiveStep('source');
      setMessage('Tilbúið fyrir nýja mynd eða annað form.');
      return;
    }
    if (!sourceFile) {
      setMessage('Veldu fyrst JPG, PNG eða WebP mynd.');
      inputRef.current?.click();
      return;
    }
    try {
      setActiveStep('generate');
      setMessage('Hleð mynd inn í local vinnslumöppu…');
      const contentBase64 = processedAsset ? null : await fileToDataUrl(sourceFile);
      const response = await fetch(`${API_ROOT}/api/jobs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          fileName: sourceFile.name,
          contentBase64,
          preprocessId: processedAsset?.id || null,
          profileId: selectedProfileId,
          blankId: selectedBlank.id,
        }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || 'Ekki tókst að stofna run.');
      setActiveJob(payload);
      setJobs((current) => [payload, ...current]);
      setMessage('Run er í biðröð.');
    } catch (error) {
      setActiveStep('generate');
      setMessage(error.message);
    }
  }

  // Reopens a completed local artifact without duplicating or rerunning it.
  function openJob(job) {
    if (job.status !== 'complete' || !job.resultUrl) return;
    setSelectedBlankId(job.blank.id);
    setSelectedProfileId(job.profileId);
    setModelUrl(job.resultUrl);
    setActiveJob(job);
    setActiveStep('result');
    setMessage(`${job.originalFileName} opnað úr local run history.`);
  }

  const isRunning = activeJob && ['queued', 'running'].includes(activeJob.status);

  return (
    <main className="workbench-page">
      <header className="topbar">
        <div className="brand-lockup"><span className="brand-mark"><Gem size={21} /></span><div><strong>ACM 2.5D Workbench</strong><small>Local research · ekkert fer í production</small></div></div>
        <div className="topbar-actions">
          <a className="gallery-link" href={`${API_ROOT}/api/gallery/workbench.jpg`} target="_blank" rel="noreferrer"><FileImage size={14} /> Opna gallery</a>
          <div className={`api-pill ${apiState}`}><Server size={14} />{apiState === 'ready' ? 'Local API tengt' : apiState === 'offline' ? 'API ótengt' : 'Tengist…'}</div>
        </div>
      </header>

      <nav className="workflow-rail" aria-label="2.5D workflow">
        {[
          ['source', '01', '1. Mynd og form', 'Input', FileImage],
          ['model', '02', '2. Módelval', '2.5D profile', Layers3],
          ['generate', '03', '3. Generate', 'Staðfesta og keyra', Sparkles],
          ['result', '04', '4. GLB output', 'Skoða og skera', Rotate3D],
        ].map(([id, number, label, detail, Icon], index) => (
          <div key={id} className="rail-segment">
            <button type="button" onClick={() => setActiveStep(id)} className={`rail-step ${activeStep === id ? 'active' : ''} ${id === 'result' && modelUrl ? 'available' : ''}`}>
              <span className="step-number">{number}</span><Icon size={18} /><span><strong>{label}</strong><small>{detail}</small></span>
            </button>
            {index < 3 && <ChevronRight className="rail-arrow" size={18} />}
          </div>
        ))}
      </nav>

      <section className="workspace-grid">
        <div className="main-surface">
          {activeStep === 'source' && (
            <div className="panel-grid route-a">
              <section className="source-stage">
                <div className="section-heading"><span>SKREF 1</span><h1>Mynd, forvinnsla og output-form</h1><p>Undirbúðu myndina með sama image-pipeline og converterinn notar, áður en 2.5D módelin fá hana.</p></div>
                <button type="button" className="upload-stage" onClick={() => inputRef.current?.click()}>
                  {sourceUrl ? <img src={processedAsset?.resultUrl || sourceUrl} alt={processedAsset ? 'Forunnin mynd' : 'Valin original mynd'} /> : <div className="upload-empty"><ImagePlus size={34} /><strong>Smelltu til að velja mynd</strong><span>JPG · PNG · WebP · hámark 40 MB</span></div>}
                  <span className="upload-overlay">{sourceUrl ? 'Skipta um mynd' : 'Local upload'}</span>
                  {processedAsset && <span className="processed-badge"><Check size={13} /> FORUNNIÐ · {processedAsset.width}×{processedAsset.height}</span>}
                </button>
                <input ref={inputRef} type="file" accept="image/jpeg,image/png,image/webp" onChange={handleSourceChange} hidden />
                <div className="preprocess-panel">
                  <div className="preprocess-heading"><div><strong>Image-pipeline</strong><span>Original er varðveitt · unnin PNG fer áfram</span></div><span className="local-chip">LOCAL</span></div>
                  <div className="preprocess-options">
                    <label className={preprocessOptions.upscale ? 'prep-card selected' : 'prep-card'}><input type="checkbox" checked={preprocessOptions.upscale} onChange={(event) => updatePreprocessOption('upscale', event.target.checked)} /><ZoomIn size={17} /><span><strong>Upscale í 2K</strong><small>2048 px lengsta hlið</small></span></label>
                    <label className={preprocessOptions.removeBackground ? 'prep-card selected' : 'prep-card'}><input type="checkbox" checked={preprocessOptions.removeBackground} onChange={(event) => updatePreprocessOption('removeBackground', event.target.checked)} /><Scissors size={17} /><span><strong>Fjarlægja bakgrunn</strong><small>RGBA + subject mask</small></span></label>
                    <label className={preprocessOptions.enhance ? 'prep-card selected' : 'prep-card'}><input type="checkbox" checked={preprocessOptions.enhance} onChange={(event) => updatePreprocessOption('enhance', event.target.checked)} /><Sparkles size={17} /><span><strong>Létt myndhreinsun</strong><small>Óvirkt sjálfgefið til að verja andlit</small></span></label>
                  </div>
                  {preprocessOptions.removeBackground && <div className="prep-detail-row"><div><span>Bakgrunnsmódel</span><select aria-label="Bakgrunnsmódel" value={preprocessOptions.removeBgModel} onChange={(event) => updatePreprocessOption('removeBgModel', event.target.value)}><option value="isnet-general-use">ISNet general · uppsett local</option><option value="birefnet-portrait">BiRefNet portrait · best fyrir hár</option><option value="u2net_human_seg">U²-Net human</option><option value="u2net">U²-Net general · uppsett</option><option value="u2netp">U²-Net tiny · uppsett</option></select></div><div className="alpha-option"><input aria-label="Fine-hair alpha matting" type="checkbox" checked={preprocessOptions.alphaMatting} onChange={(event) => updatePreprocessOption('alphaMatting', event.target.checked)} /><span><strong>Fine-hair alpha matting</strong><small>Hægara, mýkri hárkantur</small></span></div></div>}
                  <button type="button" className="preprocess-action" onClick={runImagePreprocess} disabled={!sourceFile || isPreprocessing || !catalog.imagePreprocess?.available}>{isPreprocessing ? <LoaderCircle className="spin" size={16} /> : <Sparkles size={16} />}{isPreprocessing ? 'Image-pipeline keyrir…' : processedAsset ? 'Keyra forvinnslu aftur' : 'Forvinna mynd'}</button>
                </div>
              </section>

              <section className="choice-panel">
                <div className="choice-title"><Gem size={18} /><div><strong>Output-form</strong><small>{selectedBlank.noCrystal ? 'Full-size án kristals' : `${selectedBlank.width} × ${selectedBlank.height} × ${selectedBlank.depth} mm`}</small></div></div>
                <select value={selectedBlank.id} onChange={(event) => setSelectedBlankId(event.target.value)} aria-label="Veldu output-form">
                  {catalog.blanks.map((blank) => <option key={blank.id} value={blank.id}>{blank.fullSize ? blank.name : `${blank.name.replace(/^2D\s+/i, '')} · ${blank.width}×${blank.height}×${blank.depth} mm`}</option>)}
                </select>
                <div className={`blank-silhouette ${selectedBlank.family}`} aria-label={`${selectedBlank.name} silhouette`}><span>{selectedBlank.noCrystal ? 'FULL-SIZE' : selectedBlank.family}</span></div>
                {selectedBlank.noCrystal ? <div className="fullsize-note"><strong>Allt myndhlutfallið</strong><span>Lengsta hlið verður 300 mm. Enginn kristall birtist í skrefi 4.</span></div> : <div className="metric-row"><span><small>Breidd</small><strong>{selectedBlank.width} mm</strong></span><span><small>Hæð</small><strong>{selectedBlank.height} mm</strong></span><span><small>Dýpt</small><strong>{selectedBlank.depth} mm</strong></span></div>}
              </section>
            </div>
          )}

          {activeStep === 'model' && (
            <section className="pipeline-panel">
              <div className="section-heading"><span>SKREF 2</span><h1>Veldu 2.5D módel</h1><p>Samþykkta v3 ferlið er nú keyranlegt fyrir nýjar myndir. Gamla viðmiðið er áfram í run history.</p></div>
              <div className="profile-grid">
                {catalog.profiles.map((profile) => (
                  <button key={profile.id} type="button" onClick={() => setSelectedProfileId(profile.id)} className={`profile-card ${profile.accent} ${selectedProfileId === profile.id ? 'selected' : ''}`}>
                    <span className="profile-icon">{profile.id === 'cpu-safe' ? <Cpu size={19} /> : profile.id.includes('approved') ? <Check size={19} /> : <Sparkles size={19} />}</span>
                    <span className="profile-copy"><strong>{profile.name}</strong><small>{profile.environment}</small><p>{profile.description}</p></span>
                    <span className="profile-time">{profile.estimatedTime}</span>
                  </button>
                ))}
              </div>
            </section>
          )}

          {activeStep === 'generate' && (
            <section className="pipeline-panel generate-panel">
              <div className="section-heading"><span>SKREF 3</span><h1>Staðfesta og generate</h1><p>Stór artifacts fara í `output/local-workbench`; browserinn geymir ekki myndina.</p></div>
              <div className="generation-summary">
                <div><small>MYND</small><strong>{sourceFile ? `${sourceFile.name}${processedAsset ? ` · ${processedAsset.stages.join(' → ')}` : ' · original'}` : 'Engin mynd valin'}</strong></div>
                <div><small>MÓDEL</small><strong>{selectedProfile?.name || 'Ekkert valið'}</strong></div>
                <div><small>OUTPUT</small><strong>{selectedBlank.noCrystal ? 'Full-size GLB · ekkert form' : selectedBlank.name.replace(/^2D\s+/i, '')}</strong></div>
                <div><small>DÝPT</small><strong>{selectedProfileId === 'approved-v3-reference' ? 'V3 source-camera + scene-depth + skirt' : selectedProfileId === 'cuda-quality-deep' ? '20 mm relief' : selectedBlank.noCrystal ? 'Hámark 10 mm' : '15–18% af kristaldýpt'}</strong></div>
              </div>
              {isRunning ? <div className="run-progress"><LoaderCircle className="spin" size={22} /><div><strong>{activeJob.stage}</strong><span>Run {activeJob.id} · lokaðu ekki terminal-glugganum</span></div></div> : <p className="generation-ready">Valið er tilbúið. Ýttu á Generate neðst til hægri.</p>}
            </section>
          )}

          {activeStep === 'result' && (
            <section className="route-b">
              <div className="viewer-heading"><div><span>SKREF 4</span><h1>{outputBlank.noCrystal ? 'Full-size 2.5D GLB output' : '2.5D GLB inni í völdum kristal'}</h1></div><div className="viewer-meta"><strong>{outputBlank.noCrystal ? 'Ekkert form' : outputBlank.name.replace(/^2D\s+/i, '')}</strong><small>{outputBlank.noCrystal ? 'Tilbúið fyrir crop og slicing' : `${outputBlank.width}×${outputBlank.height}×${outputBlank.depth} mm`}</small></div></div>
              <CrystalViewer modelUrl={modelUrl} blank={outputBlank} />
            </section>
          )}
        </div>

        <aside className="run-sidebar">
          <div className="sidebar-heading"><FolderClock size={18} /><div><strong>Local run history</strong><small>{jobs.length} run vistuð</small></div></div>
          <button type="button" className="reference-card" onClick={() => { setSelectedProfileId('approved-v3-reference'); setModelUrl(catalog.approvedV3Url); setActiveStep('result'); }}>
            <span className="status-dot accepted" /><span><strong>Samþykkt depth-skirt v3</strong><small>PARE · ICON · ECON · MoGe</small></span><Check size={17} />
          </button>
          <div className="run-list">
            {jobs.map((job) => (
              <button key={job.id} type="button" disabled={job.status !== 'complete'} onClick={() => openJob(job)} className="run-item">
                <span className={`status-dot ${job.status}`} />
                <span><strong>{job.originalFileName}</strong><small>{job.profileName} · {job.stage}</small></span>
                {job.status === 'running' || job.status === 'queued' ? <LoaderCircle className="spin" size={15} /> : job.status === 'failed' ? <TriangleAlert size={15} /> : <ChevronRight size={15} />}
              </button>
            ))}
            {!jobs.length && <p className="empty-history">Ný local run birtast hér með source, profile og GLB output.</p>}
          </div>
          <div className="scope-note"><Activity size={16} /><p><strong>Rannsóknarsvæði</strong>Production-vefur, Meshy og converter eru ótengd þessu local ferli.</p></div>
        </aside>
      </section>

      <footer className="action-bar">
        <p aria-live="polite">{message}</p>
        <div className="action-summary"><span>{selectedProfile?.name || 'Veldu profile'}</span><span>{selectedBlank.noCrystal ? 'Full-size · ekkert form' : `${selectedBlank.width}×${selectedBlank.height}×${selectedBlank.depth} mm`}</span></div>
        <Button type="button" onClick={continueWorkflow} disabled={apiState !== 'ready' || isRunning} className="primary-action">
          {isRunning ? <LoaderCircle className="spin" size={18} /> : <Play size={18} />}
          {isRunning ? 'Pipeline keyrir…' : activeStep === 'source' ? 'Áfram í módelval' : activeStep === 'model' ? 'Áfram í Generate' : activeStep === 'generate' ? (selectedProfileId === 'approved-v3-reference' ? 'Keyra samþykkta v3 ferlið' : 'Generate 2.5D GLB') : 'Ný keyrsla'}
        </Button>
      </footer>
    </main>
  );
}
