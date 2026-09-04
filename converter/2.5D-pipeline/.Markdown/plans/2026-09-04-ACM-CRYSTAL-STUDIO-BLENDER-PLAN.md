<!--
File: .Markdown/plans/2026-09-04-ACM-CRYSTAL-STUDIO-BLENDER-PLAN.md
Purpose:
 - Turn the existing local workbench and Blender helpers into a staged plan
   for ACM's own installable Windows portrait and crystal application.
-->

# ACM Crystal Studio: Windows + Blender framkvæmdaáætlun

## Ákvörðun

Fyrsta forritið byggir ofan á núverandi JavaScript/React/Three.js workbench og
Python pipeline. Electron verður Windows-shell, en Blender verður valfrjáls
geometry-worker og handvirkt advanced edit-rými. Þannig nýtum við það sem
þegar virkar í stað þess að endurskrifa UI í nýju tungumáli.

## Notendaflæði

```text
1 Myndvinnsla
  → 2 Model/profile
  → 3 Generate og QA
  → 4 Crystal fit, texti og export
```

### Skref 1 — Myndvinnsla

- velja original mynd;
- 2K upscale;
- BiRefNet/ISNet background removal;
- mask editor fyrir hár/gleraugu;
- sýna source-cut edges skýrt;
- vista original, processed image og mask án overwrite.

### Skref 2 — Model/profile

- velja samþykkt self-service preset eða research profile;
- sýna VRAM-áætlun fyrir 6 GB kort;
- region depth controls fyrir höfuð, axlir og flík;
- kristall eða `Ekkert form`; crystal val hefur ekki áhrif á reconstruction.

### Skref 3 — Generate og QA

- local job queue og progress/log;
- Three.js front/30°/profile viewer;
- source, clay, normals og depth modes;
- automatic topology/bounds report;
- Accept, Reject eða Continue research sem varðveitir gallery.

### Skref 4 — Crystal og edit

- velja kristalform/stærð í mm;
- move, rotate, scale og trim;
- bæta við texta sem sér geometry/object layer;
- sýna print mask og laser dots;
- exporta GLB, DXF, XYZ, PLY og project ZIP.

## Blender-hlutverk

Blender er ekki aðal-UI í fyrstu útgáfu. Það verður tvíþætt hjálpartæki:

1. **Headless worker:** scripted import, mesh checks, modifier stack, text-to-mesh,
   boolean trim, QA camera og GLB export.
2. **Open in Blender:** advanced manual lagfæring á gleraugum, sculpt, smooth,
   delete/fill, retopology og object placement.

Forritið býr til `.blend` vinnuafrit og JSON edit-manifest. Original GLB helst
óbreytt. Eftir Blender-edit er ný GLB revision flutt aftur inn í sama project.

## Áfangar

### A. Vertical slice

- Electron opnar núverandi local workbench.
- App ræsir/stöðvar Python worker örugglega.
- Import → remove background → load existing GLB → save `.acmcrystal`.
- Development installer keyrir á þessari tölvu.

### B. Blender bridge

- finna uppsettan Blender executable;
- `Open in Blender` með tilbúnu workspace, cameras og mm-units;
- `Return revision` exportar GLB og QA renders;
- texti er editable curve þar til export fer fram.

### C. Crystal/laser toolchain

- opið crystal-template JSON;
- non-destructive fit/trim;
- point spacing, Z layers, toning og budget;
- DXF/XYZ/PLY export í sér worker-processi.

### D. Installer og recovery

- Electron Forge/electron-builder installer;
- per-project autosave og crash recovery;
- dependency/VRAM health check;
- code signing áður en forritinu er dreift til annarra.

## Fyrsta Blender kennslulota

Nota endurbyggða `amma-ci-scene-mm.glb`:

1. import með `File → Import → glTF 2.0`;
2. staðfesta Metric og millimetra;
3. skoða front/side og toggla wireframe;
4. duplicate-a object áður en edit hefst;
5. læra Vertex/Edge/Face select, proportional editing og Sculpt Smooth;
6. setja einfaldan texta sem Curve, extrude-a og staðsetja;
7. exporta nýja GLB revision og bera hana saman í workbench.

Þessi lota breytir ekki sjálfkrafa reference-GLB-inu og gefur okkur fyrsta
raunverulega edit workflow-ið fyrir Windows-forritið.

