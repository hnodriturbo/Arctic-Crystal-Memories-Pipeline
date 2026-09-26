/**
 * Purpose: Back up the local Cockpit collection to private Pipeline R2.
 * Run with Node --env-file=.env.local scripts/sync-scene-files.mjs.
 * Never deletes remote files. Replaced contents are retained by SHA-256 in history.
 */
import { createReadStream } from 'node:fs';
import { readdir, stat, copyFile, rm, mkdtemp } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import path from 'node:path';
import os from 'node:os';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { S3Client, HeadObjectCommand, PutObjectCommand, CopyObjectCommand } from '@aws-sdk/client-s3';

const app = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const root = path.resolve(app, '../../../CCM-Crystal-Production/Cockpit3D-Files');
const bucket = process.env.R2_PIPELINE_BUCKET_NAME;
const prefix = 'Cockpit3D-Files/';
const dryRun = process.argv.includes('--dry-run');
const client = new S3Client({ region: 'auto', endpoint: process.env.R2_PIPELINE_ENDPOINT,
  credentials: { accessKeyId: process.env.R2_PIPELINE_ACCESS_KEY_ID, secretAccessKey: process.env.R2_PIPELINE_SECRET_ACCESS_KEY } });
if (!dryRun && (!bucket || !process.env.R2_PIPELINE_SECRET_ACCESS_KEY)) throw new Error('Pipeline R2 configuration is missing.');

// Follow only real directories and files: linked folders must not export unrelated data.
async function inventory(directory, relative = '') {
  const entries = [];
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    if (entry.isSymbolicLink()) throw new Error('Symbolic links are not backed up: ' + entry.name);
    const name = relative + entry.name;
    if (entry.isDirectory()) {
      entries.push({ relative: name + '/', directory: true });
      entries.push(...await inventory(path.join(directory, entry.name), name + '/'));
    } else if (entry.isFile()) entries.push({ relative: name, source: path.join(directory, entry.name) });
  }
  return entries;
}
async function head(key) {
  try { return await client.send(new HeadObjectCommand({ Bucket: bucket, Key: key })); }
  catch (error) { if (error.$metadata?.httpStatusCode === 404) return null; throw error; }
}
async function hashFile(file) {
  const digest = createHash('sha256');
  for await (const chunk of createReadStream(file)) digest.update(chunk);
  return digest.digest('hex');
}

// Use the same exact-member extractor as Cockpit Reconstruct before inventory.
if (!dryRun) execFileSync(path.resolve(app, '../pipeline-converter/.venv/Scripts/python.exe'),
  [path.resolve(app, '../pipeline-converter/code/extract_scene_original.py'), '--collection', root], { stdio: 'inherit' });
const files = await inventory(root);
if (dryRun) {
  for (const item of files) console.log(prefix + item.relative);
  console.log('DRY_RUN entries=' + files.length);
} else {
  const temporary = await mkdtemp(path.join(os.tmpdir(), 'acm-scene-backup-'));
  let uploaded = 0, unchanged = 0;
  try {
    for (const item of files) {
      const key = prefix + item.relative;
      const existing = await head(key);
      if (item.directory) {
        if (!existing) await client.send(new PutObjectCommand({ Bucket: bucket, Key: key, Body: '', IfNoneMatch: '*' }));
        continue;
      }
      // Upload a stable copy; a scene saved during copying is retried on the next run.
      const before = await stat(item.source);
      const snapshot = path.join(temporary, 'snapshot');
      // Windows can preserve a previous source's read-only attribute on the
      // snapshot. Remove that private copy before copying the next source.
      await rm(snapshot, { force: true });
      await copyFile(item.source, snapshot);
      const after = await stat(item.source);
      if (before.size !== after.size || before.mtimeMs !== after.mtimeMs) throw new Error('Source changed during backup: ' + item.relative);
      if (before.size > 5 * 1024 ** 3) throw new Error('File exceeds single-upload limit: ' + item.relative);
      const sha256 = await hashFile(snapshot);
      if (existing?.Metadata?.sha256 === sha256 && existing.ContentLength === before.size) { unchanged++; continue; }
      if (existing) {
        const revision = existing.Metadata?.sha256 || existing.ETag.replaceAll('"', '');
        await client.send(new CopyObjectCommand({ Bucket: bucket,
          Key: 'Cockpit3D-Scene-History/' + revision + '/' + item.relative,
          CopySource: [bucket, ...key.split('/')].map(encodeURIComponent).join('/'), CopySourceIfMatch: existing.ETag }));
      }
      await client.send(new PutObjectCommand({ Bucket: bucket, Key: key, Body: createReadStream(snapshot),
        ContentLength: before.size, ContentType: 'application/octet-stream', Metadata: { sha256 },
        ...(existing ? { IfMatch: existing.ETag } : { IfNoneMatch: '*' }) }));
      const saved = await head(key);
      if (saved.ContentLength !== before.size || saved.Metadata?.sha256 !== sha256) throw new Error('Upload verification failed: ' + item.relative);
      uploaded++;
      console.log('VERIFIED ' + item.relative + ' bytes=' + before.size);
    }
    console.log('SCENE_BACKUP_OK uploaded=' + uploaded + ' unchanged=' + unchanged);
  } finally { await rm(temporary, { recursive: true, force: true }); }
}
