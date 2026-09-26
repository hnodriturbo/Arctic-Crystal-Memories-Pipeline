/*
 * ═══════════════════════════════════════════════════════════════
 * Publish Showroom Source
 * ═══════════════════════════════════════════════════════════════
 * Path: src/app/api/reconstruct/publish/route.js
 * Purpose: Save a verified local GLB into the private R2 showroom source library.
 */
import { realpath, open, stat, readFile } from 'node:fs/promises';
import path from 'node:path';
import { auth } from '@/auth';
import { OUTPUT_DIR, resolveInside } from '@/lib/paths';
import { saveSceneModel, saveReservedFile } from '@/lib/storage/scene-model-names';
import { createHash } from 'node:crypto';

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
    let outputStem;
    if (file.startsWith('tmp/')) {
      const provenance = JSON.parse(await readFile(path.join(path.dirname(source), '.workshop-temp.json'), 'utf8'));
      if (provenance.sceneFolder !== sceneFolder) return Response.json({error:'Save this result to its original scene folder.'},{status:400});
      outputStem = provenance.outputStem;
      if (outputStem && (!new RegExp(`^${sceneFolder}-v\\d+$`).test(outputStem) || path.basename(source) !== outputStem + '.glb')) throw new Error('Invalid reserved model name.');
    }
    const size = (await stat(source)).size;
    const handle = await open(source, 'r');
    const header = Buffer.alloc(12);
    try { await handle.read(header, 0, 12, 0); } finally { await handle.close(); }
    if (header.readUInt32LE(0) !== 0x46546c67 || header.readUInt32LE(4) !== 2 || header.readUInt32LE(8) !== size) return Response.json({ error: 'Invalid GLB.' }, { status: 400 });
    const report = JSON.parse(await readFile(source.replace(/\.glb$/i, '.json'), 'utf8'));
    let originalKey;
    if (report.originalPhoto) {
      const photo = report.originalPhoto;
      const photoPattern = outputStem ? new RegExp(`^${outputStem}\\.(jpg|jpeg|png)$`) : /^original-[a-f0-9]{16}\.(jpg|jpeg|png)$/;
      if (!photoPattern.test(photo.name)) throw new Error('Invalid original photo.');
      const photoPath = await realpath(path.join(path.dirname(source), photo.name));
      if (path.dirname(photoPath) !== path.dirname(source)) throw new Error('Invalid original path.');
      const bytes = await readFile(photoPath);
      if (createHash('sha256').update(bytes).digest('hex') !== photo.sha256) throw new Error('Original photo hash mismatch.');
      originalKey = `Cockpit3D-Files/${sceneFolder}/${photo.name}`;
      await saveReservedFile(photoPath, originalKey);
    }
    const key = outputStem ? await saveReservedFile(source, `Cockpit3D-Files/${sceneFolder}/${outputStem}.glb`) : await saveSceneModel(source, sceneFolder);
    return Response.json({ key, bytes: size, originalKey });
  } catch { return Response.json({ error: 'Could not save the model to R2.' }, { status: 500 }); }
}
