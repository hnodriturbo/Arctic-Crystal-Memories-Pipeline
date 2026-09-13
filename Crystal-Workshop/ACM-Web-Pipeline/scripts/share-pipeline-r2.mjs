/**
 * Purpose: Provision the explicitly authorized Pipeline R2 connection in local Main env files.
 * Values are never logged. Existing files receive a private backup before replacement.
 */
import { readFile, writeFile, copyFile, mkdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const app = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const main = path.resolve(app, '../../../ACM-Web-Main');
process.loadEnvFile(path.join(app, '.env.local'));
const keys = ['R2_PIPELINE_ENDPOINT', 'R2_PIPELINE_ACCESS_KEY_ID', 'R2_PIPELINE_SECRET_ACCESS_KEY', 'R2_PIPELINE_BUCKET_NAME'];
for (const key of keys) if (!process.env[key]) throw new Error('Missing configuration: ' + key);
const stamp = new Date().toISOString().replaceAll(':', '-');
const backup = path.join(main, '.Production-Web-Main/environment/backups', stamp + '-pipeline-r2');
await mkdir(backup, { recursive: true });
for (const [label, relative] of [['local', '.env'], ['production', '.Production-Web-Main/environment/.env']]) {
  const target = path.join(main, relative);
  const original = await readFile(target, 'utf8');
  let updated = original;
  for (const key of keys) {
    const line = key + '=' + JSON.stringify(process.env[key]);
    const pattern = new RegExp('^' + key + '=.*$', 'm');
    updated = pattern.test(updated) ? updated.replace(pattern, () => line) : updated.trimEnd() + '\n' + line + '\n';
  }
  const grouped = updated.split(/\r?\n/).filter((line) => !keys.includes(line.split('=')[0]) && line !== '# Crystal Workshop private R2 library');
  let insertion = 0;
  grouped.forEach((line, index) => { if (/^(R2_|CLOUDFLARE_)[A-Z0-9_]*=/.test(line)) insertion = index + 1; });
  grouped.splice(insertion, 0, '', '# Crystal Workshop private R2 library', ...keys.map((key) => key + '=' + JSON.stringify(process.env[key])), '');
  updated = grouped.join('\n');
  if (updated !== original) {
    await copyFile(target, path.join(backup, label + '.env'));
    await writeFile(target, updated);
  }
  console.log('PIPELINE_R2_CONFIGURED ' + label + ' keys=' + keys.length);
}
