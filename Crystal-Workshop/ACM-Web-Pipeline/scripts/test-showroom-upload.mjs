/** Purpose: Verify same-origin GLB upload guards, bounded input, immutable destinations and temporary-file cleanup without using R2. */
import assert from 'node:assert/strict';
import vm from 'node:vm';
import * as fs from 'node:fs/promises';
import * as disk from 'node:fs';
import * as stream from 'node:stream';
import * as promises from 'node:stream/promises';
import * as crypto from 'node:crypto';
import path from 'node:path';
import os from 'node:os';

const root = await fs.mkdtemp(path.join(os.tmpdir(), 'acm-upload-tests-'));
let user = null; const writes = [];
try {
  const dependencies = {
    '@/auth': { auth: async () => user },
    '@/lib/storage/scene-model-names': { saveSceneModel: async (file, folder, options) => {
      assert.equal(options.edited, true);
      const key = `Cockpit3D-Files/${folder}/${folder}-edited-v001.glb`;
      writes.push({ key, bytes: await fs.readFile(file) });
      return key;
    } },
    '@/lib/paths': { safeFileName: (name) => path.basename(name) },
    'node:fs/promises': fs, 'node:fs': disk, 'node:stream': stream,
    'node:stream/promises': promises, 'node:crypto': crypto,
    'node:path': { default: path }, 'node:os': { default: { tmpdir: () => root } },
  };
  const context = vm.createContext({ Buffer, Response, URL });
  const source = new vm.SourceTextModule(await fs.readFile(new URL('../src/app/api/reconstruct/upload/route.js', import.meta.url), 'utf8'), { context });
  await source.link((name) => {
    const values = dependencies[name]; assert.ok(values, name);
    return new vm.SyntheticModule(Object.keys(values), function () { for (const [key, value] of Object.entries(values)) this.setExport(key, value); }, { context });
  });
  await source.evaluate();
  const bytes = Buffer.alloc(24); bytes.writeUInt32LE(0x46546c67, 0); bytes.writeUInt32LE(2, 4); bytes.writeUInt32LE(24, 8); bytes.writeUInt32LE(4, 12); bytes.writeUInt32LE(0x4e4f534a, 16); bytes.write('{}  ', 20);
  // Requests model browser headers without opening a local web server.
  const request = (patch = {}, body = bytes) => new Request('https://workshop.acm.is/api/reconstruct/upload', { method: 'POST', headers: { host: 'workshop.acm.is', origin: 'https://workshop.acm.is', 'x-scene-folder': '123-scene', 'x-filename': 'portrait.glb', ...patch }, body });
  assert.equal((await source.namespace.POST(request())).status, 401);
  user = { user: { id: 'test-operator' } };
  assert.equal((await source.namespace.POST(request({ origin: 'https://unrelated.example' }))).status, 403);
  assert.equal((await source.namespace.POST(request({ 'x-scene-folder': '../other' }))).status, 400);
  assert.equal((await source.namespace.POST(request({ 'content-length': String(65 * 1024 * 1024) }))).status, 413);
  assert.equal((await source.namespace.POST(request({}, Buffer.from('invalid')))).status, 400);
  assert.equal(writes.length, 0); assert.equal((await fs.readdir(root)).length, 0);
  const result = await source.namespace.POST(request()); assert.equal(result.status, 200);
  assert.equal(writes.length, 1); assert.deepEqual(writes[0].bytes, bytes);
  assert.ok(writes[0].key.startsWith('Cockpit3D-Files/123-scene/'));
  assert.equal((await fs.readdir(root)).length, 0);
  console.log('PASS: upload auth/origin, folders, size, GLB header, exact R2 bytes and temporary cleanup.');
} finally { await fs.rm(root, { recursive: true, force: true }); }
