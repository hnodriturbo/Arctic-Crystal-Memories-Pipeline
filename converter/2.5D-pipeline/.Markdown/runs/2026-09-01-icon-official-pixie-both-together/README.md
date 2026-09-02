<!--
File: .Markdown/runs/2026-09-01-icon-official-pixie-both-together/README.md
Purpose:
 - Preserve the first successful official ICON + PIXIE experiment on the AI-enhanced couple image.
-->

# Run: official ICON + PIXIE — AI-enhanced `both_together`

## Niðurstaða

Opinbera ICON-pipeline-ið keyrði báða einstaklingana að fullu á Windows/RTX 3060. Predicted front normals eru skýr og verðmæt 2.5D milliniðurstaða. Hráa 256³ full-3D reconstruction er lokað og tæknilega rétt, en sléttar of mikið af andlits-/fatnaðardetail og sýnir voxel/ring artifacta. ICON verður því normal/anatomy prior, ekki óbreytt loka-2.5D output.

Engin ECON, HRN, MoGe-2, ACM Composer, texture projection, útlínustrekking eða crystal-scaling var keyrð ofan á niðurstöðuna.

## Input

Upprunalegt AI-enhanced source:

```text
input-testers/amma-og-afi/for3d/both_together.png
```

- Stærð: 1086×1177 RGBA, 1.939.663 bytes.
- SHA-256: `A39599AF402AAB74726C9276BAC593A44039408050E00EDE934E267AA8F0F2F1`.

Mask R-CNN fann tvo einstaklinga:

| Subject | Score | Detector box `x1,y1,x2,y2` | Crop með 64 px margin | Canvas hash |
|---|---:|---|---|---|
| maður | 0,967422 | `3,2,585,1174` | `0,0,649,1177` | `40EF3BD1D425CB313AB436865E5947558BF4DE2BEBF5F7DBEC312A919ADC964E` |
| kona | 0,973787 | `550,40,1084,1132` | `486,0,1086,1177` | `43B68260D1BC0E675B6F901F663E6EC947958C013C71303ADE89741B08CBC399` |

Hvort crop var miðjað á gegnsætt 1177×1177 canvas án resampling. Þetta varðveitir pixla og líkamsproportion en gefur ICON einn dominant einstakling per input.

## Model stack sem var raunverulega notað

1. Torchvision Mask R-CNN COCO: hæst skoraða person bbox innan hvors canvas.
2. rembg U2Net: foreground mask fyrir ICON-crop.
3. PIXIE + SMPL-X 2020: pose, camera, shape, expression, head og hand prior.
4. Official ICON `normal.ckpt`: front/back clothed-human normals.
5. Official ICON `icon-filter.ckpt`: implicit occupancy með normal/image og geometry features.
6. Lossless 256³ sampling + marching cubes: hrátt lokað `*_recon.obj`.
7. Upstream 50k remesh var skrifað en ekki valið sem aðalartifact.

Ekki notað: PARE, ECON/d-BiNI, cloth refinement, HRN, MoGe-2, texture eða ACM geometry tools.

## Stillingar

| Stilling | Gildi |
|---|---:|
| HPS | `pixie` |
| SMPL-X fitting iterations | 100 |
| Cloth refinement iterations | 0 |
| Visualization frequency | 10 |
| GPU | 0 |
| Effective marching-cubes resolution | 256³ |
| Input count | 2 person canvases |

Athugið: config-skráin inniheldur `mcube_res: 512`, en official `apps/infer.py` override-ar gildið í 256 við inference.

## Keyrsluskipun

```powershell
.\code\research\run_icon_windows.ps1 `
  -cfg .\Models\research\ICON\source\ICON-official\configs\icon-filter.yaml `
  -gpu 0 `
  -in_dir .\output\research\icon-official\both-together-ai-enhanced-pixie\input-persons `
  -out_dir .\output\research\icon-official\both-together-ai-enhanced-pixie\result `
  -hps_type pixie `
  -loop_smpl 100 `
  -loop_cloth 0 `
  -vis_freq 10
```

Wall-clock fyrir bæði inntök: **4 mínútur 34 sekúndur**.

## Geometry output

