/** Purpose: Offline identity, channel, immutable DXF retry, readback and cross-order isolation checks. */
import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdtemp, writeFile, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { Readable } from 'node:stream';
import { S3Client } from '@aws-sdk/client-s3';
import { stableJson, readIdentity, snapshotIdentity, orderToken } from '../src/lib/orders/archive.mjs';
import { saveDxf, versions, downloadDxf } from '../src/lib/orders/storage.mjs';
const key = 'salescloud-orders/CCM-123/recovery/v1/20260926.json';
function fixture() {
  const payload = { order: { id: 'canonical-123', orderNumber: 'CCM-123', source: 'IN_STORE', status: 'CONFIRMED', paymentStatus: 'PAID_IN_STORE', createdAt: '2026-09-26T12:00:00Z' }, orderItems: [] };
  return { format: 'acm-order-recovery', schemaVersion: 1, checksumAlgorithm: 'sha256', checksum: createHash('sha256').update(stableJson(payload)).digest('hex'), orderId: payload.order.id, orderNumber: payload.order.orderNumber, capturedAt: '2026-09-26T13:00:00Z', payload };
}
test('canonical identity excludes payment claims; corruption, channel mismatch and traversal fail', () => {
  const doc = fixture();
  assert.equal(readIdentity(doc, key).id, 'canonical-123');
  assert.equal('paid' in readIdentity(doc, key), false);
  assert.throws(() => readIdentity(doc, key.replace('salescloud-orders', 'web-orders/user-orders')), /channel/);
  doc.payload.order.id = 'different'; assert.throws(() => readIdentity(doc, key), /checksum/);
  assert.throws(() => snapshotIdentity('../' + key));
  assert.notEqual(orderToken('a/b'), orderToken('a-b'));
});
test('cash evidence is separate from SalesCloud and cannot be reclassified by its path', () => {
  const doc = fixture(); doc.payload.order.paymentMethodType = 'CASH';
  doc.checksum = createHash('sha256').update(stableJson(doc.payload)).digest('hex');
  assert.equal(readIdentity(doc, key.replace('salescloud-orders', 'cash-orders')).paymentMethod, 'CASH');
  assert.throws(() => readIdentity(doc, key), /channel/);
  assert.throws(() => readIdentity(fixture(), key.replace('salescloud-orders', 'cash-orders')), /channel/);
});
test('retained unpaid drafts and tests remain readable evidence, excluded from production writes', async () => {
  for (const patch of [{ status: 'OPEN', paymentStatus: 'UNPAID' }, { isTestOrder: true }, { status: 'REFUNDED' }]) {
    const doc = fixture(); Object.assign(doc.payload.order, patch);
    doc.checksum = createHash('sha256').update(stableJson(doc.payload)).digest('hex');
    const order = readIdentity(doc, key);
    assert.equal(order.productionEligible, false);
    await assert.rejects(saveDxf({ order }), /cannot receive/);
  }
});
test('DXF manifest last, repeat idempotent, versions isolated; corrupt readback never creates manifest', async () => {
  const temporary = await mkdtemp(path.join(os.tmpdir(), 'ccm-orders-test-'));
  const originalSend = S3Client.prototype.send;
  const oldEnv = { ...process.env };
  const objects = new Map(); const calls = [];
  let corrupt = false;
  Object.assign(process.env, { R2_PIPELINE_BUCKET_NAME: 'ccm-workshop', R2_PIPELINE_ENDPOINT: 'https://test.invalid', R2_PIPELINE_ACCESS_KEY_ID: 'test', R2_PIPELINE_SECRET_ACCESS_KEY: 'test' });
  S3Client.prototype.send = async function(command) {
    const { Key, Body, Prefix } = command.input;
    const type = command.constructor.name;
    calls.push({ type, key: Key });
    if (type === 'PutObjectCommand') {
      assert.equal(command.input.IfNoneMatch, '*');
      if (objects.has(Key)) { Body?.destroy?.(); throw { $metadata: { httpStatusCode: 412 } }; }
      const bytes = typeof Body === 'string' ? Buffer.from(Body) : Buffer.concat(await Array.fromAsync(Body));
      objects.set(Key, { bytes, mime: command.input.ContentType }); return {};
    }
    if (type === 'GetObjectCommand') {
      const object = objects.get(Key); if (!object) throw Error('Missing object');
      return { Body: Readable.from([corrupt && Key.endsWith('.dxf') ? Buffer.from('corrupt') : object.bytes], { objectMode: false }), ContentLength: object.bytes.length, ContentType: object.mime, ETag: '"same-etag"' };
    }
    if (type === 'ListObjectsV2Command') return { Contents: [...objects.keys()].filter(key => key.startsWith(Prefix)).map(Key => ({ Key })) };
    throw Error('Unexpected operation');
  };
  try {
    const file = path.join(temporary, 'file.dxf'); const body = Buffer.from('0\nSECTION\n2\nENTITIES\n0\nENDSEC\n0\nEOF\n');
    await writeFile(file, body);
    const order = readIdentity(fixture(), key);
    const input = { order, path: file, sha256: createHash('sha256').update(body).digest('hex'), bytes: body.length, filename: 'file.dxf', userId: 'operator' };
    const first = await saveDxf(input);
    assert.deepEqual(await saveDxf(input), first);
    assert.equal(objects.size, 2);
    assert.ok(calls.findIndex(row => row.type === 'GetObjectCommand' && row.key.endsWith('.dxf')) < calls.findIndex(row => row.type === 'PutObjectCommand' && row.key.endsWith('.json')));
    assert.equal((await versions(order)).length, 1);
    const downloaded = await downloadDxf(order, input.sha256);
    assert.deepEqual(Buffer.from(await new Response(downloaded.body).arrayBuffer()), body);
    assert.equal((await versions({ ...order, id: 'another-order' })).length, 0);
    await assert.rejects(downloadDxf(order, '../bad'), /Invalid version/);
    objects.clear(); corrupt = true;
    await assert.rejects(saveDxf(input), /readback/);
    assert.equal([...objects.keys()].some(key => key.endsWith('.json')), false);
  } finally {
    S3Client.prototype.send = originalSend;
    for (const name of Object.keys(process.env)) if (!(name in oldEnv)) delete process.env[name];
    Object.assign(process.env, oldEnv);
    await rm(temporary, { recursive: true, force: true });
  }
});
