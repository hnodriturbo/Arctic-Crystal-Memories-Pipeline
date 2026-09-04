<!--
File: .Markdown/plans/2026-09-05-V35-SINGLE-SURFACE-PORTRAIT-WARP.md
Purpose:
 - Define the controlled v3.5 single-surface portrait experiment for 2026-09-05.
 - Preserve the decisions made after comparing v3.4 with the AC3D/Cockpit reference.
-->

# 2026-09-05 — v3.5 single-surface portrait warp

Status: **READY FOR LOCAL RESEARCH**

## Markmið morgundagsins

Byggja og prófa nýjan portrait-grunn sem líkir eftir því sem sést í AC3D-
viðmiðunum: eitt klippt, source-aligned 2.5D-yfirborð sem hallar frá búk aftur að
höfði og mótar aðeins það sem sést á myndinni.

V3.5 á ekki að búa til fullt 3D-höfuð, sérstaka hárskel eða ósýnilega líffærafræði.
Framhlið ljósmyndarinnar, skuggamyndin og stýrð hliðarsýn hafa forgang.

## Ákvörðun sem er fryst

Eftir samanburð á MeshLab-hliðarsýn v3.4 og Cockpit3D-hliðarsýn er eftirfarandi
grunnstefna samþykkt fyrir v3.5:

1. HRN closed-head er fjarlægt úr loka-geometry.
2. `SOURCE_HAIR_SHALLOW_PULLBACK`-hárskelin er ekki notuð.
3. Sérstakt parametric gleraugnamesh er ekki sjálfgefið lokaform.
4. Manneskjan verður eitt foreground-klippt triangle-yfirborð.
5. Lág-tíðni halli setur neðri búk framar en höfuð og hár.
6. Nef, varir, kinnar, haka og önnur sýnileg form fá staðbundið depth ofan á
   hallann.
7. Hár er hluti af sama myndfleti og fylgir source-silhouette.
8. Gleraugu verða síðar prófuð sem local forward warp á sama yfirborði með
   mjóu stretch/fill transition-svæði.
9. Svört/óviss jaðarsvæði mynda ekki stórar hliðarplötur eða tilbúið bakhöfuð.

V3.4 er varðveitt óbreytt sem research-candidate og A/B-viðmið. Það er ekki
yfirskrifað.

## Af hverju v3.4 er ekki grunnurinn

V3.4 bætti staðsetningu og aðgreiningu gleraugna og hélt heildardýpt nálægt AC3D,
en hliðarsýnin sýnir þrjú kerfisbundin vandamál:

- portrettflöturinn er nánast lóðréttur í stað þess að hallast aftur upp eftir
  manneskjunni;
- HRN býr til heilt, facettað höfuð sem ljósmyndin og 2.5D-notkunin þurfa ekki;
- sérstök hárskel og HRN–MoGe mörk búa til óeðlilegt hár-profile og háls-/kjálkasaum.

Þetta verður ekki leyst með meiri smoothing eða minni hárdýpt. Skipta þarf um
grunnframsetningu geometry.

## Nákvæm local viðmið

### Fyrsta control — `dad-fish`

- `reference-gallery/cockpit-files/dad-fish.cockpit`
- `reference-gallery/cockpit-files/dad-fish-2.cockpit`

Báðar skrár innihalda sömu upprunamynd en mismunandi AC3D `.ci` mesh. Þetta er
sterkasta control-parið því það einangrar endurtekningarhegðun AC3D án hárs og
gleraugna:

- ein manneskja;
- skýr foreground-silhouette;
- skýrt andlit og eyra;
- hendur og fiskur prófa depth ordering;
- engin hár- eða gleraugnaregla getur falið grunnskekkju í hallanum.

### Annað control — `amma-1`

- Source: `input-testers/amma-og-afi/amma-1.jpeg`
- AC3D-viðmið: `reference-gallery/cockpit-files/amma-4-september.cockpit`
- V3.4 control:
  `output/research/2026-09-04-portrait-v34-controls/amma-1/07-v34-smooth/`

