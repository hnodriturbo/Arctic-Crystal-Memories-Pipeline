/**
 * Purpose: Missing-only shared migration with conditional reads/writes and body verification.
 * Stores are injected so races, offline retries and conflicts can be tested without R2.
 */
import { createHash } from 'node:crypto';
import { createReadStream, createWriteStream } from 'node:fs';
import { mkdtemp, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { Transform } from 'node:stream';
import { pipeline } from 'node:stream/promises';

export function validKey(key) {
  return typeof key === 'string' && key.length > 0 && key.length <= 1024 &&
    !/[\\\x00-\x1f\x7f]/.test(key) && !key.startsWith('/') &&
    !key.split('/').some(part => part === '..' || part === '.') &&
    !/%(?:2e|2f|5c)/i.test(key);
}

export function validateMapping(entries) {
  if (!Array.isArray(entries)) throw new Error('Mapping must be an array.');
  const destinations = new Set();
  for (const entry of entries) {
    if (!validKey(entry.sourceKey) || !validKey(entry.destinationKey) ||
        !['Showroom-data/', 'claude-design/sources/', 'claude-design/videos/'].some(p => entry.destinationKey.startsWith(p))) {
      throw new Error('Unsafe migration mapping.');
    }
    if (destinations.has(entry.destinationKey)) throw new Error('Duplicate destination.');
    destinations.add(entry.destinationKey);
  }
  return entries;
}

async function digest(body, file) {
  const hash = createHash('sha256');
  let bytes = 0;
  const meter = new Transform({ transform(chunk, encoding, done) {
    bytes += chunk.length; hash.update(chunk); done(null, chunk);
  } });
  if (file) await pipeline(body, meter, createWriteStream(file, { flags: 'wx' }));
  else for await (const chunk of body) { bytes += chunk.length; hash.update(chunk); }
  return { sha256: hash.digest('hex'), bytes };
}

/** No overwrite/delete capability is exposed; retries reverify already copied bodies. */
export async function copyShared({ source, destination, entries, apply = false, onResult = async () => {} }) {
  validateMapping(entries);
  const directory = await mkdtemp(path.join(os.tmpdir(), 'ccm-shared-copy-'));
  const results = [];
  try {
    for (let index = 0; index < entries.length; index += 1) {
      const entry = entries[index];
      const file = path.join(directory, String(index));
      let result = { ...entry };
      try {
        const head = await source.head(entry.sourceKey);
        if (!head?.etag) throw new Error('Source missing or unversioned.');
        // An inventory ETag detects a source edit between planning and execution.
        if (entry.sourceEtag && entry.sourceEtag !== head.etag) throw new Error('Source changed since inventory.');
        if (head.bytes > 5_000_000_000) throw new Error('Object exceeds single-copy limit.');
        const original = await source.get(entry.sourceKey, head.etag);
        const expected = await digest(original.body, file);
        if (expected.bytes !== head.bytes) throw new Error('Source size changed.');
        const mime = original.mime || 'application/octet-stream';
        result = { ...result, sourceEtag: head.etag, ...expected, mime };
        let existing = await destination.head(entry.destinationKey);
        let copied = false;
        if (!existing && apply) {
          try {
            await destination.putMissing(entry.destinationKey, createReadStream(file), { ...expected, mime });
            copied = true;
          } catch (error) {
            // Another writer winning the reservation is checked as existing content.
            if (error.$metadata?.httpStatusCode !== 412) throw error;
          }
          existing = await destination.head(entry.destinationKey);
          if (!existing) throw new Error('Destination missing after upload.');
        }
        if (!existing) result.status = 'planned';
        else {
          const remote = await destination.get(entry.destinationKey, existing.etag);
          const actual = await digest(remote.body);
          result.status = actual.sha256 === expected.sha256 && actual.bytes === expected.bytes &&
            remote.mime === mime ? (copied ? 'copied-verified' : 'existing-verified') : 'conflict';
          if (result.status === 'conflict') result.destinationSha256 = actual.sha256;
        }
      } catch (error) {
        result.status = 'error';
        // Avoid serializing SDK requests, credentials or signed URLs into reports.
        result.errorCode = error.$metadata?.httpStatusCode || error.code || 'COPY_FAILED';
      } finally {
        await rm(file, { force: true });
      }
      results.push(result);
      await onResult(result);
    }
    return results;
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
}
