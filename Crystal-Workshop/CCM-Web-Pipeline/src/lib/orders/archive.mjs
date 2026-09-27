/** Purpose: Read canonical order identities from private recovery evidence without inferring live financial status. */
import { createHash } from 'node:crypto';

export function stableJson(value) {
  if (Array.isArray(value)) return `[${value.map(stableJson).join(',')}]`;
  if (value && typeof value === 'object') return `{${Object.entries(value).filter(([, v]) => v !== undefined).sort(([a], [b]) => a.localeCompare(b)).map(([k, v]) => `${JSON.stringify(k)}:${stableJson(v)}`).join(',')}}`;
  return JSON.stringify(value);
}
export function snapshotIdentity(key) {
  const match = String(key).match(/^((?:(?:web-orders\/)?(?:user-orders|guest-orders)|salescloud-orders|cash-orders)\/([A-Za-z0-9][A-Za-z0-9_-]{1,79}))\/recovery\/v1\/[A-Za-z0-9_-]+\.json$/);
  if (!match || key.includes('..')) throw Error('Invalid order snapshot');
  return { root: match[1], orderNumber: match[2] };
}
export function readIdentity(document, key) {
  const identity = snapshotIdentity(key);
  const order = document?.payload?.order;
  if (document.format !== 'acm-order-recovery' || document.schemaVersion !== 1 || document.checksumAlgorithm !== 'sha256' || !order?.id || !Array.isArray(document.payload.orderItems)) throw Error('Unsupported order evidence');
  if (createHash('sha256').update(stableJson(document.payload)).digest('hex') !== document.checksum) throw Error('Order checksum mismatch');
  if (document.orderId !== order.id || document.orderNumber !== order.orderNumber || order.orderNumber !== identity.orderNumber) throw Error('Order identity mismatch');
  if (!['ONLINE', 'IN_STORE'].includes(order.source)) throw Error('Unknown order channel');
  if ((identity.root.startsWith('cash-orders/') && (order.source !== 'IN_STORE' || order.paymentMethodType !== 'CASH')) || (order.paymentMethodType === 'CASH' && !identity.root.startsWith('cash-orders/')) || (identity.root.startsWith('salescloud-orders/') && order.source !== 'IN_STORE') || (identity.root.startsWith('web-orders/') && order.source !== 'ONLINE')) throw Error('Order channel mismatch');
  if (![document.capturedAt, order.createdAt].every(date => typeof date === 'string' && Number.isFinite(Date.parse(date)))) throw Error('Invalid evidence date');
  return { id: order.id, orderNumber: order.orderNumber, channel: order.source, paymentMethod: order.paymentMethodType ?? null, capturedAt: document.capturedAt, orderedAt: order.createdAt, itemCount: document.payload.orderItems.length, snapshotKey: key };
}
export function orderToken(orderId) {
  if (typeof orderId !== 'string' || !orderId || orderId.length > 200) throw Error('Invalid order identity');
  return createHash('sha256').update(orderId).digest('hex');
}
export async function boundedBytes(body, limit) {
  const chunks = []; let length = 0;
  for await (const chunk of body) { length += chunk.length; if (length > limit) throw Error('Object exceeds limit'); chunks.push(chunk); }
  return Buffer.concat(chunks);
}
