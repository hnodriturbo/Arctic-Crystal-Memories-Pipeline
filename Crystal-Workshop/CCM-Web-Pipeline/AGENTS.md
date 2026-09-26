<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->

## Crystal Workshop ownership

Read `../docs/WORKSHOP-OPERATIONS.md` before changing Cockpit Reconstruct,
scene storage, publication or the workshop.acm.is deployment. Company source
files live outside this application in workspace-root CCM-Crystal-Production/Cockpit3D-Files and R2.
Use every source DXF point and the freshly saved matching scene's named texture.
Keep local development servers stopped after verification.

## Claude Design ownership

### Authorized storage migration — verified 26-09-2026

Workshop now uses private EU bucket `ccm-workshop` for both `R2_PIPELINE_*`
and `R2_WORKSHOP_*`. The owner's explicit migration authorization supersedes
the old bucket split below. All 535 source objects were copied and SHA-256
verified; legacy buckets are preserved for recovery and must not be deleted.
Keep all existing object prefixes. Main requires its own read-only credential;
never copy the Workshop writer into Main. Local, canonical production and VPS
env files have been updated. See `docs/R2-WORKSHOP-BUCKET.md` for evidence.

Read `docs/CLAUDE-DESIGN.md` and `docs/R2-WORKSHOP-BUCKET.md` before changing
the animations workspace, the render queue or the R2 mirror.

`Claude-Design-Stuff` is the original and stays the original. Its folders are
mirrored up to `acm-workshop` under `claude-design/sources/`; nothing writes
back down over an authored design, and the mirror never deletes.

`acm-workshop` owns workshop R2 from 20-09-2026. `acm-pipeline-eu` still holds
Cockpit scenes, Meshy jobs and converter outputs and is left alone — moving
those is a separate, deliberate project, never a side effect of other work.

Keep rendering to one job at a time: this VPS also serves www.acm.is. Keep the
render token narrow, keep the design tree behind `safeJoin`, and keep the two
readers separate — folders can be played, archives cannot until unpacked.

Run `npx eslint` on the touched paths, `scripts/test-workshop-r2.mjs`, a short
`scripts/render-design-video.mjs --seconds 3` and a full `npm run build` after
any material change.

## Owner-authorized two-way design sync — 25-09-2026

The owner now requests Windows/R2 synchronization in both directions. This supersedes the upload-only instruction above. Use the shared baseline-aware engine for UI and scheduled tasks. Never propagate deletions. Archive local/remote versions before replacement and preserve both sides of unresolved conflicts. Keep .workshop-sync private and excluded from uploads. Domain-only updates in the four customer-journey is.json/en.json files are explicitly requested.
