<!--
File: README.md
Purpose:
 - What lives in this workspace and what the Meshy stage actually does.
-->

# meshy-pipeline

The workspace for the middle stage — photographs in, 3D models out, via
[Meshy](https://www.meshy.ai). The production API client lives in
`../web-converter/src/lib/meshy/`; this folder is its persistent workspace and
owns a small, isolated Python 3.11 diagnostics environment.

```txt
image-pipeline  →  meshy-pipeline  →  pipeline-converter
photograph          3D model           point cloud the engraver reads
```

## Folders

```txt
input/            photographs waiting to be generated from
work/             clean-up intermediates, if the job asked for any
output/<job-id>/  one folder per generation: job.json plus everything downloaded
code/              deployment/runtime health checks
.venv/             Python 3.11 support environment (local/shared, never Git)
```

All git-ignored — a single job can pull down several hundred megabytes.

## Python environment

The Meshy API runner itself is Node.js. This third Python environment is kept
separate so diagnostics and future Meshy-side utilities never pull image or
point-cloud packages into the wrong pipeline:

```bash
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python code/healthcheck.py
```

The health check performs no generation and spends no credits.

## The job manifest

Every generation writes `output/<job-id>/job.json`, which is the only record
that survives a restart. It carries the settings used, the Meshy task id, what
Meshy actually charged (`consumedCredits`, not the estimate), the crystal blank
chosen, and the list of files that came back.

Job ids are `YYYYMMDD-HHMMSS-subject`, so `output/` sorts chronologically on
its own.

## What settings actually matter for glass

The engraver reads geometry and nothing else, which inverts most of Meshy's
defaults:

- **`should_texture: false`.** Saves 10 credits and returns the bare grey mesh
  that is the useful output. Colour cannot survive engraving.
- **`should_remesh: false`.** Keeps Meshy's raw high-density surface. The
  point-cloud sampler wants as much surface detail as it can get; remeshing
  down to 30,000 polygons throws away exactly what it is there to read.
- **`ultra_mode: true`.** +5 credits on meshy-7 for noticeably crisper
  geometry. Worth it here in a way it is not for a game asset.
- **`image_enhancement: true`.** Meshy's own pre-pass, independent of anything
  the image pipeline did.

A typical portrait run is therefore 25 credits: 20 for meshy-7 untextured, plus
5 for ultra mode.

## Sizing

`scale_to_crystal` runs an extra Meshy remesh (+5 credits) that resizes the
export to the blank's usable height in real millimetres. It is optional and off
by default, because `mesh_to_pointcloud.py` refits the model to the blank
regardless — the resize only makes the downloaded file itself measure correctly
in Blender or a slicer.

## Webhooks

`https://pipeline.acm.is/webhooks/meshy` receives task-status callbacks, handled
by `../web-converter/src/app/webhooks/meshy/route.js`. Nothing depends on it —
the runner polls — but it lets a job whose browser tab was closed still finish
its manifest correctly.

Meshy's documentation does not name the signature header, so the route checks
every plausible one and logs the headers of an unsigned delivery to
`webhook-headers.log` here. Once a real delivery has been seen, pin the scheme
down in that route and drop the fallback.
