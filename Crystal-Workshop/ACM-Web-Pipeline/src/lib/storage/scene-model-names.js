/**
 * Purpose: Save readable, versioned scene GLBs without replacing existing objects.
 * Blender uploads share the scene version sequence and carry the edited label.
 */
import { createReadStream } from 'node:fs';
import { createHash } from 'node:crypto';
import { listObjects, uploadFile, reserveObject, objectMetadata } from './r2.js';

export async function reserveSceneModel(sceneFolder, { edited = false } = {}) {
  if (!/^\d+-[a-zA-Z0-9_-]+$/.test(sceneFolder || '')) throw new Error('Invalid scene folder.');
  const prefix = `Cockpit3D-Files/${sceneFolder}/`;
  const pattern = new RegExp(`^(?:${sceneFolder}(?:-edited)?-v(\\d+)\\.(?:glb|jpg|jpeg|png)|\\.versions/v(\\d+)\\.json)$`, 'i');
  const objects = await listObjects(prefix);
  let version = objects.reduce((maximum, object) => {
    const match = object.key.slice(prefix.length).match(pattern);
    const number = match ? Number(match[1] || match[2]) : 0;
    return Number.isSafeInteger(number) ? Math.max(maximum, number) : maximum;
  }, 0) + 1;
  // Reserve before conversion: even downloaded-only jobs own their version.
  for (let attempt = 0; attempt < 20; attempt++, version++) {
    if (!Number.isSafeInteger(version)) throw new Error('Invalid model version.');
    const suffix = String(version).padStart(3, '0');
    const stem = `${sceneFolder}${edited ? '-edited' : ''}-v${suffix}`;
    try {
      await reserveObject(`${prefix}.versions/v${suffix}.json`, { stem, createdAt: new Date().toISOString() });
      return stem;
    } catch (error) {
      if (![409, 412].includes(error.$metadata?.httpStatusCode)) throw error;
    }
  }
  throw new Error('Model versions changed repeatedly. Please retry saving.');
}

// A repeat Save keeps its reserved name and never replaces different bytes.
export async function saveReservedFile(file, key) {
  const digest = createHash('sha256');
  for await (const chunk of createReadStream(file)) digest.update(chunk);
  const sha256 = digest.digest('hex');
  try {
    await uploadFile(file, key, { ifNoneMatch: '*', metadata: { sha256 } });
  } catch (error) {
    if (![409, 412].includes(error.$metadata?.httpStatusCode)) throw error;
    const existing = await objectMetadata(key);
    if (existing.Metadata?.sha256 !== sha256) throw new Error('This version already contains a different file.');
  }
  return key;
}

export async function saveSceneModel(file, sceneFolder, options = {}) {
  const stem = await reserveSceneModel(sceneFolder, options);
  return saveReservedFile(file, `Cockpit3D-Files/${sceneFolder}/${stem}.glb`);
}
