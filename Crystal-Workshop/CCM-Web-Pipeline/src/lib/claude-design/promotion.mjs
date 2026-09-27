/**
 * Purpose: Explicit immutable handoff packages, verified body-by-body before manifest discovery.
 * The injected store only supports reads and create-only writes; publication is Main-owned.
 */
import { createHash } from 'node:crypto';
import { createReadStream } from 'node:fs';
import { copyFile, mkdtemp, rm, stat } from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import { validKey } from '../storage/shared-copy.mjs';

export const sha256 = data => createHash('sha256').update(data).digest('hex');
async function digest(body) {
  const hash = createHash('sha256'); let bytes = 0;
  for await (const chunk of body) { hash.update(chunk); bytes += chunk.length; }
  return { sha256: hash.digest('hex'), bytes };
}
async function verify(store, key, expected) {
  const remote = await store.get(key);
  if (!remote) throw new Error('Shared object missing after write.');
  const actual = await digest(remote.body);
  if (actual.sha256 !== expected.sha256 || actual.bytes !== expected.bytes || remote.mime !== expected.mime) throw new Error('Immutable shared object conflicts with this package.');
}
async function writeFile(store, key, local, expected) {
  const body = createReadStream(local);
  try { await store.putMissing(key, body, expected); }
  catch (error) { if (error.$metadata?.httpStatusCode !== 412) throw error; }
  finally { body.destroy(); }
  await verify(store, key, expected);
}

export async function promotePackage({ kind, variant, entryPath, files, store, onProgress = () => {} }) {
  if (!['video', 'design'].includes(kind) || !/^(is|en)-(desktop|tablet|mobile)$/.test(variant) || !validKey(entryPath)) throw new Error('Invalid handoff identity.');
  if (!Array.isArray(files) || !files.length || files.length > 1000) throw new Error('Invalid package size.');
  const names = new Set();
  for (const file of files) {
    if (!validKey(file.relativePath) || file.relativePath.split('/').some(part => part.startsWith('.')) || names.has(file.relativePath)) throw new Error('Unsafe package path.');
    if (!['source', 'video', 'poster'].includes(file.role) || typeof file.mime !== 'string') throw new Error('Invalid package file.');
    names.add(file.relativePath);
  }
  if (!names.has(entryPath)) throw new Error('Entry is missing from package.');
  if (kind === 'design' && (!/\.html?$/i.test(entryPath) || files.some(file => file.role !== 'source'))) throw new Error('Invalid design package.');
  if (kind === 'video' && (files.filter(file => file.role === 'video').length !== 1 || files.filter(file => file.role === 'poster').length > 1 || files.some(file => file.role === 'source') || files.find(file => file.relativePath === entryPath)?.role !== 'video')) throw new Error('Invalid video package.');
  const temporary = await mkdtemp(path.join(os.tmpdir(), 'ccm-promotion-'));
  try {
    const snapshots = new Map(), descriptors = [];
    for (const [index, file] of files.entries()) {
      const before = await stat(file.path);
      if (!before.isFile() || before.size > (kind === 'design' ? 200_000_000 : 5_000_000_000)) throw new Error('Unsupported package file size.');
      const snapshot = path.join(temporary, String(index));
      await copyFile(file.path, snapshot);
      const after = await stat(file.path);
      if (before.size !== after.size || before.mtimeMs !== after.mtimeMs) throw new Error('Source is still changing; retry after saving.');
      const hash = await digest(createReadStream(snapshot));
      if (hash.bytes !== before.size) throw new Error('Incomplete source snapshot.');
      const descriptor = { relativePath: file.relativePath, role: file.role, sha256: hash.sha256, bytes: hash.bytes, mime: file.mime };
      if (file.role === 'video') {
        for (const field of ['width', 'height', 'durationSeconds']) {
          if (!Number.isFinite(file[field]) || file[field] <= 0) throw new Error('Video metadata is missing.');
          descriptor[field] = file[field];
        }
      }
      descriptors.push(descriptor); snapshots.set(file.relativePath, snapshot);
    }
    descriptors.sort((a, b) => a.relativePath < b.relativePath ? -1 : a.relativePath > b.relativePath ? 1 : 0);
    const sourceSha256 = descriptors.find(file => file.relativePath === entryPath).sha256;
    const canonical = { kind, variant, entryPath, files: descriptors, sourceSha256 };
    const assetId = kind + '-' + sha256(entryPath).slice(0, 24);
    const version = 'sha256-' + sha256(JSON.stringify(canonical));
    const prefix = `claude-design/${kind === 'design' ? 'sources' : 'videos'}/${assetId}/${version}/`;
    const manifestKey = `claude-design/manifests/${assetId}/${version}.json`;
    const content = { files: descriptors.map(file => ({ ...file, key: prefix + file.relativePath })) };
    if (kind === 'design') content.entryKey = prefix + entryPath;
    const manifest = { schemaVersion: 1, assetId, version, kind, state: 'draft', createdAt: new Date().toISOString(), variants: { [variant]: content }, provenance: { producer: 'ccm-workshop', sourceSha256 } };
    // Every retry rechecks files; an existing manifest never substitutes for body verification.
    for (const [index, file] of descriptors.entries()) {
      onProgress({ phase: 'copying', complete: index, total: descriptors.length });
      await writeFile(store, prefix + file.relativePath, snapshots.get(file.relativePath), file);
    }
    let bytes = Buffer.from(JSON.stringify(manifest));
    try { await store.putMissing(manifestKey, bytes, { bytes: bytes.length, mime: 'application/json', sha256: sha256(bytes) }); }
    catch (error) { if (error.$metadata?.httpStatusCode !== 412) throw error; }
    const remote = await store.get(manifestKey);
    if (!remote || remote.bytes > 2_000_000 || remote.mime !== 'application/json') throw new Error('Invalid shared manifest readback.');
    const chunks = []; let length = 0;
    for await (const chunk of remote.body) { length += chunk.length; if (length > 2_000_000) throw new Error('Manifest too large.'); chunks.push(chunk); }
    bytes = Buffer.concat(chunks);
    const stored = JSON.parse(bytes.toString('utf8'));
    const { createdAt: storedAt, ...storedIdentity } = stored;
    const { createdAt: proposedAt, ...expectedIdentity } = manifest;
    if (!storedAt || !proposedAt || JSON.stringify(storedIdentity) !== JSON.stringify(expectedIdentity)) throw new Error('Shared manifest conflict.');
    onProgress({ phase: 'verified', complete: descriptors.length, total: descriptors.length });
    return { manifestKey, assetId, version, manifestSha256: sha256(bytes), filesVerified: descriptors.length };
  } finally { await rm(temporary, { recursive: true, force: true }); }
}
