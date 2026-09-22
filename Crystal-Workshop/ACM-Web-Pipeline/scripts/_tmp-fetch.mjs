/* Download one object from acm-workshop to a local file. */
import { writeFile } from "node:fs/promises";
import { GetObjectCommand, S3Client } from "@aws-sdk/client-s3";

const [key, destination] = process.argv.slice(2);

const client = new S3Client({
  region: "auto",
  endpoint: process.env.R2_WORKSHOP_ENDPOINT,
  credentials: {
    accessKeyId: process.env.R2_WORKSHOP_ACCESS_KEY_ID,
    secretAccessKey: process.env.R2_WORKSHOP_SECRET_ACCESS_KEY,
  },
});

const response = await client.send(
  new GetObjectCommand({ Bucket: process.env.R2_WORKSHOP_BUCKET_NAME, Key: key }),
);
const bytes = Buffer.from(await response.Body.transformToByteArray());
await writeFile(destination, bytes);
console.log(`${key} -> ${destination} (${bytes.length} bytes)`);
