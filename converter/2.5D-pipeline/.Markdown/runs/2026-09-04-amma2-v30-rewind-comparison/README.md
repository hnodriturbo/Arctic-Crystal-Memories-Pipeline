<!--
File: .Markdown/runs/2026-09-04-amma2-v30-rewind-comparison/README.md
Purpose:
 - Record the isolated v3.0 rewind on amma-2 and compare it with the preserved
   v3.1, v3.2, v3.3 and AC3D/Cockpit portrait evidence.
-->

# `amma-2` v3.0 rewind og v3.1–v3.3 samanburður

Staða: **REJECTED sem portrait-output; varðveitt sem mikilvægt evidence**.

## Markmið

Keyra óbreytta v3.0 uppskrift aftur á sömu erfiðu nærmynd af eldri konu með
gleraugu. Prófið átti að skera úr um hvort fyrsta fullkláraða v3-ferlið hefði
varðveitt andlit, gleraugu og útlínustrekkingu betur en v3.1, v3.2 og v3.3.

Skrárnar staðfesta að v3.0 var fyrsta fullkláraða self-service candidate-ið.
V3.1 og v3.2 voru síðar merkt rejected; v3.3 er candidate með óleyst hár,
gleraugu og neck/body stitch.

## Óbreytt v3.0 uppskrift

```text
BiRefNet RGBA source
  -> Mask R-CNN person detection
  -> PARE body fit
  -> official ICON front normals
  -> ECON d-BiNI adaptive-fillet front surface
  -> exact source-camera registration
  -> MoGe-2 ViT-L exact-source depth
  -> PARE/MoGe scene fusion
  -> silhouette depth-skirt v3
  -> crystal-tone GLB
```

ECON-stigið var keyrt með `--keep-stretched-faces`. Depth-skirt-stigið dró
1.610 boundary edges aftur að MoGe scene-depth með 0,025 lágmarksdýpt. Þetta er
því raunverulegt próf á stretching/filler-hugmyndinni, ekki aðeins ný depth-map.

## Mælingar

| Mæling | Ný v3.0 rewind-keyrsla |
|---|---:|
| Source SHA-256 | `459fd99b...6774f516` |
| Source-stærð | 946 × 2.048 px |
| Source-camera inliers | 464 / 478 |
| Inlier ratio | 0,970711 |
| Miðgildi reprojection error | 0,167051 px |
| ECON human surface | 85.436 vertices / 169.260 triangles |
| MoGe scene layer | 3.123 vertices / 5.080 triangles |
| Depth-skirt | 1.610 boundary edges / 3.220 triangles |
| Skirt-dýpt, miðgildi | 0,279931 scene units |
| Skirt-dýpt, hámark | 0,546922 scene units |
| Lokaúttak | 91.347 vertices / 177.560 triangles / 3 layers |

Nýja runnið og upprunalega v3.0 hafa sömu topology og sömu source-camera
skráningu, en eru ekki byte-identical. PARE/ICON payload og human-depth anchor
breyttust milli keyrslna; meðal absolute vertex-breyting var 0,009755 scene
units og hámark 0,565053. Failure-classið er engu að síður það sama í neutral QA.

## Sjónræn niðurstaða

### Það sem v3.0 gerir betur

- Meira staðbundið face-relief sést en í mjúku v3.1/v3.2 heightfieldunum.
- Nef, munnur og hrukkur fá greinilegri front-surface merki.
- Filler/skirt er raunverulega til staðar og lokar hluta silhouette-brúnarinnar.

### Það sem fellir v3.0

- PARE full-body prior er rangt routing fyrir close portrait og myndar
  merkingarfræðilega rangt dýptarsvið.
- Gleraugu verða að mestu relief/appearance í sama andlitsfleti; rammi og linsur
  verða ekki hreint sjálfstætt geometry-lag.
- Depth-skirt og stretched faces mynda langa lárétta gadda í 30° og profile.
- Aðskilinn alpha-hlutur fyrir ofan hárið lifir sem fljótandi scene-layer.
- Hair/silhouette jaðarinn verður tenntur og ekki framleiðsluhæfur.

V3.1 og v3.2 fjarlægja verstu full-body hallucinationina en verða of flöt og
missa identity-detail. V3.3 gefur besta höfuðrúmmálið með native HRN topology,
en hárið og gleraugun vantar enn og neck/body boundary er ólokið. Engin v3.x
niðurstaða stenst því loka portrait-gate á þessari mynd.

![V3.0–v3.3 og AC3D samanburður](artifacts/gallery/00-contact-sheet.jpg)

## Ákvörðun

Ekki endurvekja v3.0 sem almennt portrait-preset. Varðveita það sem donor fyrir:

1. skarpara source-aligned local face relief;
2. controlled, region-bundið stretching filler;
3. mælanlega source-camera registration.

Næsta run á að byrja á v3.3/native HRN head volume, bæta við source-aligned
gleraugnamaska og sérstöku frame/lens geometry-lagi og nota local backfill aðeins
bak við framfærðan gleraugnaramma. AC3D/Cockpit viðmiðið sýnir markhegðunina:
gleraugun mega deila hluta surface-ins, en stretching verður að vera staðbundin
og mega ekki mynda silhouette-gadda yfir allt höfuð eða fatnað.

Sjá [artifact index](ARTIFACTS.md) og
[full-resolution samanburðargallerí](artifacts/gallery/README.md).
