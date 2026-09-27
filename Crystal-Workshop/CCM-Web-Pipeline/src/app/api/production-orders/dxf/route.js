/** Purpose: Stream reviewed local DXF originals into immutable private storage and issue exact-version downloads. */
import { createHash } from 'node:crypto';
import { createWriteStream } from 'node:fs';
import { mkdtemp, rm, open } from 'node:fs/promises';
import { Readable, Transform } from 'node:stream';
import { pipeline } from 'node:stream/promises';
import os from 'node:os';
import path from 'node:path';
import { operator, failure } from '@/lib/orders/access';
import { getOrder, saveDxf, downloadDxf } from '@/lib/orders/storage.mjs';
export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
export const maxDuration = 900;
const MAX = 95 * 1024 * 1024;
export async function POST(request) {
  let temporary;
  try {
    const user = await operator(request, true);
    const params = new URL(request.url).searchParams;
    if (params.get('reviewed') !== 'yes' || !request.body || Number(request.headers.get('content-length')) > MAX) throw Error('Review/file required');
    const filename = params.get('filename');
    if (!filename || filename.length > 200 || /[\\/\x00-\x1f\x7f]/.test(filename) || !/\.dxf$/i.test(filename)) throw Error('Invalid filename');
    const order = await getOrder(params.get('snapshot'));
    temporary = await mkdtemp(path.join(os.tmpdir(), 'ccm-order-dxf-'));
    const local = path.join(temporary, 'original.dxf');
    let bytes = 0; const hash = createHash('sha256');
    await pipeline(Readable.fromWeb(request.body), new Transform({ transform(chunk, encoding, done) { bytes += chunk.length; if (bytes > MAX) return done(Error('DXF exceeds limit')); hash.update(chunk); done(null, chunk); } }), createWriteStream(local, { flags: 'wx' }));
    const declared = request.headers.get('content-length');
    if (declared !== null && Number(declared) !== bytes) throw Error('Incomplete DXF upload');
    // Recognize the DXF container only. Operator review is explicit, not a machine compatibility certificate.
    const file = await open(local, 'r');
    try {
      const first = Buffer.alloc(Math.min(bytes, 1024)); const last = Buffer.alloc(Math.min(bytes, 1024));
      await file.read(first, 0, first.length, 0); await file.read(last, 0, last.length, bytes - last.length);
      if (!bytes || (!first.toString('ascii').startsWith('AutoCAD Binary DXF') && (!/\bSECTION\b/.test(first.toString('ascii')) || !/\bEOF\b/.test(last.toString('ascii'))))) throw Error('Unrecognized DXF container');
    } finally { await file.close(); }
    const version = await saveDxf({ order, path: local, sha256: hash.digest('hex'), bytes, filename, userId: user.id });
    return Response.json({ version }, { headers: { 'Cache-Control': 'private, no-store' } });
  } catch (error) { return failure(error); }
  finally { if (temporary) await rm(temporary, { recursive: true, force: true }); }
}
export async function GET(request) {
  try {
    await operator(request);
    const params = new URL(request.url).searchParams;
    const order = await getOrder(params.get('snapshot'));
    const download = await downloadDxf(order, params.get('version'));
    return new Response(download.body, { headers: { 'Content-Type': 'application/dxf', 'Content-Length': String(download.bytes), 'Content-Disposition': `attachment; filename="${download.filename}"`, 'X-Content-Type-Options': 'nosniff', 'X-File-SHA256': download.sha256, 'Cache-Control': 'private, no-store', 'Referrer-Policy': 'no-referrer' } });
  } catch (error) { return failure(error); }
}
