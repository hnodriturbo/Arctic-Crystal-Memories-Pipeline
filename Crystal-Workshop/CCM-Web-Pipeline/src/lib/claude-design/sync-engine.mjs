/** Purpose: Shared, non-deleting two-way file sync with a baseline, conflict copies and conditional R2 writes. */
import path from 'node:path';
import { setTimeout as pause } from 'node:timers/promises';
import { createHash } from 'node:crypto';
import { createReadStream } from 'node:fs';
import { mkdir, readdir, lstat, readFile, writeFile, rename, copyFile, unlink, open } from 'node:fs/promises';

const IGNORED = new Set(['node_modules', 'zip-files', 'exported-videos']);
export function validCollection(name) {
  return typeof name === 'string' && name === name.trim() && name.length > 0 && name.length <= 100 &&
    !/[\\/:*?"<>|\x00-\x1f]/.test(name) && !name.startsWith('.') && !/[. ]$/.test(name) &&
    !/^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)/i.test(name) && !IGNORED.has(name);
}
export function validRelative(relative) {
  return typeof relative === 'string' && relative.split('/').every(validCollection);
}
export async function digestFile(file) {
  const hash = createHash('sha256');
  for await (const chunk of createReadStream(file)) hash.update(chunk);
  return hash.digest('hex');
}
/** Windows indexing/virus scanners can briefly hold a file across an atomic rename. */
async function replaceFile(source, destination) {
  for (let attempt = 0; ; attempt++) {
    try { await rename(source, destination); return; }
    catch (error) { if (attempt >= 8 || !['EPERM', 'EACCES', 'EBUSY'].includes(error.code)) throw error; await pause(100 * (attempt + 1)); }
  }
}
async function exists(file) { try { return await lstat(file); } catch (e) { if (e.code === 'ENOENT') return null; throw e; } }
async function safePath(root, relative) {
  if (!validRelative(relative)) throw new Error('Unsafe sync path: ' + relative);
  let current = root;
  for (const part of relative.split('/')) {
    current = path.join(current, part);
    if ((await exists(current))?.isSymbolicLink()) throw new Error('Symlinks cannot be synced: ' + relative);
  }
  return current;
}
async function inventory(root, prefix = '') {
  const found = [];
  for (const entry of await readdir(root, { withFileTypes: true })) {
    if (!validCollection(entry.name) || entry.isSymbolicLink()) continue;
    const relative = prefix + entry.name;
    if (entry.isDirectory()) found.push(...await inventory(path.join(root, entry.name), relative + '/'));
    else if (entry.isFile()) found.push(relative);
  }
  return found;
}
/** A missing side is restored, never treated as a request to delete the other side. */
export function syncAction(local, remote, baseline) {
  if (!local) return remote ? 'pull' : 'same';
  if (!remote) return 'push';
  if (local === remote) return 'same';
  if (baseline === remote) return 'push';
  if (baseline === local) return 'pull';
  return 'conflict';
}
export async function syncTree({ root, store, prefix = 'claude-design/sources/', collection, dryRun = false, onLine = () => {} }) {
  if (collection && !validCollection(collection)) throw new Error('Invalid collection name');
  await mkdir(root, { recursive: true });
  const control = path.join(root, '.workshop-sync');
  await mkdir(control, { recursive: true });
  const lockPath = path.join(control, 'lock');
  let lock;
  try { lock = await open(lockPath, 'wx'); } catch (e) { if (e.code === 'EEXIST') throw new Error('A design sync is already running (or needs its stale lock reviewed).'); throw e; }
  const statePath = path.join(control, 'state.json');
  const summary = { uploaded: 0, fetched: 0, unchanged: 0, conflicts: 0, skipped: 0 };
  try {
    let state = {};
    try { state = JSON.parse(await readFile(statePath, 'utf8')); } catch (e) { if (e.code !== 'ENOENT') throw e; }
    const save = async () => { if (!dryRun) { await writeFile(statePath + '.tmp', JSON.stringify(state)); await replaceFile(statePath + '.tmp', statePath); } };
    const localFiles = (await inventory(root)).filter(name => !collection || name.startsWith(collection + '/'));
    const objects = await store.list(prefix + (collection ? collection + '/' : ''));
    const remoteFiles = new Map(objects.map(item => [item.key.slice(prefix.length), item]));
    for (const relative of new Set([...localFiles, ...remoteFiles.keys()])) {
      if (relative.endsWith('/')) {
        const folder = relative.slice(0, -1);
        if (validRelative(folder) && !dryRun) await mkdir(await safePath(root, folder), { recursive: true });
        continue;
      }
      if (!validRelative(relative)) { summary.skipped++; onLine('SKIPPED unsafe path ' + relative); continue; }
      const destination = await safePath(root, relative);
      const info = await exists(destination);
      if (info && !info.isFile()) { summary.skipped++; continue; }
      const key = prefix + relative;
      const remote = await store.head(key);
      if (prefix.endsWith('/sources/') && ((info?.size || 0) > 200 * 1024 * 1024 || (remote?.size || 0) > 200 * 1024 * 1024)) { summary.skipped++; continue; }
      const localHash = info ? await digestFile(destination) : null;
      let remoteHash = remote?.hash;
      const temporary = path.join(control, 'incoming');
      try {
        // Old/external uploads lack metadata: read the bytes, never trust size equality.
        if (remote && !remoteHash) { await store.download(key, temporary, remote.etag); remoteHash = await digestFile(temporary); }
        const action = syncAction(localHash, remoteHash, state[key]);
        if (action === 'same') { summary.unchanged++; state[key] = localHash; }
        else if (dryRun) { onLine('WOULD_' + action.toUpperCase() + ' ' + relative); summary[action === 'push' ? 'uploaded' : action === 'pull' ? 'fetched' : 'conflicts']++; }
        else if (action === 'push') {
          if (remote) await store.archive(key, remote);
          // Snapshot prevents a concurrent editor from changing the bytes after hashing.
          const snapshot = path.join(control, 'outgoing');
          try {
            await copyFile(destination, snapshot);
            if (await digestFile(snapshot) !== localHash) throw new Error('Local file changed during sync: ' + relative);
            await store.upload(key, snapshot, localHash, remote?.etag);
          } finally { await unlink(snapshot).catch(() => {}); }
          state[key] = localHash; summary.uploaded++; onLine('UPLOADED ' + relative);
        } else {
          if (!(await exists(temporary))) await store.download(key, temporary, remote.etag);
          if (await digestFile(temporary) !== remoteHash) throw new Error('Remote checksum changed: ' + relative);
          if (action === 'conflict') {
            const conflict = path.join(control, 'conflicts', remoteHash, relative);
            await mkdir(path.dirname(conflict), { recursive: true }); await replaceFile(temporary, conflict);
            summary.conflicts++; onLine('CONFLICT kept local and remote; R2 copy saved at ' + conflict);
          } else {
            // Preserve the current local revision before any replacement.
            if (info) {
              const history = path.join(control, 'history', localHash, relative);
              await mkdir(path.dirname(history), { recursive: true }); await copyFile(destination, history);
              if (await digestFile(destination) !== localHash) throw new Error('Local file changed during download: ' + relative);
            } else if (await exists(destination)) throw new Error('Local file appeared during download: ' + relative);
            await mkdir(path.dirname(destination), { recursive: true }); await replaceFile(temporary, destination);
            state[key] = remoteHash; summary.fetched++; onLine('FETCHED ' + relative);
          }
        }
        await save();
      } finally { await unlink(temporary).catch(() => {}); }
    }
    return summary;
  } finally { await lock.close(); await unlink(lockPath); }
}
