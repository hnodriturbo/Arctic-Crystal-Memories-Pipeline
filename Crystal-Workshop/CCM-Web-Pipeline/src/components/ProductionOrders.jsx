"use client";
/** Purpose: Private order selection, reviewed DXF upload and exact-version machine downloads. */
import { useEffect, useState } from 'react';
import { useLanguage } from '@/components/LanguageProvider';

export default function ProductionOrders() {
  const { locale } = useLanguage();
  const text = (is, en) => locale === 'is' ? is : en;
  const [orders, setOrders] = useState([]);
  const [selected, setSelected] = useState('');
  const [detail, setDetail] = useState(null);
  const [file, setFile] = useState(null);
  const [reviewed, setReviewed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [refresh, setRefresh] = useState(0);
  const [search, setSearch] = useState('');
  const [channel, setChannel] = useState('');
  useEffect(() => {
    const controller = new AbortController();
    fetch('/api/production-orders', { cache: 'no-store', signal: controller.signal }).then(async response => {
      const result = await response.json(); if (!response.ok) throw Error(result.error);
      setOrders(result.orders);
    }).catch(error => { if (error.name !== 'AbortError') setError(error.message); });
    return () => controller.abort();
  }, [refresh]);
  useEffect(() => {
    if (!selected) return;
    const controller = new AbortController();
    fetch('/api/production-orders?snapshot=' + encodeURIComponent(selected), { cache: 'no-store', signal: controller.signal }).then(async response => {
      const result = await response.json(); if (!response.ok) throw Error(result.error);
      setDetail(result);
    }).catch(error => { if (error.name !== 'AbortError') setError(error.message); });
    return () => controller.abort();
  }, [selected, refresh]);
  async function upload(event) {
    event.preventDefault(); if (!file || !reviewed || !selected || busy) return;
    setBusy(true); setError('');
    try {
      if (file.size > 95 * 1024 * 1024) throw Error(text('Hámark er 95 MiB.', 'The limit is 95 MiB.'));
      const params = new URLSearchParams({ snapshot: selected, filename: file.name, reviewed: 'yes' });
      const response = await fetch('/api/production-orders/dxf?' + params, { method: 'POST', headers: { 'Content-Type': 'application/octet-stream' }, body: file });
      const result = await response.json(); if (!response.ok) throw Error(result.error);
      setReviewed(false); setRefresh(value => value + 1);
    } catch (error) { setError(error.message); }
    finally { setBusy(false); }
  }
  function date(value) {
    const d = new Date(value);
    return `${String(d.getDate()).padStart(2, '0')}-${String(d.getMonth() + 1).padStart(2, '0')}-${d.getFullYear()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
  }
  const input = 'rounded-lg border border-surface-border bg-surface p-3';
  return <section className="space-y-5">
    <h2 className="text-2xl font-semibold">Orders &amp; DXF files</h2>
    <p className="text-sm text-muted">{text('Veldu pöntun, vistaðu yfirfarna DXF-skrá úr Cockpit3D og sæktu valda útgáfu á tölvunni við vélina.', 'Choose an order, save your reviewed Cockpit3D DXF and download the chosen version on the machine computer.')}</p>
    <p className="text-sm text-muted">{text('Pöntunarlistinn byggir á varðveittum Main-afritum. Dagsetning afrits sést við pöntun; núverandi greiðslustaða er í Main.', 'Orders come from retained Main snapshots. The snapshot date is shown per order; Main holds current payment status.')}</p>
    <div className="flex flex-wrap gap-3">
      <input aria-label={text('Leita að pöntun', 'Find order')} placeholder={text('Pöntunarnúmer', 'Order number')} value={search} onChange={event => setSearch(event.target.value)} className={input} />
      <select aria-label={text('Sölurás', 'Sales channel')} value={channel} onChange={event => setChannel(event.target.value)} className={input}><option value="">{text('Allar pantanir', 'All orders')}</option><option value="ONLINE">Web</option><option value="IN_STORE">In-store</option></select>
      <button type="button" disabled={busy} className={input} onClick={() => { setError(''); setRefresh(value => value + 1); }}>{text('Endurhlaða', 'Refresh')}</button>
    </div>
    {error && <p role="alert" className="rounded-lg border border-red-400 p-3">{error}</p>}
    <label className="block space-y-2"><span>{text('Pöntun', 'Order')}</span><select disabled={busy} className={`${input} block w-full`} value={selected} onChange={event => { setSelected(event.target.value); setDetail(null); setReviewed(false); setFile(null); setError(''); }}><option value="">{text('Veldu pöntun', 'Select an order')}</option>{orders.filter(order => (!channel || order.channel === channel) && order.orderNumber.toLowerCase().includes(search.toLowerCase())).map(order => <option key={order.id} value={order.snapshotKey}>{order.orderNumber} · {order.channel === 'ONLINE' ? 'Web' : 'In-store'} · {date(order.orderedAt)}</option>)}</select></label>
    {detail && detail.order.snapshotKey === selected && <div className="space-y-5">
      <p>{detail.order.orderNumber} · {text('Afrit frá', 'Snapshot from')} {date(detail.order.capturedAt)} · {detail.order.itemCount} {text('pöntunarlínur', 'order lines')}</p>
      <form onSubmit={upload} className="space-y-4 rounded-xl border border-surface-border p-4">
        <label className="block space-y-2"><span>{text('DXF úr staðbundinni vinnslu', 'DXF from your local workstation')}</span><input key={selected} type="file" accept=".dxf" disabled={busy} required className="block max-w-full" onChange={event => { setFile(event.target.files?.[0] || null); setReviewed(false); }} /></label>
        <label className="flex items-start gap-3"><input type="checkbox" checked={reviewed} disabled={busy} onChange={event => setReviewed(event.target.checked)} /><span>{text('Ég hef yfirfarið þessa DXF-skrá í Cockpit3D og staðfest að hún tilheyri valinni pöntun.', 'I reviewed this DXF in Cockpit3D and confirmed that it belongs to the selected order.')}</span></label>
        <p className="text-sm text-muted">{text('95 MiB hámark. Workshop varðveitir nákvæma skrá; samhæfni og stillingar vélarinnar þarf áfram að yfirfara við innlestur.', '95 MiB maximum. Workshop preserves the exact file; review machine compatibility and settings when importing it.')}</p>
        <button disabled={busy || !file || !reviewed} className={`${input} disabled:opacity-50`}>{busy ? text('Vista og sannprófa…', 'Saving and verifying…') : text('Vista DXF í R2', 'Save DXF to R2')}</button>
      </form>
      <h3 className="text-lg font-semibold">{text('Varðveittar útgáfur', 'Retained versions')}</h3>
      {!detail.versions.length && <p>{text('Engin yfirfarin DXF-útgáfa hefur verið vistuð fyrir þessa pöntun.', 'No reviewed DXF version has been saved for this order.')}</p>}
      <ul className="space-y-3">{detail.versions.map(version => <li key={version.sha256} className="space-y-2 rounded-xl border border-surface-border p-4">
        <p className="break-all font-semibold">{version.filename}</p>
        <p>{date(version.createdAt)} · {(version.bytes / 1048576).toFixed(2)} MiB · {text('Yfirfarin af stjórnanda', 'Operator reviewed')}</p>
        <p className="break-all font-mono text-xs">SHA-256: {version.sha256}</p>
        <a className="inline-block underline" href={'/api/production-orders/dxf?' + new URLSearchParams({ snapshot: selected, version: version.sha256 })}>{text('Sækja þessa DXF-útgáfu', 'Download this DXF version')}</a>
      </li>)}</ul>
    </div>}
  </section>;
}
