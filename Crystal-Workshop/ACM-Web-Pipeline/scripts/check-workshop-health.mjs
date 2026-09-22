/*
 * ═══════════════════════════════════════════════════════════════
 * Check Workshop Health
 * ═══════════════════════════════════════════════════════════════
 * Path: scripts/check-workshop-health.mjs
 * Purpose: Prove both R2 buckets still answer, on whichever machine it runs.
 *
 *   node --env-file=.env.local scripts/check-workshop-health.mjs
 *   node --env-file=<shared>/.env.production scripts/check-workshop-health.mjs
 *
 * Written after a hostname change, because a bucket that has gone unreachable
 * looks exactly like one nobody happened to use that day. Each prefix here
 * belongs to a different part of the workshop, so a single failing line names
 * the pipeline that is broken.
 */

import { HeadBucketCommand, ListObjectsV2Command, S3Client } from "@aws-sdk/client-s3";

function clientFor(prefix) {
  const endpoint = process.env[`${prefix}_ENDPOINT`];
  const bucket = process.env[`${prefix}_BUCKET_NAME`];
  const accessKeyId = process.env[`${prefix}_ACCESS_KEY_ID`];
  const secretAccessKey = process.env[`${prefix}_SECRET_ACCESS_KEY`];
  if (!endpoint || !bucket || !accessKeyId || !secretAccessKey) return null;
  return {
    bucket,
    client: new S3Client({ region: "auto", endpoint, credentials: { accessKeyId, secretAccessKey } }),
  };
}

// One line per thing the workshop actually stores, named after the feature
// that breaks if the prefix is empty or unreachable.
const CHECKS = [
  { env: "R2_PIPELINE", prefix: "Cockpit3D-Files/", owner: "Cockpit Reconstruct scenes" },
  { env: "R2_PIPELINE", prefix: "jobs/", owner: "Meshy generated assets" },
  { env: "R2_PIPELINE", prefix: "converter-jobs/", owner: "Converter exports" },
  { env: "R2_PIPELINE", prefix: "uploads/", owner: "Browser uploads" },
  { env: "R2_WORKSHOP", prefix: "claude-design/sources/", owner: "Claude Design sources" },
  { env: "R2_WORKSHOP", prefix: "claude-design/videos/", owner: "Claude Design videos" },
];

const connections = new Map();
let failures = 0;

for (const check of CHECKS) {
  if (!connections.has(check.env)) {
    const connection = clientFor(check.env);
    connections.set(check.env, connection);

    console.log(`\n=== ${check.env} -> ${connection?.bucket || "not configured"} ===`);
    if (connection) {
      try {
        await connection.client.send(new HeadBucketCommand({ Bucket: connection.bucket }));
        console.log("  bucket reachable");
      } catch (error) {
        console.log(`  UNREACHABLE: ${error.name} - ${error.message}`);
        failures++;
      }
    } else {
      console.log("  credentials missing from this environment file");
      failures++;
    }
  }

  const connection = connections.get(check.env);
  if (!connection) continue;

  try {
    const page = await connection.client.send(
      new ListObjectsV2Command({ Bucket: connection.bucket, Prefix: check.prefix, MaxKeys: 1000 }),
    );
    const count = page.KeyCount ?? 0;
    console.log(`  ${check.prefix.padEnd(26)} ${String(count).padStart(5)}  ${check.owner}`);
  } catch (error) {
    console.log(`  ${check.prefix.padEnd(26)}  FAILED  ${error.name} (${check.owner})`);
    failures++;
  }
}

console.log(failures ? `\nWORKSHOP_HEALTH_FAILED checks=${failures}` : "\nWORKSHOP_HEALTH_OK");
process.exitCode = failures ? 1 : 0;
