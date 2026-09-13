<!--
File: .Markdown/methodology/DEPTH-SPACE-AND-CRYSTAL-SCALING.md
Purpose:
 - Define working depth volume, front/back headroom, and late crystal-template scaling.
-->

# Vinnudýptarrými og crystal-scaling

## Meginregla

Reconstruction á að fara fram í stærra **vinnudýptarrými** með mælanlegu svigrúmi bæði fyrir framan og aftan source-facing flötinn. Geometry er ekki þjappað í endanlega kristalstærð fyrr en ECON, face refinement, scene-depth fusion og útlínustrekking eru lokið.

Þetta kemur í veg fyrir vandamálið sem sást í eldri depth-relief tilraunum: nef eða annar fremsti punktur reynir að færast fram en rekst í fremri mörk geometry-kassans og verður flatur.

## Hugtök

- **Front headroom / framsvigrúm:** laust dýptarrými fyrir nef, enni, hendur og önnur svæði sem þurfa að færast nær áhorfanda.
- **Back headroom / baksvigrúm:** laust rými fyrir líkamsdýpt, sófa, bakgrunn og útlínustrekkingu.
- **Working depth span:** öll virk geometry-dýptin áður en hún er fitted í kristal.
- **Crystal safe volume:** leyfilegt engraving-rými innan kristals eftir öryggismörk.

## Dýptarbil án outlier-clamping

Ekki nota einn min/max pixel til að ákvarða mörk. Notaðu robust percentiles á traustu foreground geometry, til dæmis `p01` og `p99`, og geymdu outlier/silhouette confidence sérstaklega.

Ef camera-depth ásinn `z` vex í átt að áhorfanda:

```text
subject_back  = percentile(z, 1)
subject_front = percentile(z, 99)
subject_span  = subject_front - subject_back

working_back  = subject_back  - back_headroom
working_front = subject_front + front_headroom
```

Headroom á að skalast með subject/crystal depth, ekki vera föst `2.5 mm` eða `0.01 mm` regla:

```text
front_headroom = subject_span * front_ratio
back_headroom  = max(subject_span * back_ratio, strekking_depth)
```

`front_ratio` og `back_ratio` verða tilraunabreytur. Byrjunargildi eru ekki samþykkt fyrr en þau hafa verið prófuð á near-face, full-body, tveimur einstaklingum og mismunandi crystal templates.

## Lokafit í kristal

Eftir að geometry er lokið er eitt uniform scale reiknað svo aspect og dýptarhlutföll haldist:

```text
scale = min(
  available_width  / model_width,
  available_height / model_height,
  available_depth  / working_depth_span
)
```

Síðan er módelið staðsett innan safe volume með sérstöku front- og back-margin. Það er ekki normalize-að þannig að nef verði sjálfkrafa alveg við fremsta engraving-limit.

## Ljós/dökk gildi

Svart/hvítt AC3D-preview er render/shading-vísbending, ekki sönnun þess að grayscale-ljósstyrkur sé raw depth. Í okkar pipeline á physical dýpt að koma frá HPS, normals, d-BiNI og scene-depth fusion. Source brightness/texture má hjálpa fine detail en má ekki eitt og sér ákveða hvort dökkt svæði fari fram eða aftur.

## AC3D-observation

Preview-skjámyndin sýnir sýnilegt laust rými báðum megin við processed 2.5D flötinn áður en hann er settur í endanlegt kristalform. Það styður vinnutilgátuna um reconstruction-volume með depth headroom og seinni fitting. Exact proprietary röð AC3D er þó ekki staðfest.

Viðmiðun: [AC3D working-depth-volume screenshot](../runs/2026-08-31-econ-front-only-both-together/references/ac3d-working-depth-volume.png).
