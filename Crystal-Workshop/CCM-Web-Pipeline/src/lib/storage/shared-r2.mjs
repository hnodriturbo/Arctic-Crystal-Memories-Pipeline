/** Purpose: Server-only, create-only shared handoff adapter; independent from Workshop credentials. */
import { S3Client, HeadObjectCommand, GetObjectCommand, PutObjectCommand } from '@aws-sdk/client-s3';

export function sharedConfigured() {
  return process.env.R2_SHARED_BUCKET_NAME === 'ccm-shared' && ['ENDPOINT', 'ACCESS_KEY_ID', 'SECRET_ACCESS_KEY'].every(key => Boolean(process.env['R2_SHARED_' + key]));
}
export function sharedStore() {
  if (!sharedConfigured()) throw new Error('Shared handoff is not configured.');
  const Bucket = process.env.R2_SHARED_BUCKET_NAME;
  const client = new S3Client({ region: 'auto', endpoint: process.env.R2_SHARED_ENDPOINT, credentials: { accessKeyId: process.env.R2_SHARED_ACCESS_KEY_ID, secretAccessKey: process.env.R2_SHARED_SECRET_ACCESS_KEY } });
  return {
    async get(key) {
      try {
        const head = await client.send(new HeadObjectCommand({ Bucket, Key: key }));
        const object = await client.send(new GetObjectCommand({ Bucket, Key: key, IfMatch: head.ETag }));
        return { body: object.Body, bytes: object.ContentLength, mime: object.ContentType };
      } catch (error) { if (error.$metadata?.httpStatusCode === 404) return null; throw error; }
    },
    async putMissing(key, body, { bytes, mime, sha256 }) {
      if (!/^claude-design\/(sources|videos|manifests)\//.test(key)) throw new Error('Invalid shared write prefix.');
      await client.send(new PutObjectCommand({ Bucket, Key: key, Body: body, ContentLength: bytes, ContentType: mime, Metadata: { sha256 }, IfNoneMatch: '*' }));
    },
  };
}
