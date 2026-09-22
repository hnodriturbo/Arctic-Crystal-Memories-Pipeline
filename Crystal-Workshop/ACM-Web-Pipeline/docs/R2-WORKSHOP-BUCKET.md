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

Both workshop buckets carry the same policy, because both are reached from the
same two origins and nothing about the rules differs between them:

```json
[
  {
    "AllowedOrigins": [
      "https://workshop.acm.is",
      "http://localhost:3100"
    ],
    "AllowedMethods": ["GET", "PUT", "HEAD"],
    "AllowedHeaders": ["content-type", "range"],
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

`http://localhost:3100` is this app's dev port, fixed by `next dev -p 3100` in
`package.json`. It is not 3000 — that is ACM-Web-Main, a different application.

### What each bucket actually needs it for

**`acm-pipeline-eu` needs this policy.** Two real cross-origin requests:

- `PUT` — `src/lib/upload-to-r2.js` has the browser send a model straight into
  the bucket, bypassing this server, because a 300 MB file should not be
  streamed through Node twice.
- `GET` — `<model-viewer>` loads a GLB through `/api/file`, which redirects to
  a presigned URL. Unlike a `<video>` element, it fetches, so CORS applies.

**`acm-workshop` does not need it today**, and carries it anyway. Video
playback and downloads go through `/api/claude-design/videos` on this app's own
origin, which 302-redirects to R2 — and `<video>`, `<img>` and a download link
do not perform a CORS check. The policy is there so a direct upload added later
works immediately rather than failing in a way that leaves no server-side
trace.

ACM-Web-Main does **not** need an entry in either policy. It reads
`acm-pipeline-eu` server-side only and streams objects through its own routes
(`src/lib/showroom/pipeline-library.js` is `server-only`), so the customer's
browser never contacts R2 directly.

### A retired origin

The workshop's original host was `pipeline` on this domain. It was renamed to
`workshop.acm.is`; on 22-09-2026 the old nginx site was moved to
`/etc/nginx/retired-20260922/` and its certificate deleted. The old origin is
deliberately absent from the policy above, and the DNS record for it should be
removed in Cloudflare — while it still resolves, a visitor reaches the default
server and gets a certificate warning.

## Version history - built here, not by R2

**R2 has no object versioning.** `PutBucketVersioning` and
`GetBucketVersioning` are listed as unimplemented in Cloudflare's own S3
compatibility table, and there is no dashboard setting for it either. Asking
for it over the S3 API answers `AccessDenied`, which reads like a permissions
problem and is not one.

So the mirror keeps history itself. `sync-claude-design-r2.mjs` copies the
object that is already there into `claude-design/history/<sha256>/` before
replacing it, which is the same thing `sync-scene-files.mjs` does for Cockpit
scenes under `Cockpit3D-Scene-History/`. Between that and the fact that the
mirror never deletes, a design is recoverable whether it was lost or replaced.

Change detection is size and modification time first, falling back to a SHA-256
of the file only when those are inconclusive. That keeps an ordinary run from
reading the whole tree, while still catching an edit that happens to leave the
byte count unchanged - which a size comparison alone would miss forever.

Nothing prunes `history/` yet. If it grows enough to matter, an R2 lifecycle
rule on that prefix is the place to handle it; lifecycle rules R2 does support.

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
