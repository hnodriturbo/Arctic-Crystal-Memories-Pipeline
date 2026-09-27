<!-- Purpose: Private order-linked DXF handoff, evidence boundaries and deployment status. -->
# Orders & DXF files

## Verified local implementation — 26-09-2026

Open `/?view=orders-dxf` after normal Workshop login. Search the order number,
filter Web/In-store, select an order, then upload the DXF exported and reviewed
locally in Cockpit3D. Confirm the selected order before upload. On the machine
computer, log into Workshop, select the same order and download a chosen version.

The order reader currently reads retained recovery evidence in private
`ccm-orders`. It validates schema, canonical ID, channel and payload checksum.
The UI shows the snapshot date. This is historical evidence, not a live payment,
fulfilment or order-status feed. The dedicated Main production connector remains
a separate dependency. No payment, invoice or order is created by this feature.

## Storage and integrity

DXF bodies and manifests use the existing private `ccm-workshop` bucket:

```text
production-orders/<sha256(canonical Main order ID)>/files/<file-sha256>.dxf
production-orders/<sha256(canonical Main order ID)>/versions/<file-sha256>.json
```

The body is streamed to a bounded temporary file (95 MiB maximum), hashed and
checked for a recognizable DXF container. It is uploaded create-only, then read
back in full to verify SHA-256, byte count and MIME before the manifest is written
create-only. A retry of the same order/file reuses the original manifest and date.
The HTTP limit is deliberately below the existing 100 MiB Nginx upload limit.
This streaming endpoint uses its own complete auth/role/origin check outside the
Next proxy matcher, avoiding Next 16's default 10 MB request-clone truncation.
Existing files and earlier versions are never replaced or deleted. An interrupted
body upload without a verified manifest is not listed as a finished version.

The manifest records canonical order ID, order number, channel, filename, hash,
bytes, object ETag, upload date, operator ID and explicit `OPERATOR_REVIEWED`
state. This is the operator's review declaration; container recognition is not
a geometric, DXF dialect or laser-machine compatibility certificate.

Every endpoint rechecks the active Workshop OWNER/ADMIN in the database.
Uploads also require the configured same origin. Downloads resolve a manifest
inside that exact order and stream the original body with an ETag condition,
attachment disposition, SHA header and private/no-store caching. No general R2
key or local filesystem path is accepted as a download capability. Nothing sends
commands to the laser machine. Review the imported file/settings in its software.

## Configuration and release gate

- `R2_ORDERS_*`: dedicated `ccm-orders` reader, server-only.
- `R2_PIPELINE_*`: existing `ccm-workshop` writer for immutable DXF versions.
- Local `.env.local` order reader is configured and verified (6 identities:
  4 ONLINE and 2 IN_STORE).
- `scripts/configure-order-shared-env.mjs` prepares the exact additive production
  change for the order reader and explicit Claude shared-handoff group. It takes
  private backups, refuses differing pre-existing values and prints no secrets.
- Automatic approval review rejected the combined local/VPS production credential
  setup on 26-09-2026 because exact production permission, especially the shared
  writer, was unclear. The command did not run. Owner confirmation is pending;
  this feature has **not** been deployed. The existing live release is unchanged.

## Verification

- Production build and focused ESLint passed after the repository move.
- 11 offline tests passed across order/DXF identity, readback/retry/isolation,
  shared-copy races/conflicts, design discovery and immutable handoff.
- Normal authenticated HTTP QA read all 6 orders and their version lists;
  guest, foreign-origin upload and traversal attempts were denied. No production
  order or DXF was created by these checks.
- Desktop/mobile Orders UI checked in a real browser. Existing Workshop read
  endpoint regression reported `ALL_PIPELINES_OK`.
- No real customer final DXF or machine import was used as test data. Exact-body
  upload/download was exercised against an isolated in-memory object store.

## Remaining wider local integration

Four routed local workspaces, the embedded In-store component, canonical scheduled
order/evidence downloads and Bookkeeping's two-channel intake are still separate
unfinished work. Do not describe the recovery reader as completion of those flows.
