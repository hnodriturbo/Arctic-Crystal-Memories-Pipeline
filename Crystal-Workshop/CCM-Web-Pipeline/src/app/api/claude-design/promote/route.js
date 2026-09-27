/** Purpose: Explicit authenticated design/video handoff to immutable private shared storage. */
import { mkdtemp, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { auth } from '@/auth';
import { prisma } from '@/lib/prisma';
import { DESIGN_ROOT, allowedDesignKey, R2_VIDEO_PREFIX } from '@/lib/claude-design/paths';
import { collectDesignSources } from '@/lib/claude-design/discovery.mjs';
import { promotePackage } from '@/lib/claude-design/promotion.mjs';
import { sharedStore, sharedConfigured } from '@/lib/storage/shared-r2.mjs';
import { fetchObject, contentTypeFor } from '@/lib/storage/workshop-r2';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
export const maxDuration = 900;
export async function POST(request) {
  const session = await auth();
  if (!session?.user?.id) return Response.json({ error: 'Unauthorized' }, { status: 401 });
  const user = await prisma.user.findUnique({ where: { id: session.user.id }, select: { isActive: true, role: true } });
  if (!user?.isActive || !['OWNER', 'ADMIN'].includes(user.role)) return Response.json({ error: 'Forbidden' }, { status: 403 });
  // Next's internal URL may use localhost behind the proxy; compare against the configured public origin.
  if (request.headers.get('origin') !== new URL(process.env.AUTH_URL || request.url).origin) return Response.json({ error: 'Foreign origin' }, { status: 403 });
  if (!sharedConfigured()) return Response.json({ error: 'Shared handoff is not configured.' }, { status: 503 });
  let temporary;
  try {
    const body = await request.json();
    if (!/^(is|en)-(desktop|tablet|mobile)$/.test(body.variant)) return Response.json({ error: 'Select language and device.' }, { status: 400 });
    let entryPath, files;
    if (body.kind === 'design') {
      entryPath = body.rootRel;
      files = collectDesignSources(DESIGN_ROOT, entryPath, contentTypeFor);
    } else if (body.kind === 'video') {
      if (!allowedDesignKey(body.key) || !body.key.startsWith(R2_VIDEO_PREFIX) || !/\.(mp4|webm)$/i.test(body.key)) throw new Error('Invalid video.');
      temporary = await mkdtemp(path.join(os.tmpdir(), 'ccm-video-handoff-'));
      const local = path.join(temporary, 'video' + path.extname(body.key));
      await fetchObject(body.key, local);
      const probe = spawnSync('ffprobe', ['-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height:format=duration', '-of', 'json', local], { encoding: 'utf8', timeout: 30000, windowsHide: true });
      if (probe.status !== 0) throw new Error('Video metadata could not be verified.');
      const metadata = JSON.parse(probe.stdout);
      entryPath = body.key.slice(R2_VIDEO_PREFIX.length);
      files = [{ path: local, relativePath: entryPath, role: 'video', mime: contentTypeFor(entryPath), width: metadata.streams?.[0]?.width, height: metadata.streams?.[0]?.height, durationSeconds: Number(metadata.format?.duration) }];
      const posterKey = body.key.replace(/\.(mp4|webm)$/i, '.jpg');
      const posterPath = path.join(temporary, 'poster.jpg');
      try {
        await fetchObject(posterKey, posterPath);
        files.push({ path: posterPath, relativePath: entryPath.replace(/\.(mp4|webm)$/i, '.jpg'), role: 'poster', mime: 'image/jpeg' });
      } catch (error) { if (error.$metadata?.httpStatusCode !== 404) throw error; }
    } else throw new Error('Select a design or video.');
    const receipt = await promotePackage({ kind: body.kind, variant: body.variant, entryPath, files, store: sharedStore() });
    return Response.json({ status: 'verified', receipt }, { headers: { 'Cache-Control': 'private, no-store' } });
  } catch (error) {
    console.error('[shared-handoff]', error.code || error.$metadata?.httpStatusCode || error.name);
    return Response.json({ error: 'Transfer was not verified. Sources are preserved; check dependencies/configuration and retry.' }, { status: 422 });
  } finally { if (temporary) await rm(temporary, { recursive: true, force: true }); }
}
