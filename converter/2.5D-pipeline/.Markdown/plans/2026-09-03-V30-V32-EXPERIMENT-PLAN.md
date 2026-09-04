<!--
File: .Markdown/plans/2026-09-03-V30-V32-EXPERIMENT-PLAN.md
Purpose:
 - Define the next controlled experiments for the two-person v3.0 and portrait v3.2 branches.
 - Keep model ownership, face protection, and silhouette-stretch parameters auditable.
-->

# Tilraunaáætlun 2026-09-03: v3.0 og v3.2

## Sameiginlegar reglur

1. „3D“ merkir source-facing 2.5D nema annað sé tekið fram.
2. V3.0 og v3.2 eru tvær aðskildar reconstruction-leiðir; niðurstöðum þeirra er ekki blandað óskoðað.
3. Sömu source-skrár og fryst checkpoint eru notuð aftur og aftur.
4. Ein breyta er breytt í einu innan hverrar parameter-runu.
5. Hvert afbrigði fær nýja möppu, config, model-route, checksum og front/30°/45°/profile QA.
6. Neutral geometry og B/W source appearance eru alltaf metin sitt í hvoru lagi.
7. Ekkert output er kallað samþykkt fyrr en mannlegt QA hefur skráð `accepted`.

## Braut A — v3.0: gömlu hjónin, tveir einstaklingar með líkama

### Frystur árangur

V3.0 er **successful að ákveðnu marki** fyrir mynd með tveimur sýnilegum efri líkömum. PARE/ICON/ECON myndaði source-derived human front surfaces og MoGe var notað sem scene/missing-area fill. Þetta er áfram gild baseline; gallarnir við strekkingu ógilda ekki mannflötinn.

### Model ownership

- PARE: pose/occlusion-aware structural prior fyrir hvorn einstakling.
- ICON/ECON d-BiNI: sýnilegur líkami, fatnaður, höfuð, háls og hendur.
- MoGe-2: aðeins non-human eða sannanlega vöntuð svæði.
- Source texture/alpha: appearance og silhouette.
- Útlínustrekking: sjálfstætt post-process eftir að front surface er fryst.

### A0 — nákvæm endurgerð baseline

- Endurkeyra síðasta samþykkta checkpoint án breytinga.
- Staðfesta input/output hashes og triangle count.
- Merkja hvaða pixels/triangles koma frá human surface og hvaða koma frá MoGe fill.
- Varðveita raunveruleg occlusion-bil milli handa, handleggja og bols.

### A1 — staðfest MoGe exclusion

- MoGe má ekki endurreikna pixels sem tilheyra samþykktum human surfaces.
- Búa til sýnilegt ownership-map:
  - human/ECON;
  - MoGe fill;
  - transition;
  - transparent/unused.
- Bera saman við v3.0 baseline áður en strekking er bætt við.

### A2 — parameter-matrix fyrir sliding stretch / útlínustrekkingu

Byrja á sama frysta v3.0 front mesh. Breyta aðeins einum flokki í einu:

| Run | Breyta | Gildi |
|---|---|---|
| A2.1 | ring count | 4, 8, 12 |
| A2.2 | inset | 0,25; 0,50; 0,75 |
| A2.3 | maximum back-depth | 0,5; 1,0; 1,5; 2,5 |
| A2.4 | boundary smoothing iterations | 0, 8, 16, 32 |
| A2.5 | easing | smoothstep, cosine, cubic |
| A2.6 | adaptive depth | fast við brattar brúnir, shallow við hár/fínar brúnir |

QA metur:

- hvort strekkingin fari aftur en ekki fram;
- hvort hún myndi sýnilegan vegg/rim;
- hvort hún loki raunverulegum bilum;
- hvort hár, eyru og hendur rifni;
- hvort 30–45° útlit nálgist AC3D án óstaðfestrar 360° completion.

## Braut B — v3.2: ein erfið close-portrait mynd

### Föst ownership-regla

- **Höfuð og andlit:** aldrei MoGe og aldrei almennt depth-smoothing.
- **Háls, bolur og fatnaður:** MoGe má vinna utan HRN head-lock mask.
- **Hár:** source silhouette/appearance tengt við head prior; ekki sjálfstæður djúpur MoGe-kambur.
- **Nef:** native head geometry varðveitt; nefbroddur verður fremsti samfelldi punktur innan nose ROI.

### Staða v3.2-a

