/** Purpose: Exercise missing-only migration, races, retry, MIME and source integrity offline. */
import test from 'node:test';
import assert from 'node:assert/strict';
import { Readable } from 'node:stream';
import { copyShared, validateMapping } from '../src/lib/storage/shared-copy.mjs';

const entry = { sourceKey: 'Cockpit3D-Files/.Showroom/a/points.ply', destinationKey: 'Showroom-data/a/points.ply' };
function store(initial = {}) {
  const data = new Map(Object.entries(initial).map(([key, body]) => [key, { body: Buffer.from(body), mime: 'application/octet-stream', etag: 'v1' }]));
  let writes = 0;
  return { data, get writes() { return writes; },
    async head(key) { const item = data.get(key); return item ? { etag: item.etag, bytes: item.body.length } : null; },
    async get(key, etag) { const item = data.get(key); assert.equal(item.etag, etag); return { body: Readable.from([item.body]), mime: item.mime }; },
    async putMissing(key, stream, meta) {
      if (data.has(key)) { stream.destroy(); throw { $metadata: { httpStatusCode: 412 } }; }
      const chunks = []; for await (const chunk of stream) chunks.push(chunk);
      data.set(key, { body: Buffer.concat(chunks), mime: meta.mime, etag: 'v2' }); writes += 1;
    },
  };
}
test('dry run reads source, never writes; apply and duplicate retry verify bytes', async () => {
  const source = store({ [entry.sourceKey]: 'all source points' }), destination = store();
  const run = apply => copyShared({ source, destination, entries: [entry], apply });
  assert.equal((await run(false))[0].status, 'planned'); assert.equal(destination.writes, 0);
  assert.equal((await run(true))[0].status, 'copied-verified');
  assert.equal((await run(true))[0].status, 'existing-verified'); assert.equal(destination.writes, 1);
});
test('different destination or MIME remains a conflict without overwrite', async () => {
  const source = store({ [entry.sourceKey]: 'original' }), destination = store({ [entry.destinationKey]: 'changed!' });
  assert.equal((await copyShared({ source, destination, entries: [entry], apply: true }))[0].status, 'conflict');
  destination.data.get(entry.destinationKey).body = Buffer.from('original');
  destination.data.get(entry.destinationKey).mime = 'text/plain';
  assert.equal((await copyShared({ source, destination, entries: [entry], apply: true }))[0].status, 'conflict');
  assert.equal(destination.writes, 0);
});
test('stale inventory and offline failure do not mutate destination; retry succeeds', async () => {
  const source = store({ [entry.sourceKey]: 'original' }), destination = store();
  assert.equal((await copyShared({ source, destination, entries: [{ ...entry, sourceEtag: 'old' }], apply: true }))[0].status, 'error');
  const get = source.get; source.get = async () => { throw Object.assign(new Error(), { code: 'ECONNRESET' }); };
  assert.equal((await copyShared({ source, destination, entries: [entry], apply: true }))[0].errorCode, 'ECONNRESET');
  assert.equal(destination.writes, 0); source.get = get;
  assert.equal((await copyShared({ source, destination, entries: [entry], apply: true }))[0].status, 'copied-verified');
});
test('conditional race verifies competing object instead of replacing it', async () => {
  const source = store({ [entry.sourceKey]: 'original' }), destination = store();
  destination.putMissing = async (key, stream) => {
    stream.destroy(); destination.data.set(key, { body: Buffer.from('other'), mime: 'application/octet-stream', etag: 'race' });
    throw { $metadata: { httpStatusCode: 412 } };
  };
  assert.equal((await copyShared({ source, destination, entries: [entry], apply: true }))[0].status, 'conflict');
});
test('reject traversal, encoded traversal, publication and ambiguous mapping', () => {
  for (const destinationKey of ['../private', 'Showroom-data/../secret', 'Showroom-data/%2e%2e/a', 'Showroom-data/a\\b', 'claude-design/published/a']) {
    assert.throws(() => validateMapping([{ ...entry, destinationKey }]));
  }
  assert.throws(() => validateMapping([entry, entry]));
});
