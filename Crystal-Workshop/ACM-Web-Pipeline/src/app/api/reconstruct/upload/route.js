/** Purpose: Accept a bounded operator GLB through the Workshop origin and persist it to R2; remove temporary bytes after every attempt. */
import { auth } from '@/auth';
import { saveSceneModel } from '@/lib/storage/scene-model-names';
import { safeFileName } from '@/lib/paths';
import { mkdtemp, open, rm, stat } from 'node:fs/promises';
import { createWriteStream } from 'node:fs';
import { Readable, Transform } from 'node:stream';
import { pipeline } from 'node:stream/promises';
import path from 'node:path';
import os from 'node:os';

export const runtime = 'nodejs';
export const maxDuration = 3600;
const maximumBytes = 64 * 1024 * 1024;

// Same-origin, signed-in uploads have one immutable R2 destination and bounded disk use.
export async function POST(request) {
  if (!(await auth())?.user) return new Response(null, { status: 401 });
  let temporary;
  try {
    const origin = request.headers.get('origin');
    if (!origin || new URL(origin).host !== (request.headers.get('x-forwarded-host') || request.headers.get('host'))) return new Response(null, { status: 403 });
    const folder = request.headers.get('x-scene-folder');
    const name = safeFileName(decodeURIComponent(request.headers.get('x-filename') || ''));
    if (!/^\d+-[a-zA-Z0-9_-]+$/.test(folder || '') || path.extname(name).toLowerCase() !== '.glb' || !request.body) return Response.json({ error: 'Choose a numbered scene folder and a GLB file.' }, { status: 400 });
    const declared = Number(request.headers.get('content-length'));
    if (declared > maximumBytes) return Response.json({ error: 'GLB uploads support up to 64 MB.' }, { status: 413 });
    temporary = await mkdtemp(path.join(os.tmpdir(), 'acm-showroom-upload-'));
    const file = path.join(temporary, 'model.glb');
    let received = 0;
    const bounded = new Transform({ transform(chunk, _encoding, next) {
      received += chunk.length;
      next(received > maximumBytes ? new Error('GLB uploads support up to 64 MB.') : null, chunk);
    } });
    await pipeline(Readable.fromWeb(request.body), bounded, createWriteStream(file, { flags: 'wx', mode: 0o600 }), { signal: request.signal });
    const size = (await stat(file)).size;
    const handle = await open(file, 'r'); const header = Buffer.alloc(12);
    try { await handle.read(header, 0, 12, 0); } finally { await handle.close(); }
    if (size < 12 || header.readUInt32LE(0) !== 0x46546c67 || header.readUInt32LE(4) !== 2 || header.readUInt32LE(8) !== size) return Response.json({ error: 'Invalid GLB.' }, { status: 400 });
    const key = await saveSceneModel(file, folder, { edited: true });
    return Response.json({ key, bytes: size });
  } catch { return Response.json({ error: 'GLB upload failed. Check the file and retry (maximum 64 MB).' }, { status: 400 }); }
  finally {
    if (temporary && path.dirname(temporary) === path.resolve(os.tmpdir()) && path.basename(temporary).startsWith('acm-showroom-upload-')) await rm(temporary, { recursive: true, force: true });
  }
}
