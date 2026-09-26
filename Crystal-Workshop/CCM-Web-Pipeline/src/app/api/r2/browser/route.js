/** Purpose: Authenticated live R2 folder listing and direct, short-lived downloads. */
import path from 'node:path';
import { auth } from '@/auth';
import { listObjects, presignDownload } from '@/lib/storage/r2';
import { STORAGE_AREAS, allowedStorageKey } from '@/lib/storage/browser-scope';
export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export async function GET(request) {
  if (!(await auth())?.user) return new Response(null, { status: 401 });
  const params = new URL(request.url).searchParams;
  const prefix = params.get('prefix');
  const key = params.get('download');
  try {
    if (key) {
      if (!allowedStorageKey(key) || key.endsWith('/')) return new Response(null, { status: 400 });
      return Response.redirect(await presignDownload(key, { fileName: path.posix.basename(key) }), 302);
    }
    if (!prefix) return Response.json({ areas: STORAGE_AREAS });
    if (!allowedStorageKey(prefix) || !prefix.endsWith('/')) return new Response(null, { status: 400 });
    const objects = await listObjects(prefix);
    const folders = new Set();
    const files = [];
    for (const object of objects) {
      const rest = object.key.slice(prefix.length);
      if (!rest) continue;
      if (rest.includes('/')) folders.add(prefix + rest.split('/')[0] + '/');
      else files.push(object);
    }
    return Response.json({ prefix, folders: [...folders].sort(), files }, { headers: { 'Cache-Control': 'private, no-store' } });
  } catch {
    return Response.json({ error: 'Could not read R2. Refresh to try again.' }, { status: 502 });
  }
}
