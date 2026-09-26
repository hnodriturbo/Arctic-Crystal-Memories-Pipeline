/**
 * Purpose: Browse private R2 scene folders and materialize an explicitly selected pair.
 * All folders are visible; paired files must belong to the same scene folder.
 */
import path from 'node:path';
import { rm } from 'node:fs/promises';
import { createTemporaryWorkspace } from '@/lib/temporary-workspace';
import { auth } from '@/auth';
import { INPUT_DIR, CODE_DIR, PYTHON_EXE, CONVERTER_ROOT } from '@/lib/paths';
import { runPython } from '@/lib/python';
import { listObjects, downloadObject } from '@/lib/storage/r2';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
export const maxDuration = 3600;
const PREFIX = 'Cockpit3D-Files/';
const safeFolder = /^[^./\\][^/\\]*$/;

// Read the live bucket on refresh, including newly synchronized folders.
export async function GET() {
  if (!(await auth())?.user) return new Response(null, { status: 401 });
  try {
    const objects = await listObjects(PREFIX);
    const folders = new Map();
    for (const file of objects) {
      const relative = file.key.slice(PREFIX.length);
      const id = relative.split('/')[0];
      if (!safeFolder.test(id)) continue;
      if (!folders.has(id)) folders.set(id, { id, files: [] });
      if (!file.key.endsWith('/')) folders.get(id).files.push({ ...file, relative: relative.slice(id.length + 1) });
    }
    return Response.json({ folders: [...folders.values()].sort((a, b) => a.id.localeCompare(b.id)) }, { headers: { 'Cache-Control': 'private, no-store' } });
  } catch { return Response.json({ error: 'Could not read the R2 scene library.' }, { status: 502 }); }
}

// Unique import directories isolate concurrent selections and preserve exact scene pairing.
export async function POST(request) {
  if (!(await auth())?.user) return new Response(null, { status: 401 });
  let directory;
  try {
    const origin = request.headers.get('origin');
    if (!origin || new URL(origin).host !== (request.headers.get('x-forwarded-host') || request.headers.get('host'))) return new Response(null, { status: 403 });
    const { exportKey, sceneKey } = await request.json();
    const keys = [exportKey, sceneKey];
    for (const key of keys) {
      if (typeof key !== 'string' || !key.startsWith(PREFIX) || path.posix.normalize(key) !== key || key.includes('\\') || key.split('/').includes('..') || !safeFolder.test(key.slice(PREFIX.length).split('/')[0])) return new Response(null, { status: 400 });
    }
    if (!['.dxf', '.cad'].includes(path.posix.extname(exportKey).toLowerCase()) || path.posix.extname(sceneKey).toLowerCase() !== '.cockpit' || exportKey.split('/')[1] !== sceneKey.split('/')[1]) return new Response(null, { status: 400 });
    const temporary = await createTemporaryWorkspace(INPUT_DIR, { sourceKeys: keys, sceneFolder: exportKey.split('/')[1] });
    const { relative } = temporary;
    directory = temporary.directory;
    const names = keys.map((key) => path.posix.basename(key));
    for (let i = 0; i < keys.length; i++) await downloadObject(keys[i], path.join(directory, names[i]));
    let pose = null;
    await runPython(PYTHON_EXE, [path.join(CODE_DIR, 'cockpit_reconstruct.py'), '--inspect-scene', path.join(directory, names[1])], {
      cwd: CONVERTER_ROOT,
      onLine(event) { if (event.line?.startsWith('ACM_SCENE_POSE=')) pose = JSON.parse(event.line.slice(15)); },
    });
    return Response.json({ file: relative + '/' + names[0], texture: relative + '/' + names[1], sceneFolder: exportKey.split('/')[1], sourceKeys: keys, pose });
  } catch {
    if (directory) await rm(directory, { recursive: true, force: true });
    return Response.json({ error: 'Could not load the selected scene pair from R2.' }, { status: 502 });
  }
}
