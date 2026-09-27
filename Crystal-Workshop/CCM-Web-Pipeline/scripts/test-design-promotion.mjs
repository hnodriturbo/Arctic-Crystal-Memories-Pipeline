/** Purpose: Verify immutable promotion receipts, repeatability and withheld manifests on failure. */
import test from 'node:test';
import assert from 'node:assert/strict';
import { Readable } from 'node:stream';
import { mkdtemp, writeFile, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { promotePackage, sha256 } from '../src/lib/claude-design/promotion.mjs';

test('manifest last, content identity stable, retries verify and preserve manifest', async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), 'ccm-promote-test-'));
  try {
    const file = path.join(root, 'index.html'); await writeFile(file, '<html>fixture</html>');
    const objects = new Map(), order = [];
    const store = {
      async putMissing(key, body, meta) {
        if (objects.has(key)) throw { $metadata: { httpStatusCode: 412 } };
        const chunks = []; if (Buffer.isBuffer(body)) chunks.push(body); else for await (const chunk of body) chunks.push(chunk);
        objects.set(key, { body: Buffer.concat(chunks), ...meta }); order.push(key);
      },
      async get(key) { const value = objects.get(key); return value ? { ...value, body: Readable.from([value.body]) } : null; },
    };
    const spec = { kind: 'design', variant: 'is-tablet', entryPath: 'example/index.html', files: [{ path: file, relativePath: 'example/index.html', role: 'source', mime: 'text/html' }], store };
    const first = await promotePackage(spec), second = await promotePackage(spec);
    assert.deepEqual(second, first); assert.equal(order.length, 2);
    assert.equal(order.at(-1), first.manifestKey);
    assert.equal(sha256(objects.get(first.manifestKey).body), first.manifestSha256);
    const sourceKey = order[0]; objects.get(sourceKey).body = Buffer.from('corrupted');
    await assert.rejects(promotePackage(spec), /conflicts/);
    // A new version with a failed upload never becomes discoverable as a manifest.
    await writeFile(file, '<html>new fixture</html>');
    store.putMissing = async () => { throw new Error('offline'); };
    await assert.rejects(promotePackage(spec), /offline/);
    assert.equal(order.length, 2);
  } finally { await rm(root, { recursive: true, force: true }); }
});