| Raw OBJ | Vertices | Triangles | Extents XYZ | Watertight | Components | SHA-256 |
|---|---:|---:|---|---|---:|---|
| `man_recon.obj` | 115.132 | 230.304 | `0.884929, 1.867693, 1.063526` | já | 1 | `978180487814816E55527F03B987D73ECB960F2AC6D57131F02D81DC3CE3F6D7` |
| `woman_recon.obj` | 105.137 | 210.326 | `0.910883, 1.877182, 0.849204` | já | 1 | `A92495559F5B76B91831CA687A3FE6AB7253D93B99E2685E78F55E1A455C0871` |

Samtals: **220.269 vertices og 440.630 triangles**.

Upstream `*_remesh.obj` er 50.000 triangles á mann og er ætlað cloth-refinement. Það er ekki density target eða aðaloutput þessa runs.

## Normal output

`*_smpl.png` geymir 5×2 official QA-grid. `extract_icon_normal_maps.py` tók `cloth-norm(pred)` front/back 512×512 visualization-cell úr gridinu án resampling. Rauði upstream-titillinn er inni í bakgrunnspixlum; þetta er því nákvæmt QA-cell, ekki enn hrátt tensor-export.

| Visualization | SHA-256 |
|---|---|
| `man_normal_F.png` | `5CA87AB6E7132C67ABACF706E6571337BCDFB6EFA48088F3CBC90DD43F167CC9` |
| `woman_normal_F.png` | `0A3FB3295CCC4596154F26FD5D11676BD3FBD36A8265DB89F20C654D498A5F23` |

## Sjónmat

### Notendamat eftir skoðun í Blender

`man_normal_F.png` og `woman_normal_F.png` eru samþykktar sem langréttasta posture- og human-shape niðurstaðan í rannsókninni hingað til. Þær fylgja upprunalegu líkamsstöðu og skörun handa mun betur en fyrri heildarmöskvar.

`both_together_icon_official_pixie_front.png`, `*_45deg.png`, `*_profile.png`, raw GLB og QA `.blend` eru **ekki samþykkt geometry-baseline**. Sérstaklega er 45° posture/útlit ekki nógu trútt source. Þau eru varðveitt sem neikvæð sönnun fyrir því að implicit closure/marching-cubes skrefið eyðileggur hluta af upplýsingunum sem sjást í predicted normals.

Blender-QA senan normalize-ar og staðsetur einstaklingana hlið við hlið en breytir ekki innri geometry. Import á raw GLB sýnir því sömu takmörkuðu geometry; Blender-útgáfan sjálf lagar ekki þessa niðurstöðu.

Sterkt í predicted front normals:

- höfuðhalli og líkamsstaða fylgja source;
- enni, nef, kinnar, háls og coarse andlit;
- peysu- og ermafellingar;
- samsetning handleggja og handa;
- skýr silhouette fyrir sitjandi líkama.

Veikt í 256³ closed reconstruction:

- identity og andlitsdetail mýkist verulega;
- hár og gleraugu verða ekki rétt geometry;
- lárétt marching-cubes/voxel-ribbing sést á bol og hliðum;
- óstaðfest bakhlið og 360° closure bæta við geometry sem kristal-2.5D þarf ekki;
- engin source texture eða sameiginleg source-camera registration fylgir hráa OBJ.

## Ályktun

ICON staðfestir að whole-human normals/prior leiðin er rétt. Samþykkt ICON-baseline þessa runs eru front-normal upplýsingarnar, ekki raw closed mesh. Næsta samþykkta skref er að stöðva fyrir implicit closure og samþætta `normal_F` í þéttan source-facing front-flöt. ECON front-only er enn sterkari immediate geometry baseline, en ICON gefur direct PARE-vs-PIXIE rannsóknarleið og annan normal prior.

## Skrár

- [Uppsetning og bilanagreining](INSTALLATION-AND-TROUBLESHOOTING.md)
- [Artifact skrá](ARTIFACTS.md)
- [Runtime versions](requirements/RUNTIME-VERSIONS.md)
- [Frozen ICON overlay requirements](requirements/requirements-icon-windows-py38.txt)
- [Checksums](CHECKSUMS.sha256)
- `code-snapshot/`: exact launcher, preprocess, normal extraction, renderer, requirements og patch-afrit.
