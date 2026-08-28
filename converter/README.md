<!--
File: README.md
Purpose:
 - Orient anyone opening the converter project for the first time.
-->

# Crystal Converter

Three pipelines that chain in one direction, plus the web UI that drives all of
them. Self-contained: nothing here depends on the main website, and the whole
`converter/` folder is what gets deployed to `pipeline.acm.is`.

```txt
converter/
├── image-pipeline/       Python CLI - clean a photograph
├── meshy-pipeline/       Workspace - photograph to 3D model, via the Meshy API
├── pipeline-converter/   Python CLI - 3D model to printable point cloud
└── web-converter/        Next.js 16 UI that drives all three
```

```txt
a photograph
    │  image-pipeline      restore, upscale, cut the subject out
    ▼
a clean cut-out
    │  meshy-pipeline      Meshy generates geometry from it
    ▼
an OBJ or GLB
    │  pipeline-converter  sample the surface into a dot cloud, fit to a blank
    ▼
a DXF the SSLE engraver reads
```

Each stage is usable on its own, and each hands its result to the next with one
button in the UI. Start anywhere: an existing model can go straight into the
converter, and a photograph that is already clean can go straight to Meshy.

## The two formats that matter

**Cockpit3D / SSLE point DXF** — what the engraver reads. `POINT` entities only,
on layer `VWX`, millimetres, centred on the origin, two decimal places,
sequential integer handles. Roughly 0.07 mm between dots; closer than that
over-burns the glass.

**Mesh DXF / OBJ** — what Meshy, Blender and CAD tools produce. `3DFACE`
entities or `v`/`f` lines describing a surface, not a cloud of dots.

These are not interchangeable. A mesh handed straight to the engraver has no
dot spacing and no crystal fit, which is why `mesh_to_pointcloud.py` exists.

## Quick start

```powershell
cd web-converter
npm run dev        # http://localhost:3000
```

Everything is driven from there. For a one-off from the command line:

```powershell
cd pipeline-converter
.\.venv\Scripts\python.exe code\mesh_to_pointcloud.py `
    --file "input\your-model.obj" --template 60x80x40 --points 750000 --upright y
```

Each pipeline has its own venv and its own README. `web-converter/.env.example`
lists every setting; `DEPLOY-VPS.md` covers the server.

## 2.5D or full 3D

Cockpit3D's own workflow, and 3dcrystal.com's, is 2.5D: a photograph becomes a
relief, deepest where the image is brightest. `mesh_to_pointcloud.py --texture`
does the same thing.

The Meshy stage makes the other option real — a genuine 3D bust, solved from
one photograph, with a back and sides that exist. It costs more depth than a
relief does, and depth is the binding constraint in a crystal, so read the
fitting note below before assuming a full 3D subject will fit the blank you had
in mind.

## Fitting a model to a crystal

A full 3D subject is almost always **depth-limited**. A 60x80x40 mm blank with a
5 mm border leaves 50 x 70 x 30 mm of engravable space, and 30 mm of depth runs
out long before the height does. Use a deeper blank (`80x50x50` gives 44 mm) if
the subject needs to be larger.

`--upright y` pins the model's Y axis to crystal height. Without it,
`--auto-orient` will happily lay a church tower on its side to win a bigger
scale. Check which source axis actually points up before choosing.

`--depth-axis` picks which face points at the viewer. Two mappings often tie
on size while showing completely different elevations, so choose deliberately
rather than letting the tie-break decide.

## Making glass read as a photograph

Even dot spacing produces a model in the glass. A photograph needs dot
**density** to follow image brightness, which is what Cockpit3D's `Toning`
does and what `--texture` does here:

```powershell
python code\mesh_to_pointcloud.py --file "input\model.obj" `
    --texture "input\photo.jpg" --toning 1.8 --layers 8 --stagger 2
```