Þessi mynd prófar reglulegt hár, gleraugu, andlit, háls og búk eftir að
single-surface grunnurinn hefur staðist `dad-fish`.

### Stress-próf — aðeins ef control-prófin standast

- Source: `input-testers/amma-og-afi/amma-2.jpeg`
- AC3D-viðmið: `reference-gallery/cockpit-files/amma.cockpit`
- V3.4 stress-output:
  `output/research/2026-09-04-portrait-v34-controls/amma-2/03-v34-smooth/`

`amma-2` er ekki fyrsta þróunarmyndin. Hún er þröng nærmynd með gleraugum,
flóknu hvítu hári og litlu svigrúmi við silhouette og er því notuð síðast.

## Vinnuröð

### 1. Varðveita núverandi stöðu

- staðfesta `git status` áður en breytingar hefjast;
- ekki breyta eða yfirskrifa v3.3/v3.4 run-möppur;
- nýr kóði, prófanir og output fá `v35`/`portrait-v35` nöfn;
- engin GitHub push nema notandinn biðji sérstaklega um það.

### 2. Endurbyggja bæði `dad-fish` AC3D-meshin

Nota núverandi local interoperability-tól:

- `code/research/extract_cockpit_ci_mesh.ps1`
- `code/research/build_glb_from_cockpit.py`

Hvort `.cockpit` viðmið fær sína eigin óbreytanlegu output-möppu. Original
Cockpit-skrárnar eru aðeins lesnar.

### 3. Mæla AC3D-grunnformið

Fyrir bæði `dad-fish` mesh skal skrá:

- vertex- og triangle-fjölda;
- physical width, height og depth;
- depth/height og depth/width hlutföll;
- low-frequency halla `z` eftir normaliseruðu `y`;
- robust median/quantile cross-sections við höfuð, axlir, búk, hendur og fisk;
- hversu stór hluti total depth kemur frá heildarhalla og hversu stór hluti frá
  local relief;
- connected components, boundary edges og óeðlilega gadda;
- breidd og dýpt silhouette support/backfill þar sem það sést.

Ekki giska á hallagráður eða millimetra áður en þessar mælingar liggja fyrir.

### 4. Útfæra v3.5 single-surface grunn

Fyrsta útgáfa notar eina triangulated foreground-grid/surface:

```text
foreground mask
  -> klippt source-aligned grid
  -> mældur AC3D-líkur base tilt
  -> low-frequency scene/person depth
  -> bounded local feature relief
  -> narrow silhouette transition
  -> eitt textured GLB-yfirborð
```

Fyrir hvern foreground-vertex verður lokadýpt hugsuð sem:

```text
z_final = z_base_tilt
        + z_low_frequency
        + z_local_visible_features
        + z_bounded_transition
```

Skilmálar:

- `z_base_tilt` fæst úr mælingu AC3D-viðmiðanna;
- MoGe má leggja til low-frequency ordering en ræður ekki silhouette eða
  óbundinni heildardýpt;
- face landmarks mega skilgreina svæði og anchors;
- HRN má aðeins vera ósýnilegt weak depth-prior í A/B-rannsókn, aldrei closed
  exported head;
- source-luma má aðeins leggja til mjög vægt detail innan confidence-maska;
- jaðarfylling verður mjó, bounded og mæld miðað við AC3D.

### 5. Keyra stýrða `dad-fish` A/B-röð

| Afbrigði | Innihald | Tilgangur |
| --- | --- | --- |
| A | Mask + tilt | Staðfesta grunnstöðu yfirborðsins |
| B | A + low-frequency depth | Staðfesta mann/fisk/handa ordering |
| C | B + bounded face/detail | Staðfesta andlit án fulls höfuðs |
| D | C + narrow silhouette transition | Lokakandidat gegn AC3D |

Hvert afbrigði fær front, 30°, 45°, vinstri profile og hægri profile QA. Sama
orthographic camera, world orientation og overall height verða notuð fyrir ACM
og AC3D samanburð.

### 6. Flytja samþykktan grunn yfir á `amma-1`

Ekki bæta hár- eða gleraugnareglum við fyrr en `dad-fish` D hefur staðist.

Á `amma-1`:

