/** Purpose: Authenticate normally and verify read-only order routes and denied writes without creating order/file data. */
import assert from 'node:assert/strict';
const base = process.env.VERIFY_BASE || 'http://127.0.0.1:3100';
const jar = new Map();
async function call(path, options = {}) {
  const response = await fetch(base + path, { ...options, redirect: 'manual', headers: { cookie: [...jar].map(([key, value]) => `${key}=${value}`).join('; '), ...options.headers } });
  for (const line of response.headers.getSetCookie()) { const pair = line.split(';')[0], index = pair.indexOf('='); jar.set(pair.slice(0, index), pair.slice(index + 1)); }
  return response;
}
assert.ok([302, 303, 307, 401, 403].includes((await call('/api/production-orders')).status));
assert.equal((await call('/api/production-orders/dxf')).status, 403);
assert.equal((await call('/api/production-orders/dxf', { method: 'POST', headers: { Origin: base }, body: 'invalid' })).status, 403);
const csrf = await (await call('/api/auth/csrf')).json();
await call('/api/auth/callback/credentials', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: new URLSearchParams({ csrfToken: csrf.csrfToken, email: process.env.AGENT_EMAIL, password: process.env.AGENT_PASSWORD, callbackUrl: base + '/' }) });
assert.ok((await (await call('/api/auth/session')).json()).user?.id);
const response = await call('/api/production-orders'); assert.equal(response.status, 200);
assert.match(response.headers.get('cache-control'), /no-store/);
const { orders } = await response.json();
for (const order of orders) {
  const response = await call('/api/production-orders?snapshot=' + encodeURIComponent(order.snapshotKey)); assert.equal(response.status, 200);
  const detail = await response.json(); assert.equal(detail.order.id, order.id); assert.ok(Array.isArray(detail.versions));
}
assert.equal((await call('/api/production-orders?snapshot=..%2Fsecret')).status, 422);
assert.equal((await call('/api/production-orders/dxf', { method: 'POST', headers: { Origin: 'https://foreign.invalid' }, body: 'invalid' })).status, 403);
const logout = await (await call('/api/auth/csrf')).json();
await call('/api/auth/signout', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: new URLSearchParams({ csrfToken: logout.csrfToken, callbackUrl: base + '/login' }) });
console.log(JSON.stringify({ status: 'PASS', orders: orders.length, guestDenied: true, foreignWriteDenied: true, traversalDenied: true, writes: 0 }));
