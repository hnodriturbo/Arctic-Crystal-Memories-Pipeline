/**
 * Purpose: Inventory/copy explicit Workshop prefixes into private shared storage.
 * Defaults to read-only plan; --apply requires a reviewed mapping file. Never deletes.
 */
import { readFile, writeFile } from 'node:fs/promises';
import { S3Client, ListObjectsV2Command, HeadObjectCommand, GetObjectCommand, PutObjectCommand } from '@aws-sdk/client-s3';
import { copyShared, validateMapping } from '../src/lib/storage/shared-copy.mjs';

const args = process.argv.slice(2);
const value = flag => { const index = args.indexOf(flag); return index < 0 ? null : args[index + 1]; };
function store(prefix, bucketExpected) {
  const env = name => process.env[`${prefix}_${name}`];
  const bucket = env('BUCKET_NAME');
  if (bucket !== bucketExpected || !env('ENDPOINT') || !env('ACCESS_KEY_ID') || !env('SECRET_ACCESS_KEY')) throw new Error('Missing or unexpected bucket configuration.');
  const client = new S3Client({ region: 'auto', endpoint: env('ENDPOINT'), credentials: { accessKeyId: env('ACCESS_KEY_ID'), secretAccessKey: env('SECRET_ACCESS_KEY') } });
  return {
    async list(prefix) {
      const objects = []; let token;
      do {
        const page = await client.send(new ListObjectsV2Command({ Bucket: bucket, Prefix: prefix, ContinuationToken: token }));
        objects.push(...(page.Contents || []).map(item => ({ sourceKey: item.Key, sourceEtag: item.ETag })));
        token = page.IsTruncated ? page.NextContinuationToken : undefined;
      } while (token);
      return objects;
    },
    async head(key) {
      try { const object = await client.send(new HeadObjectCommand({ Bucket: bucket, Key: key })); return { etag: object.ETag, bytes: object.ContentLength }; }
      catch (error) { if (error.$metadata?.httpStatusCode === 404) return null; throw error; }
    },
    async get(key, etag) {
      const object = await client.send(new GetObjectCommand({ Bucket: bucket, Key: key, IfMatch: etag }));
      return { body: object.Body, mime: object.ContentType || 'application/octet-stream' };
    },
    async putMissing(key, body, info) {
      try {
        await client.send(new PutObjectCommand({ Bucket: bucket, Key: key, Body: body, ContentLength: info.bytes, ContentType: info.mime, Metadata: { sha256: info.sha256 }, IfNoneMatch: '*' }));
      } finally { body.destroy(); }
    },
  };
}

try {
  const source = store('R2_WORKSHOP', 'ccm-workshop');
  const reportPath = value('--report');
  if (!reportPath) throw new Error('--report is required.');
  if (args.includes('--inventory')) {
    if (args.includes('--apply')) throw new Error('Inventory is read-only.');
    const prefixes = [
      ['Cockpit3D-Files/.Showroom/', 'Showroom-data/'],
      ['claude-design/sources/', 'claude-design/sources/'],
      ['claude-design/videos/', 'claude-design/videos/'],
    ];
    const entries = [];
    for (const [from, to] of prefixes) for (const object of await source.list(from)) {
      entries.push({ ...object, destinationKey: to + object.sourceKey.slice(from.length) });
    }
    // Main supplies all saved Workshop references outside .Showroom after its DB audit.
    const extraPath = value('--extra-keys');
    if (extraPath) for (const key of JSON.parse(await readFile(extraPath, 'utf8'))) {
      if (!key.startsWith('Cockpit3D-Files/') || key.startsWith('Cockpit3D-Files/.Showroom/')) throw new Error('Unexpected legacy reference.');
      const head = await source.head(key);
      if (!head) throw new Error('Referenced source missing.');
      entries.push({ sourceKey: key, sourceEtag: head.etag, destinationKey: 'Showroom-data/legacy/' + key });
    }
    validateMapping(entries);
    await writeFile(reportPath, JSON.stringify({ schemaVersion: 1, createdAt: new Date().toISOString(), entries }, null, 2), { flag: 'wx' });
    console.log(JSON.stringify({ inventoryObjects: entries.length }));
  } else {
    const mappingPath = value('--mapping');
    if (!mappingPath) throw new Error('--mapping is required.');
    const mapping = JSON.parse(await readFile(mappingPath, 'utf8'));
    if (mapping.schemaVersion !== 1) throw new Error('Unsupported mapping.');
    const destination = store('R2_SHARED', 'ccm-shared');
    // Reserve the evidence file before any remote writes; never replace prior evidence.
    await writeFile(reportPath, '', { flag: 'wx' });
    const results = await copyShared({ source, destination, entries: mapping.entries, apply: args.includes('--apply'),
      onResult: async result => { const { appendFile } = await import('node:fs/promises'); await appendFile(reportPath, JSON.stringify(result) + '\n'); },
    });
    const counts = {}; for (const result of results) counts[result.status] = (counts[result.status] || 0) + 1;
    console.log(JSON.stringify(counts));
    if (results.some(result => ['error', 'conflict'].includes(result.status))) process.exitCode = 1;
  }
} catch (error) {
  console.error('Shared copy stopped:', error.$metadata?.httpStatusCode || error.code || error.message);
  process.exitCode = 1;
}
