/** Purpose: Private read-only order archive and immutable order-linked production DXF storage. */
import { createReadStream } from 'node:fs';
import { createHash } from 'node:crypto';
import { Readable } from 'node:stream';
import { S3Client, ListObjectsV2Command, GetObjectCommand, PutObjectCommand } from '@aws-sdk/client-s3';
import { snapshotIdentity, readIdentity, orderToken, boundedBytes } from './archive.mjs';

function store(group, expectedBucket) {
  if (process.env[`${group}_BUCKET_NAME`] !== expectedBucket || !['ENDPOINT', 'ACCESS_KEY_ID', 'SECRET_ACCESS_KEY'].every(k => process.env[`${group}_${k}`])) throw Error('Storage is not configured');
  const client = new S3Client({ region: 'auto', endpoint: process.env[`${group}_ENDPOINT`], credentials: { accessKeyId: process.env[`${group}_ACCESS_KEY_ID`], secretAccessKey: process.env[`${group}_SECRET_ACCESS_KEY`] } });
  return { client, Bucket: expectedBucket };
}
async function list({ client, Bucket }, Prefix) {
  const rows = []; let token;
  do {
    const page = await client.send(new ListObjectsV2Command({ Bucket, Prefix, ContinuationToken: token }));
    rows.push(...(page.Contents || []));
    token = page.IsTruncated ? page.NextContinuationToken : undefined;
    if (page.IsTruncated && !token) throw Error('Incomplete listing');
  } while (token);
  return rows;
}
async function json(storage, Key) {
  const object = await storage.client.send(new GetObjectCommand({ Bucket: storage.Bucket, Key }));
  return JSON.parse((await boundedBytes(object.Body, 16 * 1024 * 1024)).toString('utf8'));
}
export async function getOrder(snapshotKey) {
  snapshotIdentity(snapshotKey);
  const source = store('R2_ORDERS', 'ccm-orders');
  try { return readIdentity(await json(source, snapshotKey), snapshotKey); }
  finally { source.client.destroy(); }
}
export async function listOrders() {
  const source = store('R2_ORDERS', 'ccm-orders');
  try {
    const latest = new Map();
    for (const object of await list(source, '')) {
      let identity; try { identity = snapshotIdentity(object.Key); } catch { continue; }
      const version = object.Key.split('/').at(-1);
      const old = latest.get(identity.orderNumber);
      if (!old || version > old.version || (version === old.version && object.Key.startsWith('web-orders/'))) latest.set(identity.orderNumber, { key: object.Key, version });
    }
    const orders = [];
    for (const { key } of latest.values()) orders.push(readIdentity(await json(source, key), key));
    return orders.filter(order => order.productionEligible).sort((a, b) => b.orderedAt.localeCompare(a.orderedAt));
  } finally { source.client.destroy(); }
}
function manifestKey(orderId, hash) {
  if (!/^[a-f0-9]{64}$/.test(hash)) throw Error('Invalid version');
  return `production-orders/${orderToken(orderId)}/versions/${hash}.json`;
}
function validateManifest(value, order, key) {
  if (typeof value.filename !== 'string' || value.filename.length > 200 || /[\\/\x00-\x1f\x7f]/.test(value.filename) || typeof value.etag !== 'string' || !value.etag || typeof value.createdAt !== 'string') throw Error('Invalid DXF metadata');
  if (value.schemaVersion !== 1 || value.orderId !== order.id || value.orderNumber !== order.orderNumber || value.channel !== order.channel || value.review !== 'OPERATOR_REVIEWED' || key !== manifestKey(order.id, value.sha256) || value.fileKey !== `production-orders/${orderToken(order.id)}/files/${value.sha256}.dxf` || !Number.isSafeInteger(value.bytes) || value.bytes <= 0 || value.bytes > 512 * 1024 * 1024 || !Number.isFinite(Date.parse(value.createdAt))) throw Error('Invalid DXF manifest');
  return value;
}
export async function versions(order) {
  const target = store('R2_PIPELINE', 'ccm-workshop');
  try {
    const rows = [];
    for (const object of await list(target, `production-orders/${orderToken(order.id)}/versions/`)) rows.push(validateManifest(await json(target, object.Key), order, object.Key));
    return rows.sort((a, b) => b.createdAt.localeCompare(a.createdAt));
  } finally { target.client.destroy(); }
}
async function verifyBody(target, key, expectedHash, expectedBytes) {
  const object = await target.client.send(new GetObjectCommand({ Bucket: target.Bucket, Key: key }));
  const hash = createHash('sha256'); let bytes = 0;
  for await (const chunk of object.Body) { bytes += chunk.length; if (bytes > expectedBytes) throw Error('DXF readback size mismatch'); hash.update(chunk); }
  if (bytes !== expectedBytes || hash.digest('hex') !== expectedHash || object.ContentType !== 'application/dxf') throw Error('DXF readback mismatch');
  return object.ETag;
}
export async function saveDxf({ order, path, sha256, bytes, filename, userId }) {
  if (!order.productionEligible) throw Error('Archived draft, test or unpaid order cannot receive production files');
  const target = store('R2_PIPELINE', 'ccm-workshop');
  const key = manifestKey(order.id, sha256);
  const fileKey = `production-orders/${orderToken(order.id)}/files/${sha256}.dxf`;
  try {
    // Every version is create-only. A manifest becomes visible only after complete body readback.
    try { await target.client.send(new PutObjectCommand({ Bucket: target.Bucket, Key: fileKey, Body: createReadStream(path), ContentLength: bytes, ContentType: 'application/dxf', IfNoneMatch: '*', Metadata: { sha256 } })); }
    catch (error) { if (error.$metadata?.httpStatusCode !== 412) throw error; }
    const etag = await verifyBody(target, fileKey, sha256, bytes);
    const value = { schemaVersion: 1, orderId: order.id, orderNumber: order.orderNumber, channel: order.channel, sha256, bytes, fileKey, etag, filename, createdAt: new Date().toISOString(), reviewedBy: userId, review: 'OPERATOR_REVIEWED', snapshotKey: order.snapshotKey };
    try { await target.client.send(new PutObjectCommand({ Bucket: target.Bucket, Key: key, Body: JSON.stringify(value), ContentType: 'application/json', IfNoneMatch: '*' })); }
    catch (error) { if (error.$metadata?.httpStatusCode !== 412) throw error; }
    const saved = validateManifest(await json(target, key), order, key);
    if (saved.sha256 !== sha256 || saved.bytes !== bytes || saved.etag !== etag) throw Error('DXF version conflict');
    return saved;
  } finally { target.client.destroy(); }
}
export async function downloadDxf(order, hash) {
  const target = store('R2_PIPELINE', 'ccm-workshop');
  try {
    const key = manifestKey(order.id, hash);
    const version = validateManifest(await json(target, key), order, key);
    const object = await target.client.send(new GetObjectCommand({ Bucket: target.Bucket, Key: version.fileKey, IfMatch: version.etag }));
    if (object.ContentLength !== version.bytes || object.ContentType !== 'application/dxf') { object.Body.destroy(); throw Error('Stored DXF differs'); }
    object.Body.once('close', () => target.client.destroy());
    return { body: Readable.toWeb(object.Body), bytes: version.bytes, filename: `${order.orderNumber}-${hash.slice(0, 12)}.dxf`, sha256: hash };
  } catch (error) { target.client.destroy(); throw error; }
}
