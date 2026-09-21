<!--
File: docs/R2-WORKSHOP-BUCKET.md
Purpose: The acm-workshop R2 bucket - what it holds, its CORS policy and its keys.
-->

# R2 bucket `acm-workshop`

Private, EU jurisdiction. From 20-09-2026 this is the bucket for everything
R2-related that belongs to ACM-Web-Workshop.

## Migrating off acm-pipeline-eu

The intended direction is that the other workshop pipelines move here too,
gradually: Cockpit3D scenes, Meshy jobs and converter outputs all still live in
`acm-pipeline-eu` under `R2_PIPELINE_*`, and each of those should eventually be
re-pointed at `acm-workshop` under its own prefix.

That is a separate project and is not started here. Nothing is copied, moved or
deleted out of `acm-pipeline-eu` as a side effect of other work — a scene
library that half exists in two buckets is worse than one that has not moved at
all. New workshop storage, however, goes straight into `acm-workshop`.

## Prefixes

| Prefix | Holds |
| --- | --- |
| `claude-design/sources/<collection>/…` | The design source tree mirrored from Claude-Design-Stuff |
| `claude-design/videos/<collection>/<name>.mp4` | Rendered videos |
| `claude-design/posters/<collection>/<name>.jpg` | First-frame poster for each video |

## CORS policy

Needed because the browser talks to R2 directly in two places: a presigned
`PUT` when a source tree is uploaded, and a ranged `GET` when a rendered video
is scrubbed in the player. Without `Content-Range` and `Accept-Ranges` exposed,
Chrome refuses to seek inside an mp4.

Paste this in Cloudflare → R2 → acm-workshop → Settings → CORS Policy:

```json
[
  {
    "AllowedOrigins": [
      "https://workshop.acm.is",
      "https://pipeline.acm.is",
      "http://localhost:3100"
    ],
    "AllowedMethods": ["GET", "PUT", "HEAD"],
    "AllowedHeaders": ["content-type", "content-length", "range"],
    "ExposeHeaders": [
      "ETag",
      "Content-Length",
      "Content-Range",
      "Accept-Ranges",
      "Content-Type"
    ],
    "MaxAgeSeconds": 3600
  }
]
```

`http://localhost:3100` is the local `npm run dev` port. Leaving it in is safe:
an attacker who could serve a page from the operator's own localhost already
has the machine.

`pipeline.acm.is` was the workshop's original host and was renamed to
`workshop.acm.is` on 21-09-2026. Nginx still answers on both and both proxy to
the same process on port 3003, so both are listed — an origin that is dropped
from here while it still resolves fails only in the browser, as a CORS error
with no server-side trace.

## API token

Cloudflare → R2 → API → Create API token, scoped to **this bucket only**,
permission **Object Read & Write**. Name it `ACM-Web-Workshop`. The token page
shows the Access Key ID, Secret Access Key and the S3 endpoint once.

## Environment variables

Both `.env.local` and `.env.production` carry the same five keys:

```dotenv
R2_WORKSHOP_ACCOUNT_ID=
R2_WORKSHOP_ENDPOINT=https://<account-id>.eu.r2.cloudflarestorage.com
R2_WORKSHOP_BUCKET_NAME=acm-workshop
R2_WORKSHOP_ACCESS_KEY_ID=
R2_WORKSHOP_SECRET_ACCESS_KEY=
```

On the VPS they live only in `/home/hreidar/apps/acm-pipeline/shared/.env.production`.
