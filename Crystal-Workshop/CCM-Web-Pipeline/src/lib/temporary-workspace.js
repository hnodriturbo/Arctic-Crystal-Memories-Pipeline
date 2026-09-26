/** Purpose: Isolate disposable R2 working copies; expire only marked seven-day-old job directories. */
import path from 'node:path';
import { randomUUID } from 'node:crypto';
import { mkdir, readdir, readFile, writeFile, realpath, rm } from 'node:fs/promises';
const MAX_AGE = 7 * 24 * 60 * 60 * 1000;

export async function createTemporaryWorkspace(root, metadata = {}) {
  const parent = path.join(root, 'tmp');
  await mkdir(parent, { recursive: true });
  const actualParent = await realpath(parent);
  for (const item of await readdir(parent, { withFileTypes: true })) {
    if (!item.isDirectory() || !/^[a-f0-9-]{36}$/.test(item.name)) continue;
    const candidate = path.join(parent, item.name);
    try {
      const actual = await realpath(candidate);
      if (path.dirname(actual) !== actualParent) continue;
      const marker = JSON.parse(await readFile(path.join(candidate, '.workshop-temp.json'), 'utf8'));
      if (marker.owner === 'workshop-temporary-v1' && Number.isFinite(marker.created) && Date.now() - marker.created > MAX_AGE) await rm(actual, { recursive: true });
    } catch { /* Unmarked or unavailable folders are preserved. */ }
  }
  const relative = 'tmp/' + randomUUID();
  const directory = path.join(root, relative);
  await mkdir(directory);
  await writeFile(path.join(directory, '.workshop-temp.json'), JSON.stringify({ ...metadata, owner: 'workshop-temporary-v1', created: Date.now() }), { flag: 'wx' });
  return { relative, directory };
}
