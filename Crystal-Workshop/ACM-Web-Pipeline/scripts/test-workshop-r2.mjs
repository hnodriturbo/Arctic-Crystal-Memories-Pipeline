/*
 * ═══════════════════════════════════════════════════════════════
 * Test Workshop R2
 * ═══════════════════════════════════════════════════════════════
 * Path: scripts/test-workshop-r2.mjs
 * Purpose: Prove the acm-workshop credentials actually work, before anything
 *          depends on them.
 *
 *   node --env-file=.env.local scripts/test-workshop-r2.mjs
 *
 * Writes one small object, lists it, fetches it back through a presigned URL
 * and deletes it again. All four are exercised because a token can easily be
 * read-only, or scoped to the wrong bucket, and each of those fails at a
 * different step - which is the useful thing to learn from a single run.
 */

import {
  DeleteObjectCommand,
  GetObjectCommand,
  ListObjectsV2Command,
  PutObjectCommand,
  S3Client,
} from "@aws-sdk/client-s3";
import { getSignedUrl } from "@aws-sdk/s3-request-presigner";

const bucket = process.env.R2_WORKSHOP_BUCKET_NAME;
if (!bucket || !process.env.R2_WORKSHOP_SECRET_ACCESS_KEY) {
  throw new Error("R2_WORKSHOP_* is missing from the environment file.");
}

console.log("bucket   :", bucket);
console.log("endpoint :", process.env.R2_WORKSHOP_ENDPOINT);

const client = new S3Client({
  region: "auto",
  endpoint: process.env.R2_WORKSHOP_ENDPOINT,
  credentials: {
    accessKeyId: process.env.R2_WORKSHOP_ACCESS_KEY_ID,
    secretAccessKey: process.env.R2_WORKSHOP_SECRET_ACCESS_KEY,
  },
});

// A name nothing else will ever use, so a failed run cannot leave something
// that looks like a real design behind.
const key = "claude-design/sources/__connection-test.txt";

await client.send(
  new PutObjectCommand({
    Bucket: bucket,
    Key: key,
    Body: "acm-workshop connection test",
    ContentType: "text/plain; charset=utf-8",
  }),
);
console.log("PUT      : ok");

const listed = await client.send(
  new ListObjectsV2Command({ Bucket: bucket, Prefix: "claude-design/" }),
);
console.log("LIST     :", listed.KeyCount, "object(s) under claude-design/");

const url = await getSignedUrl(client, new GetObjectCommand({ Bucket: bucket, Key: key }), {
  expiresIn: 60,
});
const response = await fetch(url);
console.log("PRESIGN  :", response.status, JSON.stringify(await response.text()));

await client.send(new DeleteObjectCommand({ Bucket: bucket, Key: key }));
console.log("DELETE   : ok");
console.log("WORKSHOP_R2_OK");
