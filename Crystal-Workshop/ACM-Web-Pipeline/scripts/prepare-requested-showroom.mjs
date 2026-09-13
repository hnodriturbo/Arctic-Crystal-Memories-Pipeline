/**
 * Purpose: Run the two owner-requested scene pairs through the deployed website APIs.
 * Execute on the VPS with its private environment; never print session credentials.
 */
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import pg from 'pg';
import { encode } from 'next-auth/jwt';

const database = new pg.Client({ connectionString: process.env.DATABASE_URL });
await database.connect();
try {
  const user = (await database.query('SELECT id, role FROM users WHERE "isActive"=true AND "mustChangePassword"=false ORDER BY "createdAt" LIMIT 1')).rows[0];
  assert.ok(user, 'An existing active operator is required');
  const salt = '__Secure-authjs.session-token';
  const token = await encode({ secret: process.env.AUTH_SECRET, salt, maxAge: 3600, token: { sub: user.id, id: user.id, role: user.role, mustChangePassword: false } });
  const headers = { host: 'workshop.acm.is', origin: 'https://workshop.acm.is', 'x-forwarded-host': 'workshop.acm.is', 'x-forwarded-proto': 'https', cookie: salt + '=' + token, 'content-type': 'application/json' };
  // Invoke exactly the authenticated endpoints used by the browser, with no local candidate inputs.
  async function post(route, body) {
    const response = await fetch('http://127.0.0.1:3003' + route, { method: 'POST', headers, body: JSON.stringify(body) });
    assert.equal(response.status, 200, route + ': ' + response.status);
    return response;
  }
  const manifest = [];
  for (const name of ['75572-jon-thor', '76579-pabbi-baby']) {
    const prefix = 'Cockpit3D-Files/' + name + '/' + name;
    const pair = await (await post('/api/reconstruct/scenes', { exportKey: prefix + '.dxf', sceneKey: prefix + '.cockpit' })).json();
    console.log('Imported fresh R2 pair: ' + name);
    const response = await post('/api/reconstruct', { file: pair.file, values: { texture_from: pair.texture, sample_rate: 1, limit: 0, dedupe: false } });
    let buffer = '', job, done;
    for await (const chunk of response.body) {
      buffer += Buffer.from(chunk).toString('utf8');
      let end;
      while ((end = buffer.indexOf('\n\n')) >= 0) {
        const block = buffer.slice(0, end); buffer = buffer.slice(end + 2);
        if (!block.startsWith('data: ')) continue;
        const event = JSON.parse(block.slice(6));
        if (event.type === 'result') job = event.job;
        if (event.type === 'done') done = event.code;
        if (event.type === 'error') throw new Error(event.message);
        if (event.line) console.log(event.line);
      }
    }
    assert.equal(done, 0); assert.ok(job?.files?.glb);
    const published = await (await post('/api/reconstruct/publish', { file: job.files.glb, sceneFolder: pair.sceneFolder })).json();
    manifest.push({ name, sourceKeys: pair.sourceKeys, job, published });
    await fs.writeFile('/home/hreidar/apps/acm-pipeline/shared/requested-showroom-20260913.json', JSON.stringify(manifest, null, 2), { mode: 0o600 });
    console.log('Saved private R2 GLB: ' + published.key);
  }
} finally { await database.end(); }
