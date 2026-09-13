/** Purpose: Verify storage scopes, live browser authorization, and isolated temporary expiry without real R2 credentials. */
import assert from 'node:assert/strict';
import vm from 'node:vm';
import * as fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import { createTemporaryWorkspace } from '../src/lib/temporary-workspace.js';
import { STORAGE_AREAS, allowedStorageKey } from '../src/lib/storage/browser-scope.js';

for (const key of ['Cockpit3D-Files/123-scene/model.glb', 'converter-jobs/a/model.dxf', 'uploads/file.glb']) assert.ok(allowedStorageKey(key));
for (const key of ['private/customer.glb', 'Cockpit3D-Files/../private.glb', 'uploads/../secret', 'jobs\\secret', null]) assert.equal(allowedStorageKey(key), false);
const root = await fs.mkdtemp(path.join(os.tmpdir(), 'acm-workflow-test-'));
try {
  const old = await createTemporaryWorkspace(root, { sourceKeys: ['Cockpit3D-Files/123-scene/a.dxf'] });
  await fs.writeFile(path.join(old.directory, '.workshop-temp.json'), JSON.stringify({ owner: 'workshop-temporary-v1', created: Date.now() - 8 * 86400000 }));
  const preserved = path.join(root, 'tmp', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa');
  await fs.mkdir(preserved); await fs.writeFile(path.join(preserved, 'original.txt'), 'preserve');
  const fresh = await createTemporaryWorkspace(root);
  await assert.rejects(fs.stat(old.directory), {code:'ENOENT'});
  assert.equal(await fs.readFile(path.join(preserved,'original.txt'),'utf8'),'preserve');
  assert.ok((await fs.stat(fresh.directory)).isDirectory());

  let signedIn = false; let listed = 0;
  const context = vm.createContext({ Response, URL });
  const dependencies = {
    'node:path': { default:path },
    '@/auth': {auth:async()=>signedIn ? {user:{id:'test-operator'}} : null},
    '@/lib/storage/browser-scope': {STORAGE_AREAS,allowedStorageKey},
    '@/lib/storage/r2': {
      listObjects:async prefix=> { listed++; return [{key:prefix+'123-scene/a.glb',name:'a.glb',bytes:24},{key:prefix+'root.glb',name:'root.glb',bytes:24}]; },
      presignDownload:async key=>'https://download.example/'+key,
    },
  };
  const module = new vm.SourceTextModule(await fs.readFile(new URL('../src/app/api/r2/browser/route.js',import.meta.url),'utf8'),{context});
  await module.link(name=>{const values=dependencies[name];assert.ok(values,name);return new vm.SyntheticModule(Object.keys(values),function(){for(const [key,value]of Object.entries(values))this.setExport(key,value);},{context});});
  await module.evaluate();
  const get = query=>module.namespace.GET(new Request('https://workshop.example/api/r2/browser?'+query));
  assert.equal((await get('prefix=Cockpit3D-Files/')).status,401); assert.equal(listed,0);
  signedIn=true;
  assert.equal((await get('prefix=private/')).status,400);
  const listing=await (await get('prefix=Cockpit3D-Files/')).json();
  assert.deepEqual(listing.folders,['Cockpit3D-Files/123-scene/']); assert.equal(listing.files.length,1);
  const download=await get('download=Cockpit3D-Files/123-scene/a.glb');
  assert.equal(download.status,302); assert.equal(download.headers.get('location'),'https://download.example/Cockpit3D-Files/123-scene/a.glb');
  console.log('PASS: authorized live R2 browsing, scoped direct downloads, and expiry preserves unmarked files.');
} finally { await fs.rm(root,{recursive:true,force:true}); }
