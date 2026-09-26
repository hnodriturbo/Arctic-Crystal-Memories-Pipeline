/** Purpose: Conditional R2 operations for the shared Claude Design sync engine. */
import path from 'node:path';
import { createReadStream, createWriteStream } from 'node:fs';
import { stat } from 'node:fs/promises';
import { pipeline } from 'node:stream/promises';
import { S3Client, ListObjectsV2Command, HeadObjectCommand, GetObjectCommand, PutObjectCommand, CopyObjectCommand } from '@aws-sdk/client-s3';
const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.jsx': 'text/javascript', '.mjs': 'text/javascript', '.json': 'application/json', '.css': 'text/css', '.svg': 'image/svg+xml', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp', '.gif': 'image/gif', '.avif': 'image/avif', '.mp4': 'video/mp4', '.webm': 'video/webm', '.mp3': 'audio/mpeg', '.wav': 'audio/wav', '.woff': 'font/woff', '.woff2': 'font/woff2' };
export function designStore() {
  const bucket = process.env.R2_WORKSHOP_BUCKET_NAME;
  if (!bucket || !process.env.R2_WORKSHOP_SECRET_ACCESS_KEY) throw new Error('Workshop R2 configuration is missing.');
  const client = new S3Client({ region: 'auto', endpoint: process.env.R2_WORKSHOP_ENDPOINT, credentials: { accessKeyId: process.env.R2_WORKSHOP_ACCESS_KEY_ID, secretAccessKey: process.env.R2_WORKSHOP_SECRET_ACCESS_KEY } });
  return {
    async list(prefix) {
      const result = []; let token;
      do { const page = await client.send(new ListObjectsV2Command({ Bucket: bucket, Prefix: prefix, ContinuationToken: token })); result.push(...(page.Contents || []).map(x => ({ key: x.Key }))); token = page.IsTruncated ? page.NextContinuationToken : undefined; } while (token);
      return result;
    },
    async head(key) {
      try { const r = await client.send(new HeadObjectCommand({ Bucket: bucket, Key: key })); return { etag: r.ETag, hash: r.Metadata?.sha256, size: r.ContentLength }; }
      catch (e) { if (e.$metadata?.httpStatusCode === 404) return null; throw e; }
    },
    async download(key, file, etag) {
      const r = await client.send(new GetObjectCommand({ Bucket: bucket, Key: key, IfMatch: etag }));
      await pipeline(r.Body, createWriteStream(file));
    },
    async upload(key, file, hash, etag) {
      const info = await stat(file);
      await client.send(new PutObjectCommand({ Bucket: bucket, Key: key, Body: createReadStream(file), ContentLength: info.size, ContentType: TYPES[path.extname(key).toLowerCase()] || 'application/octet-stream', Metadata: { sha256: hash }, ...(etag ? { IfMatch: etag } : { IfNoneMatch: '*' }) }));
    },
    async archive(key, existing) {
      const revision = existing.hash || existing.etag.replaceAll('"', '');
      await client.send(new CopyObjectCommand({ Bucket: bucket, Key: 'claude-design/history/' + revision + '/' + key.slice('claude-design/'.length), CopySource: [bucket, ...key.split('/')].map(encodeURIComponent).join('/'), CopySourceIfMatch: existing.etag }));
    },
    async createCollection(name) {
      await client.send(new PutObjectCommand({ Bucket: bucket, Key: 'claude-design/sources/' + name + '/', Body: '', IfNoneMatch: '*' }));
    }
  };
}
