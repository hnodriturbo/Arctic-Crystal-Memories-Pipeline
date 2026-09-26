/*
 * ═══════════════════════════════════════════════════════════════
 * Show R2 CORS
 * ═══════════════════════════════════════════════════════════════
 * Path: scripts/show-r2-cors.mjs
 * Purpose: Print the CORS policy currently set on both workshop buckets.
 *
 *   node --env-file=.env.local scripts/show-r2-cors.mjs
 *
 * A CORS mistake shows up only in a browser, as a blocked request with no
 * server-side trace, so being able to read the live policy back is worth more
 * than remembering what was pasted into the dashboard.
 */

import { GetBucketCorsCommand, S3Client } from "@aws-sdk/client-s3";

const BUCKETS = [
  {
    label: "Workshop scenes and pipeline jobs",
    bucket: process.env.R2_PIPELINE_BUCKET_NAME,
    endpoint: process.env.R2_PIPELINE_ENDPOINT,
    accessKeyId: process.env.R2_PIPELINE_ACCESS_KEY_ID,
    secretAccessKey: process.env.R2_PIPELINE_SECRET_ACCESS_KEY,
  },
  {
    label: "Workshop design sources and media",
    bucket: process.env.R2_WORKSHOP_BUCKET_NAME,
    endpoint: process.env.R2_WORKSHOP_ENDPOINT,
    accessKeyId: process.env.R2_WORKSHOP_ACCESS_KEY_ID,
    secretAccessKey: process.env.R2_WORKSHOP_SECRET_ACCESS_KEY,
  },
];

for (const entry of BUCKETS) {
  console.log(`\n=== ${entry.label} (${entry.bucket || "not configured"}) ===`);
  if (!entry.bucket || !entry.secretAccessKey) {
    console.log("  credentials missing from this environment file");
    continue;
  }

  const client = new S3Client({
    region: "auto",
    endpoint: entry.endpoint,
    credentials: { accessKeyId: entry.accessKeyId, secretAccessKey: entry.secretAccessKey },
  });

  try {
    const result = await client.send(new GetBucketCorsCommand({ Bucket: entry.bucket }));
    console.log(JSON.stringify(result.CORSRules, null, 2));
  } catch (error) {
    // Neither of these is a fault. No policy is a normal answer, and Access
    // Denied is the right answer for an Object Read & Write token: reading a
    // bucket's configuration needs Admin, which these deliberately do not have.
    const code = error.name || error.Code;
    if (code === "NoSuchCORSConfiguration") {
      console.log("  no CORS policy set");
    } else if (code === "AccessDenied") {
      console.log("  not readable with an Object Read & Write token, which is correct -");
      console.log("  bucket configuration needs Admin. Read it in the Cloudflare dashboard.");
    } else {
      console.log(`  could not read it: ${code} - ${error.message}`);
    }
  }
}
