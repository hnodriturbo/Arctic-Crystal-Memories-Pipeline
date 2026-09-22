<!--
File: docs/CLAUDE-DESIGN.md
Purpose: How the Claude Design animations workspace is put together and what
         owns what.
-->

# Claude Design animations

**Claude Design** in the Crystal Workshop sidebar turns the animations in
`Claude-Design-Stuff` into MP4 files, stores them in the `acm-workshop` bucket,
and plays them back from there.

Two entries, deliberately. Both keep their English names in the Icelandic UI,
the way `Cockpit Reconstruct` and `Crystal Workshop` do — they name a screen
rather than describe one:

- **Design Animations** reads folders. Everything it lists can be previewed,
  rendered or played.
- **Design Archives** reads only archives. A zip cannot be previewed or
  rendered until it has been unpacked, and mixing the two lists made a sealed
  archive look like an empty collection.

## Where the parts live

```txt
src/lib/claude-design/paths.js        Root resolution and the escape guard
src/lib/claude-design/scan.js         Collections, designs, zips, exports
src/lib/claude-design/mirror.js       Push and pull one collection to/from R2
src/lib/claude-design/render-jobs.js  The queue, one render at a time
src/lib/storage/workshop-r2.js        The acm-workshop client
scripts/render-design-video.mjs       The renderer itself
scripts/sync-claude-design-r2.mjs     Standalone mirror for the daily R2 job
src/components/ClaudeDesignClient.jsx The animations workspace
src/components/ClaudeDesignZips.jsx   The archive shelf
```

## Two machines, one page

|                         | Operator's Windows box | VPS (`workshop.acm.is`)                     |
| ----------------------- | ---------------------- | ------------------------------------------- |
| `CLAUDE_DESIGN_ROOT`    | the real repository    | an empty scratch workspace                  |
| Where designs come from | already there          | pulled from R2 on demand                    |
| Rendering               | yes                    | yes - ffmpeg and a shared Chromium installed |
| Playback and download   | from R2                | from R2                                     |

The page adapts rather than branching on which host it is: it reports whether
this machine can render, and lists what is in the bucket either way.

## How a render actually works

The page is stepped by hand through a virtual clock. `requestAnimationFrame`
and `setTimeout` are replaced inside the page, so it believes exactly 1/60 of a
second passed between frames however long the work really took. That is why the
output is always smooth 60fps on a loaded VPS as much as on an idle desktop,
and why this is not a screen recording — a recorder cannot promise that.

Frames go to ffmpeg over stdin as JPEG. No temporary files, and far quicker
than writing several thousand images to disk and reading them back.

Scene length is read out of the design's own `OM_SCENES`, so a redesigned
animation reports its new length without anything here being edited.

### The player bar

The design carries its own player bar. It is hidden by default because it
belongs to the design's preview rather than to a finished video, and
**Keep the player bar** turns that off. The bar has neither id nor
class, so it is found by shape and position: a short box across the bottom of
the screen containing a button. When that match fails the console says so,
which is worth reading — it means the first frame should be checked by eye.

### The closing scene

`www.acm.is` in the last scene is too small and sits too close to the artwork
above it. It is enlarged at capture time rather than in the HTML, so a fresh
export out of Claude Design never silently overwrites the correction. The
multiplier is on the settings panel.

## One at a time

Rendering saturates the CPU, and this VPS also serves www.acm.is. Two
concurrent renders would each be worse than half speed and would make the live
shop feel slow while they ran; queued, the first video is finished sooner
anyway. Several designs can still be queued in one action, which is the normal
case — a language pair and a desktop/mobile pair is four renders of one change.

## Why the renderer serves the files itself

A `.dc.html` fetches its `.jsx` scenes at runtime and a browser refuses that
from `file://`, so the page has to arrive over http. The obvious route is the
application's own `/api/claude-design/preview` — and that is a trap worth
recording, because it fails in a way that looks like success.

The renderer's Chromium has no operator session. An unauthenticated request is
caught by the auth middleware, which redirects to the sign-in page at
`AUTH_URL` — the public host. There, Cloudflare answers a headless browser with
a bot check, and the render captures *that page* instead of the design. It
completes, reports done, uploads a real MP4, and the file is a three-second
recording of "Performing security verification". Nothing errors.

A per-job token in a cookie does not fix it either: the middleware runs in the
Edge runtime and cannot see the queue's in-process state, so it redirects
before the route ever gets to check anything.

So the renderer starts its own static server on `127.0.0.1` with an
OS-assigned port, rooted at `CLAUDE_DESIGN_ROOT`, and closes it when the render
ends. No session, no middleware, no public host, nothing that leaves the
machine. `/api/claude-design/preview` remains, session-gated, for the operator's
own preview frame.

**The lesson for next time:** a render that finishes is not a render that
worked. Look at the poster.

## R2 layout

Inside `acm-workshop` (see `R2-WORKSHOP-BUCKET.md`):

```txt
claude-design/sources/<collection>/…      mirrored design trees
claude-design/videos/<collection>/x.mp4   rendered video
claude-design/videos/<collection>/x.jpg   its poster, one second in
```

The mirror never deletes. A file that has gone locally stays in the bucket,
because a file disappearing is far more often a mistake than a decision.

An overwrite is covered separately, because R2 has no object versioning to
lean on: before replacing an object the sync copies the existing one into
`claude-design/history/<sha256>/`. Together those two are why
`Claude-Design-Stuff` stopped being a git repository on 22-09-2026 - its
history was two commits, both "Initial commit", behind 214 MB that recorded no
change. That history is untouched at `github.com/hnodriturbo/claude-design-stuff`.

`zip-files/` and `exported-videos/` are outside the mirror, and were outside
git too. Rendered videos reach R2 through the render itself; those two folders
are local-only.

Uploading is triggered three ways: the **↑ R2** button beside a collection, the
**ACM - Update R2** desktop shortcut, and the daily scheduled R2 job.

## Checks after a change

```powershell
npx eslint src/components/ClaudeDesign*.jsx src/lib/claude-design src/app/api/claude-design
node --env-file=.env.local scripts/test-workshop-r2.mjs
node --env-file=.env.local scripts/sync-claude-design-r2.mjs --dry-run
npm run build
```

A three-second render is the quickest end-to-end proof. Use a `.dc.html`: that
is the case that needs the files served over http, and a self-contained `.html`
would pass without ever exercising it.

```powershell
node scripts/render-design-video.mjs `
  --dir "…\Claude-Design-Stuff\showroom\Arctic Crystal Memories showroom animation" `
  --file "Showroom Intro.dc.html" `
  --serve-root "…\Claude-Design-Stuff" `
  --out "$env:TEMP\test.mp4" --poster "$env:TEMP\test.jpg" `
  --size 1920x1080 --fps 30 --seconds 3
```

Then **open the poster and look at it**. A render that captured the wrong page
completes normally and uploads a perfectly valid MP4. Roughly 0.6 MB for three
seconds at 1080p is healthy; tens of kilobytes means the frames were nearly
blank, and something was captured that should not have been.
