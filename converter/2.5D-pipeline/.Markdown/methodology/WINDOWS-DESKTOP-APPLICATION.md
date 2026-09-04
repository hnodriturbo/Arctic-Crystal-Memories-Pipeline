<!--
File: .Markdown/methodology/WINDOWS-DESKTOP-APPLICATION.md
Purpose:
 - Give a beginner-friendly plan for turning the local 2.5D workbench into ACM's first Windows application.
-->

# Fyrsta Windows-forritið: ACM Crystal Studio

## Markmið

Byggja eigið local Windows-forrit með sambærilegu **verkflæði** og gagnlegustu
hlutar Cockpit3D, en með eigin kóða, eigin útliti og opnum skráarsniðum:

```text
mynd → image prep → 2.5D módel → kristal/crop → point cloud → DXF → QA
```

Forritið á að geta virkað án internets. Fyrsta útgáfa þarf ekki að leysa allt;
hún þarf að opnast sem venjulegt Windows-forrit og keyra núverandi local
workbench á áreiðanlegan hátt.

## Ráðlagður tæknigrunnur

| Lag | Tækni | Tungumál | Ástæða |
|---|---|---|---|
| Desktop shell | Electron | JavaScript | Nýtir núverandi React-þekkingu og getur ræst Python worker. |
| UI | React + CSS | JavaScript/JSX | Núverandi 1→2→3→4 workbench færist nær óbreyttur. |
| 3D viewer | Three.js | JavaScript | GLB, kristall, músarsnúningur og laser-dot preview eru þegar virk. |
| Pipeline worker | Python | Python | MoGe, ICON/ECON adapters, mesh og DXF-kóði eru þegar til. |
| Windows hjálparskriptur | PowerShell | PowerShell | Setup, health-check og local packaging. |
| Seinni hraðahlutar | CUDA/C++ aðeins ef þarf | C++/CUDA | Ekki fyrsta skref; aðeins eftir mældan flöskuháls. |

Microsoft mælir með WinUI 3 fyrir ný native Windows-forrit með C#/C++ og XAML.
Það er góð framtíðarleið ef við viljum fullkomlega native UI. Fyrir **fyrsta**
forritið er Electron þó lægri áhætta hér, því vinnandi React/Three.js UI er
þegar til og Electron main-process getur stjórnað local worker. Opinber skjöl:

- [Electron process model](https://www.electronjs.org/docs/latest/tutorial/process-model)
- [Electron distribution overview](https://www.electronjs.org/docs/latest/tutorial/distribution-overview)
- [Microsoft Windows app development](https://learn.microsoft.com/en-us/windows/apps/)
- [WinUI 3 overview](https://learn.microsoft.com/en-us/windows/apps/winui/winui3/)

## Öryggismörk

- Renderer fær ekki óheft Node-aðgengi.
- `contextIsolation` og sandbox eru virk.
- Aðeins skýrt skilgreind IPC-köll mega velja skrá, ræsa job og opna artifact.
- Python API bindur aðeins á loopback eða er ræst sem child process með
  handahófskenndum local port/token.
- Pipeline les og skrifar aðeins í valda project/run-möppu.
- Originalmynd er aldrei skrifuð yfir.

## Fyrstu áfangar

### 0. Núverandi local prototype

- React/Three.js workbench á `localhost:3000`.
- Python API á `127.0.0.1:8425`.
- Image-pipeline og 2.5D jobs vista stór gögn undir `output/local-workbench`.

### 1. Desktop shell

1. Bæta `desktop/` við **2.5D research-svæðið**, ekki production-vefinn.
2. Electron main-process ræsir workbench og Python worker.
3. Einn `BrowserWindow` opnar 1→2→3→4 UI.
4. App lokar child processes snyrtilega þegar glugganum er lokað.
5. Búa til development build sem opnast með tvísmelli.

### 2. Eigið verkefnissnið

- `.acmcrystal` ZIP-container með JSON manifest, GLB, source/processed PNG,
  mask og stillingum.
- Save, Save As, Open og autosave recovery.
- Engin `.cockpit` eða `.ci` authoring.

### 3. Geometry-vinnusvæði

- mm-accurate kristalform eða `Ekkert form`.
- Move, rotate, uniform scale og crop/slice í mm.
- Surface/laser-dot view og mælanlegt depth-percent.
- Mesh bounds, triangle/vertex count og out-of-bounds viðvaranir.

### 4. Point-cloud og DXF

- Nota núverandi `pipeline-converter` sem worker.
- Stýra XY spacing, Z spacing/layers, toning og max points.
- Vista standard DXF/XYZ/PLY og fullan QA-manifest.

### 5. Installer

Electron þarf packaging, code signing og installer. Fyrsta local build má vera
unsigned development-installer; dreifing til annarra véla þarf síðar code
signing svo Windows SmartScreen treysti útgefandanum. Electron mælir með
Electron Forge eða sambærilegu packaging-tóli. Ef `electron-builder` verður
valið er NSIS sjálfgefin Windows-installer leið:

- [Electron packaging/distribution](https://www.electronjs.org/docs/latest/tutorial/distribution-overview)
- [electron-builder NSIS](https://www.electron.build/docs/nsis/)

## Fyrsta kennsluverkefnið

Fyrsta installable útgáfan á aðeins að gera þetta:

1. Opna ACM Crystal Studio.
2. Velja eina mynd.
3. Keyra 2K + background removal.
4. Opna samþykkt GLB eða nýtt local run.
5. Skoða GLB með 18% dýpt, með eða án kristals.
6. Vista/opna `.acmcrystal` project.

Þegar þessi lóðrétti biti er stöðugur bætum við crop, slicing, point-cloud og
DXF við í litlum mælanlegum skrefum.

## Blender sem vinnuforrit

Blender verður valfrjálst advanced edit-rými og headless geometry-worker:

- scripted import/export og mm-staðfesting;
- texti sem sér Curve/Mesh object;
- crystal boolean trim og non-destructive modifier stack;
- manual sculpt/smooth eða gleraugnalag þegar sjálfvirkni dugar ekki;
- sjálfvirk front, 30° og profile QA-render;
- ný revision fer aftur í `.acmcrystal`, original GLB er aldrei skrifað yfir.

Nánari framkvæmdaáætlun er í
[Windows + Blender planinu](../plans/2026-09-04-ACM-CRYSTAL-STUDIO-BLENDER-PLAN.md).
