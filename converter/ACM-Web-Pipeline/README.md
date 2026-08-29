<!--
File: README.md
Purpose:
 - How the converter UI is wired and where to change things.
-->

# ACM-Web-Pipeline

Next.js 16 operator front end for the image, Meshy, 2.5D and point-cloud
pipelines. It uploads files, streams Python output live, keeps each long-running
panel mounted, and carries results between stages without another upload.

```powershell
npm run dev     # http://localhost:3100
```

## Bookmarkable navigation

The selected workspace is canonical URL state, for example
`?view=meshy-review` or `?view=convert-export`. Refresh preserves the active
workspace, browser Back/Forward moves between selections, and unknown values
fall back safely to `?view=inputs-library`. Internal component ids are mapped
to stable public slugs in `src/lib/navigation.js`.

## Configuration

`.env.local`:

```txt
CONVERTER_ROOT=D:\...\ACM-Pipeline\converter\pipeline-converter
CONVERTER_PYTHON=              # optional, defaults to CONVERTER_ROOT\.venv\Scripts\python.exe
```

Without `CONVERTER_ROOT` it falls back to `../pipeline-converter`, which is
correct for the normal checkout.

## Crystal workflow

The 2.5D sidebar section is one continuous local workflow:

```txt
Leið A · fixed 2D crop
    ↓ composed PNG + Cockpit blank metadata
2.5D · depth.png → relief.glb + relief.obj → printer DXF
    ↓ finished relief GLB
Leið B · rotatable Three.js viewer
```

- Leið A reads every locally imported Cockpit3D 2D blank and uses projected
  OBJ masks where the product is not a bevelled box.
- Printer output uses the existing `pipeline-converter/code/mesh_to_pointcloud.py`.
  Automatic jobs target 250,000–1,000,000 points from source image area.
- Preview dot diameter is fixed at `0.08 mm`. Point spacing, minimum distance,
  Z distance and layer distance are separate production controls.
- Remote relief-library writes are disabled by default. Only
  `RELIEF_REMOTE_LIBRARY_ENABLED=true` opts a deployment into mirroring and
  pruning; local development does neither.
- `PIPELINE_DEV_AUTH_BYPASS=true` is accepted only under `next dev` for local
  visual QA. It has no effect in a production build.

## Where things live

```txt
src/lib/operations.js     Operation catalogue - scripts, accepted types, options
src/lib/paths.js          Root resolution and the path-escape guard
src/app/api/upload        Streams a request body straight to input/uploads/
src/app/api/convert       Spawns Python, relays stdout as Server-Sent Events
src/app/api/files         Lists input/ and output/
src/app/api/download      Streams one file back
src/components/           Leið A, relief, Leið B, converter and shared controls
```

## Adding an option or a script

Everything is driven from `src/lib/operations.js`. Add a `field` and the form
control appears and the flag reaches the command line; add an `OPERATIONS` entry
and a new card shows up. The UI has no per-script knowledge of its own.

Field types: `select`, `multiselect`, `number`, `text`, `boolean`, `file`.
A `file` field lists matching uploads from `input/` and the API resolves the
pick to an absolute path through the same escape check as the source file.

Each field carries a `group`, and `FIELD_GROUPS` decides section order, so a
long form stays navigable instead of turning into one flat wall of inputs.

## Theming

Light is the base palette in `globals.css`. Dark is defined twice - once under
`prefers-color-scheme` guarded by `:root:not([data-theme="light"])`, once under
`:root[data-theme="dark"]` - so the Auto/Light/Dark toggle wins in both
directions. A small script in `layout.js` applies a stored choice before first
paint, so a forced theme never flashes the other one.

Use the tokens (`bg-surface`, `text-muted`, `border-surface-border`, …) rather
than raw Tailwind colours; the console panel is the one deliberate exception,
keeping a dark ground in both themes.

## Notes

- Uploads are piped with `Readable.fromWeb`, never `formData()`, because a Meshy
  DXF runs past 300 MB and buffering one takes the dev server down.
- `/api/convert` reassembles lines across chunk boundaries; Python writes in
  chunks that do not respect newlines.
- `COLUMNS=200` is set on the spawned process so `rich` stops wrapping paths at
  80 characters.
- Every filesystem path goes through `resolveInside`, so a crafted name cannot
  read outside `input/` or `output/`.