- hármaski breytir depth innan sama yfirborðs en býr ekki til nýjan object;
- silhouette fylgir ysta trausta source-hármarki;
- eyru eru aðeins mótuð þar sem source sýnir þau;
- gleraugnarammi er local positive depth-offset á sama surface;
- face-under-lens heldur eðlilegu relief;
- mjór edge-aware transition teygir source-pixla frá ramma aftur að andliti;
- engin sérstök `EYEGLASSES_FRAME` eða `HAIR_SHELL` scene-node er í v3.5
  kandidatnum.

### 7. `amma-2` sem valfrjálst lokapróf

Keyra aðeins ef `dad-fish` og `amma-1` standast acceptance-skilyrðin. Ef annað
control-prófið bregst er orsökin lagfærð þar fyrst; ekki fela grunnvandamál með
sérstillingum fyrir erfiðustu myndina.

## Acceptance-skilyrði

### `dad-fish`

- eitt aðal source-aligned foreground-yfirborð;
- ekkert closed generic head eða ósýnilegt bakhöfuð;
- neðri búkur er framar en höfuð í profile samkvæmt AC3D-hallanum;
- total depth og low-frequency halli eru innan skráðrar, mælanlegrar tolerance
  frá báðum AC3D-viðmiðum;
- andlit er þekkjanlegt að framan án lóðrétts „face-on-wall“ forms;
- fiskur, hendur og búkur hafa rétta innbyrðis röð;
- engir langir profile-gaddar, sjálfsskurðir eða stórar svartar hliðarplötur.

### `amma-1`

- engin hárskel eða facettað fullt höfuð;
- hárið les sem hluti af manneskjunni í front, 30° og profile;
- búkur/höfuð halli líkist AC3D frekar en lóðréttu v3.4-hliðinni;
- enginn HRN–MoGe kjálka-/háls-saumur;
- gleraugu standa vægt framar en andlit en tengjast því með mjóu, sléttu
  stretch/fill-svæði;
- framhlið, nef, varir og kinnar halda source-likeness;
- silhouette er þétt klippt og stór svört side-region myndast ekki.

## Reject/stop-skilyrði

Afbrigði er hafnað strax ef:

- það endurskapar fullt höfuð eða sérstakt hair volume;
- aukin dýpt gerir portrettið að lóðréttum vegg með haus framan á;
- silhouette-fylling verður að breiðri blokk;
- gleraugu verða frístandandi þykk geometry í stað vægrar source-strekkingar;
- front-likeness versnar til að bæta profile;
- sérregla fyrir eina mynd er nauðsynleg áður en control-prófið er skilið.

## Fyrirhuguð skjöl og artifacts

Ný run-mappa:

```text
.Markdown/runs/2026-09-05-portrait-v35-single-surface/
  README.md
  ARTIFACTS.md
  artifacts/gallery/
```

Ný research-output mappa:

```text
output/research/2026-09-05-portrait-v35-single-surface/
  ac3d-dad-fish-1/
  ac3d-dad-fish-2/
  dad-fish/
  amma-1/
  amma-2/          # aðeins ef control-prófin standast
```

Skjalfesta þarf nákvæm input-hash, stillingar, geometry-mælingar, QA-camera og
ástæðu fyrir samþykki eða höfnun hvers afbrigðis.

## Definition of done fyrir morgundaginn

Morgundagslotan telst fullkláruð þegar:

1. bæði `dad-fish` AC3D-mesh hafa verið endurbyggð og mæld;
2. v3.5 single-surface kóði og einingapróf eru til;
3. `dad-fish` hefur reproducible A–D samanburð og neutral QA;
4. samþykktur grunnur hefur verið keyrður á `amma-1`;
5. AC3D, v3.4 og v3.5 profile/front samanburður er í gallery;
6. niðurstaða er merkt `ACCEPTED`, `RESEARCH CANDIDATE` eða `REJECTED` með
   mælanlegri ástæðu;
7. öll staðbundin próf standast og `git diff --check` er hreint;
8. engin GitHub push hefur átt sér stað án nýrrar skýrrar beiðni notandans.
