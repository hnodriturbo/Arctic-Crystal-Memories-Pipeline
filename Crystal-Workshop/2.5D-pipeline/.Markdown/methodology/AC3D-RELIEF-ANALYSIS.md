<!--
File: .Markdown/methodology/AC3D-RELIEF-ANALYSIS.md
Purpose:
 - Record visual observations from the user's AC3D reference without claiming proprietary implementation details as fact.
-->

# AC3D sjónræn viðmiðun

## Það sem sést á viðmiðuninni

Front-view sýnir mjög nákvæma source texture og sannfærandi sýnilega dýpt. Skámyndirnar sýna hins vegar að bakhlið manneskjunnar er ekki full 360° endurgerð. Við silhouette myndast langar, mjóar rendur eða fleygar sem ganga aftur í flatari/baklægari flöt. Í verkefninu köllum við þetta **útlínustrekkingu**, stytt í **strekkingu**. Ensk tæknileg heiti eru **silhouette depth skirt** og **silhouette backfill**.

Þetta styður vinnutilgátuna að kerfið varðveiti sterkan front-facing 2.5D flöt og extrude-i boundary vertices/triangles aftur í dýpt sem depth skirt til að loka eða tengja hann fyrir kristalvinnslu. Þetta er sjónræn ályktun úr outputi, ekki staðfest þekking á proprietary AC3D-kóða.

## Samanburður við ECON baseline

Sameiginlegt:

- dýptin þarf ekki að vera fullkomin 360° til að virka vel í kristal;
- andlit, fatnaður og hendur eru fyrst og fremst metin frá source-facing sjónarhorni;
- bakhlið getur verið completion/backfill fremur en ljósmyndafræðilega staðfest anatomy.

Munurinn sem enn þarf að leysa:

- ECON-baseline varðveitir eðlileg occlusion-bil milli handleggs/handar og bols. Það eru aðeins örfínar óæskilegar seam-línur/mask-göt á sumum mörkum sem þarf að greina og laga;
- AC3D tengir silhouette aftur á bak með reglulegum depth skirt;
- hár, gleraugu og mjög fín andlitsatriði þurfa sérhæfðara model eða refinement ofan á ECON;
- source-aligned sameining fólks og sófa er ekki lokið í okkar fyrstu QA-senu.

## Varðveittar myndir

- [AC3D skáviðmiðun](../runs/2026-08-31-econ-front-only-both-together/references/ac3d-reference-45deg.png)
- [AC3D edge/backfill nærmynd](../runs/2026-08-31-econ-front-only-both-together/references/ac3d-streak-detail.png)
- [ECON: eðlileg occlusion-bil og örfín seam-lína](../runs/2026-08-31-econ-front-only-both-together/references/econ-occlusion-vs-fine-seams.png)
- [AC3D silhouette depth skirt](../runs/2026-08-31-econ-front-only-both-together/references/ac3d-silhouette-depth-skirt.png)
- [AC3D preview með fram- og baksvigrúmi](../runs/2026-08-31-econ-front-only-both-together/references/ac3d-working-depth-volume.png)

## Vinnudýptarrými

Nýja preview-viðmiðunin sýnir processed 2.5D flöt inni í stærra preview-volume með lausu rými fyrir framan og aftan. Þetta styður að dýptarsköpun fari fram áður en geometry er fitted í endanlega kristalstærð. Fremsti punktur, til dæmis nef, fær því framsvigrúm í stað þess að vera clamped við fremri ramma. Sjá [nákvæma scaling-reglu](DEPTH-SPACE-AND-CRYSTAL-SCALING.md).

## Staðfest með `amma.cockpit` 2026-09-04

Nýja reference-skráin gerir okkur kleift að aðgreina staðreyndir frá eldri
sjónrænum tilgátum:

- `.cockpit` er ZIP-container með XML, triangle `.ci`, JPEG texture og PNG maska;
- `.ci` surface hefur 99.614 vertices og 198.063 triangles;
- scene-space stærðin er 67,304 × 127,528 × 28,901 mm;
- 4.435.041 í DXF eru `POINT` entities, ekki triangle-count;
- 120 mm kristall inniheldur surface sem er 127,528 mm hátt fyrir trim;
- black texture/mask svæði merkir óprentað svæði þótt samfelld geometry sé til;
- höfuðið notar mikla convex dýpt en framhlið flíkur er mun þynnri;
- gleraugu og local backfill eru hluti af sama surface, ekki fullkomið
  sjálfstætt eyewear-módel.

Við vitum enn ekki hvaða dýptarnet, morphable model eða manual edit-skref var
notað til að búa til upprunalega `.ci`. Sú framkvæmd er því áfram tilgáta. Sjá
[eigin evidence-led portrait plan](AC3D-LIKE-PORTRAIT-PIPELINE-PLAN.md) og
[nákvæmu run-færsluna](../runs/2026-09-04-ac3d-cockpit-amma-reference/README.md).
