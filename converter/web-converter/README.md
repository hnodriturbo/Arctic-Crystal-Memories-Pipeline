<!--
File: README.md
Purpose:
 - How the converter UI is wired and where to change things.
-->

# web-converter

Next.js 16 front end for `../pipeline-converter`. It uploads a file, runs one of
the Python scripts, streams the console output live, and offers the results for
download. Local tool — no auth, not meant to face the internet.

```powershell
npm run dev     # http://localhost:3000
```

## Configuration

`.env.local`:

```txt
CONVERTER_ROOT=D:\...\ACM-Pipeline\converter\pipeline-converter
CONVERTER_PYTHON=              # optional, defaults to CONVERTER_ROOT\.venv\Scripts\python.exe
```

Without `CONVERTER_ROOT` it falls back to `../pipeline-converter`, which is
correct for the normal checkout.

## Where things live

```txt
src/lib/operations.js     Operation catalogue - scripts, accepted types, options
src/lib/paths.js          Root resolution and the path-escape guard
src/app/api/upload        Streams a request body straight to input/uploads/
src/app/api/convert       Spawns Python, relays stdout as Server-Sent Events
src/app/api/files         Lists input/ and output/
src/app/api/download      Streams one file back
src/components/           ConverterClient, OptionFields, ConsoleLog
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
