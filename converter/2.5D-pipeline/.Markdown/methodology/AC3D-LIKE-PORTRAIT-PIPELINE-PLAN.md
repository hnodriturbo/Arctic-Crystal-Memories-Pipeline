<!--
File: .Markdown/methodology/AC3D-LIKE-PORTRAIT-PIPELINE-PLAN.md
Purpose:
 - Define an evidence-led, independently implemented portrait pipeline that
   targets the useful visual properties measured in the AC3D reference.
-->

# Plan fyrir AC3D-líkt ACM portrait pipeline

## Meginregla

Við endurgerum ekki proprietary Cockpit internals. Við mælum sýnilegt output,
notum okkar eigin model stack og varðveitum öll milliskref í opnum sniðum.
Canonical master verður GLB; point-cloud og DXF verða afleidd lokaúttök.

## Gögn sem reference-módelið kennir okkur

Fyrir `amma` reference er source-facing surface um 67,3 × 127,5 × 28,9 mm og
198.063 triangles. Höfuðið er djúpt, framhlið flíkur þunn og allt portraitið
er búið til örlítið stærra en 80 × 120 kristalramminn áður en trim fer fram.
Svart print-mask svæði getur haft geometry án þess að verða laserprentað.

## Fyrirhugað flæði

```text
1. Original image evidence
   ↓
2. 2K upscale + semantic background mask
   ↓
3. Region ownership: head / hair / glasses / garment / background
   ↓
4. Independent depth candidates and confidence maps
   ↓
5. Source-camera fusion into one metric-mm surface
   ↓
6. Local occlusion backfill + bounded silhouette transition
   ↓
7. Oversized canonical GLB
   ↓
8. Crystal fit/trim in mm
   ↓
9. Laser sampling and DXF/XYZ/PLY export
```

## 1. Evidence og crop-regla

- Original pixel er eina ljósmyndafræðilega sönnunin.
- Background removal má hreinsa alpha/maska en ekki outpaint-a nýjan líkama.
- Þegar flík snertir myndramma verður sú brún `source-cut boundary`.
- Sjálfgefið er að hafa slíka flík þunna eða trimma hana við kristal; global
  frame-cut backfill er óvirkt.
- Hár, gagnsæ gleraugu og op milli hluta fá sér confidence, ekki binary maska.

## 2. Region ownership

| Svæði | Aðaluppspretta | Hlutverk |
|---|---|---|
| Andlit/höfuð | direct HRN/face mesh + landmarks | djúp native geometry, varðveitt detail |
| Hár | source-derived mask + depth shell | silhouette og yfirborð, ekki tilbúið snoð |
| Gleraugu | frame landmarks/template | sérstakt framfært geometry-lag |
| Háls/axlir | SMPL-X/HRN anchors + MoGe | mjúk anatomísk tenging |
| Fatnaður | MoGe/metric scene depth | raunverulegar fellingar, lægri dýpt |
| Bakgrunnur | MoGe + print mask | geometry aðeins þar sem samfelldur grunnur þarf |

## 3. Dýptarúthlutun

Ekki skal margfalda alla myndina með einni tölu. Við notum region-based mm
budget og lærum hlutföll af reference:

- höfuð/andlit fær hæsta convex dýptarsvið;
- háls og axlir fá mjúkt aukasvið;
- fatnaður helst marktækt þynnri;
- crop-brún verður ekki sjálfkrafa jafn djúp og öxl eða höfuð;
- nef, varir, haka og augnsvæði eru varðveitt með detail-weighted normals.

## 4. Gleraugu og staðbundin bakfylling

Gleraugu þurfa sér lag fremur en að vera aðeins intensity í face texture:

1. finna linsu- og rammalandmarks;
2. passa symmetric curve/frame template;
3. leggja rammann örlítið fyrir framan face surface;
4. nota nose/temple contact anchors;
5. fylla aðeins holrúmið sem opnaðist við færsluna með feathered occlusion
   backfill;
6. halda linsusvæði opnu eða merkja það sem ekki-prentað.

Þetta er sama tegund vandamáls og sést í reference, en lausnin verður okkar
eigin deterministic geometry-aðferð.

## 5. Transition í stað 90° veggjar

- Multi-ring transition færist aftur eftir normals og depth-gradient.
- 0,01 mm er geometric tolerance/glide threshold, ekki föst extrusion-dýpt.
- Feather og ring-count ráðast af local edge curvature.
- Raunveruleg occlusion-op eru varðveitt; aðeins staðfest seam/hole lokast.
- Frame-cut backfill er sér opt-in og með miklu minna dýptarsvið en silhouette.

## 6. Oversized master og crystal trim

Reconstruction keyrir fyrst án kristalforms. GLB varðveitir alla sýnilega myndina
og getur verið stærra en endanleg 80 × 120 mm prentsvæði. Kristalvalið kemur
síðan:

1. setja form og stærð í mm;
2. staðsetja/scale-a portrait án þess að breyta depth ratio;
3. sýna out-of-bounds overlay;
4. trimma geometry og print mask við inner printable volume;
5. varðveita ótrimmað master í projectinu.

## 7. QA-gates

Run má ekki verða samþykkt preset nema það standist:

- front, 30° og exact profile clay render;
- source-textured render;
- face/hair/glasses nærmynd;
- mm bounds og depth-by-region report;
- open-edge, non-manifold og self-intersection check;
- crystal out-of-bounds check;
- laser-dot preview og point-count budget;
- samanburð við frozen accepted/rejected galleries.

## Næsta controlled portrait-próf

Byggja nýja v3.4 candidate úr direct HRN front/head geometry, MoGe garment,
source-derived hair shell og sér eyeglasses layer. Nota 28,9 mm AC3D reference
sem samanburðarmark, ekki sem blinda föst dýpt. Prófa þrjú höfuðdýptarhlutföll
en halda fatnaðardýpt föstum. Velja niðurstöðu eingöngu úr neutral profile og
30° gallery.