Fyrsta head-lock heightfield-prófið staðfesti:

- MoGe head pixels: `0`;
- global head/face smoothing: `false`;
- nose prominence: um `0,1577` af normalized relief, eða um `3,15 mm` við 20 mm working relief;
- mesh: 363.105 vertices / 722.732 triangles.

Það er **rejected/informative**, ekki samþykkt:

- native HRN detail tapast enn við raster/depth-map millistig;
- source-alpha hair edge verður tennt þegar nearest-fill nær út að silhouette;
- hárbrún og andlitsdetail ná ekki gæðum fyrri HRN native rendera.

### B0 — direct HRN native face/head checkpoint

- Nota HRN OBJ beint, ekki rastera andlitið yfir í almennt depth-map.
- Varpa native HRN mesh í exact source camera með varðveittri SIFT/RANSAC affine-skráningu.
- Klippa í source-facing sýnilegan front patch; engin 360° bakhlið í loka-2.5D.
- Rendera neutral front/30°/profile áður en bolur eða strekking er tengd.

### B1 — HRN direct face patch + MoGe body only

- Fjarlægja head/face region úr body heightfield.
- Tengja direct HRN front patch við háls/jakka með mjóu, mælanlegu transition-bandi neðan við höku.
- MoGe ownership-map verður svart/0 yfir öllu höfði og andliti.
- Engin fillet/smoothing yfir HRN vertices.

### B2 — ECON/ICON samanburður fyrir höfuð

ECON og önnur `*CON` líkön eru fyrst A/B-samanburður, ekki sjálfkrafa replacement:

- taka aðeins front/head region úr frystu ECON/ICON keyrslunni;
- bera neutral geometry saman við direct HRN;
- meta nefbrodd, nefbrú, kinnar, munn, augnsvæði, eyru og head pose;
- velja region per mælanleg gæði, ekki eftir nafni líkans.

Ef ECON coarse form er betra en HRN á einhverju svæði má prófa HRN high-frequency residual ofan á ECON coarse head, en aðeins í sérstöku B3-run.

### B3 — hair/source silhouette án helmet-rim

Prófa eftir að andlitið er samþykkt:

1. open hair boundary, engin strekking;
2. mjög grunn hair-only transition;
3. body-only strekking sem útilokar efri head boundary;
4. source-luma hair microdetail með edge-distance falloff;
5. engin geometry frá ótengdum alpha-components fyrir ofan hárið.

Hár má ekki verða að sérstöku jafndjúpu lagi eða kambvegg.

### B4 — v3.2 sliding-stretch matrix

Þegar B1/B3 front surface er samþykkt er sama strekkingarmatrix og í A2 keyrð, en með region-specific takmörkunum:

- head/hair: open eða shallow-only;
- shoulders/jacket: medium backfill;
- neðri crop edge: dýpri transition leyfileg;
- face interior: alltaf excluded.

## Samþykkisskilyrði

### Geometry

- Nefbroddur er kúptur og fremstur; enginn flatur pallur.
- Andlitsdetail HRN minnkar ekki eftir fusion.
- Engin fake hönd, limur eða completion sem source staðfestir ekki.
- Hárbrún myndar hvorki tenntan vegg né helmet-rim.
- Bolur/fatnaður heldur source-derived lögum.

### QA og rekjanleiki

- Front, 30°, 45° og profile með neutral material.
- B/W source-appearance render merkt með nákvæmum model stack.
- Ownership-map fyrir hvert líkan.
- Vertices, triangles, depth-span og nose-prominence skráð.
- `accepted`, `rejected` eða `informative` staða skráð með ástæðu.

## Röð morgundagsins

1. Frysta v3.0 two-person checkpoint og v3.2 HRN/source-camera checkpoint með hashes.
2. Búa til ownership-map renderer sem sýnir model source per region.
3. Keyra B0 direct HRN front patch og samþykkja/hafna andliti áður en annað er tengt.
4. Keyra B1 með MoGe eingöngu á bol/föt.
5. Keyra einn ECON/ICON head A/B samanburð við nákvæmlega sama camera og QA.
6. Hefja A2 strekkingarmatrix á gömlu hjónunum frá óbreyttu v3.0 front mesh.
7. Flytja bestu strekkingarregluna yfir í B3/B4 með head/hair exclusion.
8. Uppfæra model-router út frá staðfestum, ekki áætluðum, niðurstöðum.
