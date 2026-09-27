/** Purpose: Add only the reviewed server-side order-reader/shared-writer groups to canonical environments; never expose credential values. */
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import dotenv from 'dotenv';

const source = dotenv.parse(fs.readFileSync('.env.local'));
const values = {};
for (const [group, bucket] of [['R2_ORDERS', 'ccm-orders'], ['R2_SHARED', 'ccm-shared']]) {
  if (source[group + '_BUCKET_NAME'] !== bucket) throw Error('Unexpected storage target');
  for (const field of ['BUCKET_NAME', 'ENDPOINT', 'ACCESS_KEY_ID', 'SECRET_ACCESS_KEY']) {
    const key = group + '_' + field;
    if (!source[key] || /[\r\n]/.test(source[key])) throw Error('Incomplete configuration');
    values[key] = source[key];
  }
}
const applyLocal = process.argv.includes('--apply-local');
const applyVps = process.argv.includes('--apply-vps');
if (!applyLocal && !applyVps) { console.log('Validated eight source assignments. Use --apply-local and/or --apply-vps to add them.'); process.exit(0); }

if (applyLocal) {
  for (const file of ['.env.production', '../.Production-Web-Workshop/environment/.env.production']) {
    const current = fs.readFileSync(file, 'utf8');
    const parsed = dotenv.parse(current);
    for (const [key, value] of Object.entries(values)) if (parsed[key] && parsed[key] !== value) throw Error('Existing target assignment differs; left unchanged');
    const missing = Object.entries(values).filter(([key]) => !parsed[key]);
    if (!missing.length) continue;
    const backup = path.resolve('../.Production-Web-Workshop/environment', path.basename(path.dirname(path.resolve(file))) + '-before-order-shared-27-09-2026.env');
    if (!fs.existsSync(backup)) fs.writeFileSync(backup, current, { flag: 'wx', mode: 0o600 });
    // Existing production settings stay byte-for-byte intact; only absent names are appended.
    fs.appendFileSync(file, '\n# Private order archive and explicit shared handoff\n' + missing.map(([key, value]) => key + '=' + JSON.stringify(value)).join('\n') + '\n');
    const verified = dotenv.parse(fs.readFileSync(file));
    if (!Object.entries(values).every(([key, value]) => verified[key] === value)) throw Error('Configuration verification failed');
  }
  console.log('CANONICAL_LOCAL_ENV_GROUPS_VERIFIED');
}
if (applyVps) {
  // Secret values travel only over encrypted stdin, never command arguments or output.
  const python = `import json,sys,os,tempfile,shutil
values=json.load(sys.stdin)
allowed={g+'_'+f for g in ('R2_ORDERS','R2_SHARED') for f in ('BUCKET_NAME','ENDPOINT','ACCESS_KEY_ID','SECRET_ACCESS_KEY')}
assert set(values)==allowed
assert values['R2_ORDERS_BUCKET_NAME']=='ccm-orders' and values['R2_SHARED_BUCKET_NAME']=='ccm-shared'
root='/home/hreidar/apps/ccm-workshop/shared'
target=root+'/.env.production'
with open(target) as f: current=f.read()
present={}
for line in current.splitlines():
 if '=' in line and not line.lstrip().startswith('#'):
  k,v=line.split('=',1)
  if k in allowed:
   assert k not in present
   present[k]=v.strip().strip(chr(34)).strip(chr(39))
assert all(present[k]==v for k,v in values.items() if k in present)
missing={k:v for k,v in values.items() if k not in present}
if missing:
 backup=root+'/.env.before-order-shared-27-09-2026'
 if not os.path.exists(backup):
  fd=os.open(backup,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
  with os.fdopen(fd,'w') as f: f.write(current)
 fd,tmp=tempfile.mkstemp(prefix='.env-order-shared-',dir=root)
 try:
  with os.fdopen(fd,'w') as f: f.write(current+'\\n# Private order archive and shared handoff\\n'+''.join(k+'='+json.dumps(v)+'\\n' for k,v in missing.items()))
  os.chmod(tmp,0o600)
  os.replace(tmp,target)
 finally:
  if os.path.exists(tmp): os.remove(tmp)
print('VPS_ENV_GROUPS_ADDED_NO_RESTART')
`;
  const quoted = "'" + python.replaceAll("'", "'\"'\"'") + "'";
  const result = spawnSync('ssh', ['acm-vps', 'python3 -c ' + quoted], { input: JSON.stringify(values), encoding: 'utf8', timeout: 60000, windowsHide: true });
  if (result.status !== 0 || !result.stdout.includes('VPS_ENV_GROUPS_ADDED_NO_RESTART')) throw Error('VPS configuration failed; inspect target without printing secrets');
  console.log('VPS_ENV_GROUPS_ADDED_NO_RESTART');
}
