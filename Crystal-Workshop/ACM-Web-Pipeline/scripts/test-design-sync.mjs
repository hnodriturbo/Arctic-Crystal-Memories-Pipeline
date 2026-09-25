/** Purpose: Verify safe two-way sync against real temporary files and a conditional in-memory object store. */
import assert from 'node:assert/strict';
import path from 'node:path';
import os from 'node:os';
import { createHash } from 'node:crypto';
import { mkdtemp, mkdir, readFile, writeFile, rm, stat } from 'node:fs/promises';
import { syncTree, validCollection, validRelative } from '../src/lib/claude-design/sync-engine.mjs';
const root = await mkdtemp(path.join(os.tmpdir(), 'ccm-sync-test-'));
const hash = b => createHash('sha256').update(b).digest('hex');
const objects = new Map(); const archives = [];
const key = 'claude-design/sources/demo/a.txt';
const put = (k, text, metadata = true) => objects.set(k, { body: Buffer.from(text), hash: metadata ? hash(text) : undefined, etag: hash(text), size: Buffer.byteLength(text) });
const store = {
 async list(prefix) { return [...objects.keys()].filter(key => key.startsWith(prefix)).map(key => ({ key })); },
 async head(key) { return objects.get(key) || null; },
 async download(key, file, etag) { assert.equal(objects.get(key).etag, etag); await writeFile(file, objects.get(key).body); },
 async upload(key, file, digest, etag) { assert.equal(objects.get(key)?.etag, etag); const body = await readFile(file); assert.equal(hash(body), digest); put(key, body); },
 async archive(key, old) { assert.equal(objects.get(key).etag, old.etag); archives.push(objects.get(key).body.toString()); }
};
const sync = extra => syncTree({ root, store, ...extra });
try {
 await mkdir(path.join(root, 'demo')); await writeFile(path.join(root, 'demo/a.txt'), 'AAAA');
 assert.equal((await sync()).uploaded, 1);
 assert.equal((await sync()).unchanged, 1);
 await writeFile(path.join(root, 'demo/a.txt'), 'BBBB');
 assert.equal((await sync()).uploaded, 1); assert.deepEqual(archives, ['AAAA']);
 put(key, 'CCCC', false); // Same bytes, no custom metadata: must download and hash.
 assert.equal((await sync()).fetched, 1); assert.equal(await readFile(path.join(root, 'demo/a.txt'), 'utf8'), 'CCCC');
 assert.equal(await readFile(path.join(root, '.workshop-sync/history', hash('BBBB'), 'demo/a.txt'), 'utf8'), 'BBBB');
 await writeFile(path.join(root, 'demo/a.txt'), 'DDDD'); put(key, 'EEEE');
 assert.equal((await sync()).conflicts, 1); assert.equal(await readFile(path.join(root, 'demo/a.txt'), 'utf8'), 'DDDD'); assert.equal(objects.get(key).body.toString(), 'EEEE');
 assert.equal(await readFile(path.join(root, '.workshop-sync/conflicts', hash('EEEE'), 'demo/a.txt'), 'utf8'), 'EEEE');
 // Resolve deliberately by choosing remote, then baseline converges.
 await writeFile(path.join(root, 'demo/a.txt'), 'EEEE'); assert.equal((await sync()).unchanged, 1);
 await rm(path.join(root, 'demo/a.txt')); assert.equal((await sync()).fetched, 1);
 objects.delete(key); assert.equal((await sync()).uploaded, 1);
 put('claude-design/sources/new/remote.txt', 'new'); assert.equal((await sync()).fetched, 1);
 put('claude-design/sources/empty/', ''); await sync(); assert.ok((await stat(path.join(root, 'empty'))).isDirectory());
 for (const name of ['../escape','..','C:\\escape','bad/name','.env','con','name.','exported-videos']) assert.equal(validCollection(name), false, name);
 assert.equal(validRelative('demo/../../escape'), false); assert.equal(validCollection('Nýtt safn'), true);
 put('claude-design/sources/../../escape.txt', 'bad'); assert.equal((await sync()).skipped, 1);
 put('claude-design/sources/dry/a.txt', 'dry'); const report = await sync({ dryRun: true }); assert.equal(report.fetched, 1); await assert.rejects(readFile(path.join(root, 'dry/a.txt')));
 await writeFile(path.join(root, '.workshop-sync/lock'), ''); await assert.rejects(sync(), /already running/); await rm(path.join(root, '.workshop-sync/lock'));
 // A changed R2 object between HEAD and PUT must stop without overwriting it.
 await writeFile(path.join(root, 'demo/a.txt'), 'FFFF');
 const racing = { ...store, async archive(key, old) { await store.archive(key, old); put(key, 'RACE'); } };
 await assert.rejects(syncTree({ root, store: racing })); assert.equal(objects.get(key).body.toString(), 'RACE');
 console.log('DESIGN_SYNC_TESTS_OK: same-size edits, remote edits, conflicts, history, new folders, restore missing, dry run, lock, traversal, concurrent R2 edit');
} finally { await rm(root, { recursive: true, force: true }); }
