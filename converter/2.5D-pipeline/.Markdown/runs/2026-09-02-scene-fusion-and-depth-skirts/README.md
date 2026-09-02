<!--
File: .Markdown/runs/2026-09-02-scene-fusion-and-depth-skirts/README.md
Purpose:
 - Record human/scene layer fusion and the first measurable silhouette depth-skirt variants.
-->

# Run family: PARE human + MoGe scene + depth skirts

## Human/scene fusion v1 — candidate

Samþykkt PARE+ICON+ECON geometry á human-maskinu var sameinuð MoGe-lagi fyrir
restina af myndinni. MoGe scene mesh notar stride 3 og 0,35 scene-unit robust
depth span. Human local depth er óbreytt; MoGe gaf aðeins litla global offseta:
maður +0,005873, kona −0,010043 scene-units.

- Scene: 60.134 vertices / 116.702 triangles.
- Combined: 186.246 vertices / 365.952 triangles.
- Náttúrulega arm-bilið helst opið og sýnir MoGe-lagið aftar.
- 30°/45° QA sýndi að formlegt backfill vantaði við silhouette.

![Scene fusion v1](artifacts/gallery/scene-fusion-v1.jpg)

## Rejected gap-fill v2

Tilraun til að fylla arm-bilið var hafnað af notanda: bilið er raunverulegt
occlusion-bil. Global d-BiNI re-integration jók einnig dýpt manns úr 0,523745 í
0,842873 og myndaði óæskilega rauf. Kóðaleiðin var fjarlægð; evidence er geymt.

![Rejected gap fill](artifacts/gallery/rejected-gap-fill-v2.jpg)

## Depth-skirt v3 — candidate

Hver boundary-edge fær back-duplicate við sampled MoGe depth og tvö triangles
sem mynda stýrða útlínustrekkingu. Innri arm-opnunin er ekki fyllt; hún fær sinn
eigin jaðar sem teygist aftur og sýnir scene-lagið fyrir aftan.

- Maður: 1.568 boundary edges / 3.136 skirt triangles.
- Kona: 1.404 boundary edges / 2.808 skirt triangles.
- Combined: 193.551 vertices / 374.592 triangles.
- 0 px scene clearance var betra en 2 px variant.
- Ytri back-edge join og lárétt banding þarf áfram refinement áður en samþykkt.

![Depth skirts v3](artifacts/gallery/depth-skirts-v3.jpg)

## Local galleries

```text
output/research/scene-fusion/pare-icon-econ-moge2-both-together-v1/artifacts/gallery/
output/research/source-camera-fusion/both-together-ai-enhanced-pare-repaired-v2/artifacts/gallery/
output/research/scene-fusion/pare-icon-econ-moge2-clearance0-depth-skirts-v3/artifacts/gallery/
```

Sjá [artifact skrá](ARTIFACTS.md).
