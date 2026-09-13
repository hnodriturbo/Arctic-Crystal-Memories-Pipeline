/*
 * ═══════════════════════════════════════════════════════════════
 * Publish Showroom Source
 * ═══════════════════════════════════════════════════════════════
 * Path: src/app/api/reconstruct/publish/route.js
 * Purpose: Save a verified local GLB into the private R2 showroom source library.
 */
import { realpath, open, stat, readFile } from 'node:fs/promises';
import path from 'node:path';
import { randomUUID } from 'node:crypto';
import { auth } from '@/auth';
import { OUTPUT_DIR, resolveInside } from '@/lib/paths';
import { uploadFile } from '@/lib/storage/r2';

// Only authenticated same-origin operators can publish existing output files.
export async function POST(request) {
  if (!(await auth())?.user) return Response.json({ error: 'Sign in required.' }, { status: 401 });
  const origin = request.headers.get('origin');
  if (!origin || new URL(origin).host !== (request.headers.get('x-forwarded-host') || request.headers.get('host'))) return new Response(null, { status: 403 });
  try {
    const { file, sceneFolder } = await request.json();
    if (typeof sceneFolder !== 'string' || !/^\d+-[a-zA-Z0-9_-]+$/.test(sceneFolder)) return Response.json({ error: 'Choose a numbered scene folder first.' }, { status: 400 });
    if (typeof file !== 'string' || path.extname(file).toLowerCase() !== '.glb') return new Response(null, { status: 400 });
    const candidate = resolveInside(OUTPUT_DIR, file);
    if (!candidate) return new Response(null, { status: 400 });
    const [root, source] = await Promise.all([realpath(OUTPUT_DIR), realpath(candidate)]);
    if (!resolveInside(root, path.relative(root, source))) return new Response(null, { status: 400 });
    if (file.startsWith('tmp/')) {
      const provenance = JSON.parse(await readFile(path.join(path.dirname(source), '.workshop-temp.json'), 'utf8'));
      if (provenance.sceneFolder !== sceneFolder) return Response.json({error:'Save this result to its original scene folder.'},{status:400});
    }
    const size = (await stat(source)).size;
    const handle = await open(source, 'r');
    const header = Buffer.alloc(12);
    try { await handle.read(header, 0, 12, 0); } finally { await handle.close(); }
    if (header.readUInt32LE(0) !== 0x46546c67 || header.readUInt32LE(4) !== 2 || header.readUInt32LE(8) !== size) return Response.json({ error: 'Invalid GLB.' }, { status: 400 });
    const key = `Cockpit3D-Files/${sceneFolder}/${randomUUID()}-${path.basename(file)}`;
    await uploadFile(source, key);
    return Response.json({ key, bytes: size });
  } catch { return Response.json({ error: 'Could not save the model to R2.' }, { status: 500 }); }
}
