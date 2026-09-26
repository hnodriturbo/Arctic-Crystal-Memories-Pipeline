/** Purpose: Test reserved versions, paired filenames and repeat-save protection without R2. */
import assert from 'node:assert/strict';
import vm from 'node:vm';
import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
const context=vm.createContext({});
const claims=new Set(['003']); const saved=new Map();
const values={
 listObjects:async()=>[{key:'Cockpit3D-Files/75572-jon-thor/75572-jon-thor-edited-v002.glb'}],
 reserveObject:async(key)=>{const version=key.match(/v(\d+)\.json$/)[1];if(claims.has(version))throw {$metadata:{httpStatusCode:412}};claims.add(version);},
 uploadFile:async(_file,key,options)=>{assert.equal(options.ifNoneMatch,'*');if(saved.has(key))throw {$metadata:{httpStatusCode:412}};saved.set(key,options.metadata);},
 objectMetadata:async key=>({Metadata:saved.get(key)}),
};
const dependencies={ './r2.js':values, 'node:crypto':{createHash}, 'node:fs':{createReadStream:()=>[Buffer.from('model bytes')]} };
const sceneModule=new vm.SourceTextModule(await readFile(new URL('../src/lib/storage/scene-model-names.js',import.meta.url),'utf8'),{context});
await sceneModule.link(name=>{const exports=dependencies[name];return new vm.SyntheticModule(Object.keys(exports),function(){for(const [key,value] of Object.entries(exports))this.setExport(key,value);},{context});});
await sceneModule.evaluate();
const {reserveSceneModel,saveReservedFile}=sceneModule.namespace;
assert.equal(await reserveSceneModel('75572-jon-thor',{edited:true}),'75572-jon-thor-edited-v004');
assert.equal(await reserveSceneModel('75572-jon-thor'),'75572-jon-thor-v005');
await assert.rejects(()=>reserveSceneModel('../invalid'));
const key='Cockpit3D-Files/75572-jon-thor/75572-jon-thor-v005.glb';
await saveReservedFile('file',key);await saveReservedFile('file',key);
saved.set(key,{sha256:'different'});
await assert.rejects(()=>saveReservedFile('file',key));
console.log('PASS: version reservation, shared sequence, edited label, idempotent save and conflict protection.');
