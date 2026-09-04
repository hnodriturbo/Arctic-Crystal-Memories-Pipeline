<!--
File: .Markdown/README.md
Purpose:
 - Index the local 2.5D model research, reproducible runs, and frozen evidence.
-->

# ACM 2.5D rannsóknarsafn

Þessi mappa er rekjanleg rannsóknardagbók fyrir umbreytinguna:

```text
Ljósmynd
  -> source-aligned dense 2.5D triangular geometry
  -> texture + print/silhouette mask
  -> seinna: refinement og point-cloud/DXF framleiðsla
```

Markmiðið er ekki að búa til óþarfa 360° mannslíkan. Markmiðið er að varðveita ljósmyndina að framan, endurgera trúverðuga dýpt í manneskjum og umhverfi og skila þéttum 2.5D fleti sem má vinna áfram fyrir kristal.

Í verkefissamtölum og rannsóknarskjölum merkir „3D“ sjálfgefið **source-facing 2.5D** þar til annað er tekið sérstaklega fram.

## Staðfest baseline og ICON samanburður

Fyrsta sterka baseline-ið er [ECON front-only keyrslan](runs/2026-08-31-econ-front-only-both-together/README.md). Hún notar PIXIE + SMPL-X, ECON normals og d-BiNI front-surface integration. Hún býr til þekkjanleg andlit, hálsa, líkama, fatnað og hendur án HRN, MoGe-2 eða ACM Composer. [PARE](models/PARE/README.md) verður prófað sem occlusion-aware samanburðar-HPS við PIXIE.

[Official ICON + PIXIE keyrslan](runs/2026-09-01-icon-official-pixie-both-together/README.md) staðfestir að ICON front normals eru sterk, en 256³ closed full-3D mesh missir of mikið detail fyrir loka-2.5D. ICON er því varðveitt sem normal/anatomy prior og direct PARE-vs-PIXIE rannsóknarleið; ECON front-only helst aðal geometry baseline.

[ICON raw-normal → adaptive-fillet d-BiNI keyrslan](runs/2026-09-01-icon-front-bni-pixie-both-together/README.md) staðfestir að lossless ICON front normals geta orðið að samfelldum source-facing 2.5D fleti án implicit closure.

[Controlled PARE-vs-PIXIE keyrslan](runs/2026-09-01-icon-front-bni-pare-both-together/README.md) velur PARE sem structural body/posture grunn fyrir þessa occluded sitjandi mynd. PIXIE er áfram skarpari detail-samanburður; næsta geometry-skref er source-camera fusion, ekki fleiri óstýrð full-3D closure-próf.

[Samþykkta source-camera runnið](runs/2026-09-02-source-camera-pare-both-together/README.md)
varpar PARE-flötunum aftur í exact 1086×1177 source camera með 0,18 px miðgildisvillu.
[Exact-source MoGe runnið](runs/2026-09-02-moge-exact-source-both-together/README.md)
gefur scene-depth fyrir restina af myndinni. [Scene-fusion og fyrstu depth-skirt
tilraunirnar](runs/2026-09-02-scene-fusion-and-depth-skirts/README.md) varðveita
náttúrulega arm-opnunina og sýna næsta óleysta back-edge join skref í gallery.

## Uppbygging

- `models/`: rannsóknarsíða fyrir hvert líkan og skýrt hlutverk þess.
- `runs/`: óbreytanlegar keyrslufærslur með stillingum, artifacts, villum og kóðaafritum.
- `methodology/`: sameiginleg aðferðafræði, AC3D-samanburður og fyrirhugaður samruni líkana.

Fast hugtakasafn er í [GLOSSARY.md](methodology/GLOSSARY.md). „Strekking“ merkir sérstaklega útlínustrekkingu: geometry sem er teygð aftur í dýpt frá silhouette-mörkum.

[Vinnudýptarrými og crystal-scaling](methodology/DEPTH-SPACE-AND-CRYSTAL-SCALING.md) skilgreinir framsvigrúm fyrir nef/hendur, baksvigrúm fyrir scene/strekkingu og þá reglu að lokastærð kristals sé sett á eftir reconstruction.

[Hybrid-glide aðferðin](methodology/HYBRID-GLIDE-TRANSITION.md) skilgreinir næsta
v6-próf: samþykkt v3-framhlið helst fryst, multi-ring v5 vinnur aðeins
silhouette-transition og 0,01 mm er mælanleg tolerance en ekki 90° extrusion.

[Windows desktop áætlunin](methodology/WINDOWS-DESKTOP-APPLICATION.md) lýsir
fyrsta installable ACM Crystal Studio og
[`.acmcrystal` sniðið](methodology/ACMCRYSTAL-PROJECT-FORMAT.md) skilgreinir
opið ACM-eigið project-container með JSON, GLB og PNG.

[Model router og source-evidence](methodology/MODEL-ROUTER-AND-EVIDENCE.md)
skráir fyrir hverja ein-manneskju mynd hvað sést, hvaða model stack var valið,
hvaða profile var hafnað og hvort valið reyndist rétt eftir neutral QA.

[SMPL-X evaluation plan](methodology/SMPL-X-EVALUATION-PLAN.md) staðfestir hvaða
SMPL-X assets eru þegar í notkun og raðar locked-head, v1.1, Blender 10/300-shape,
SMPLify-X og Unity samanburðunum í afmarkaðar local rannsóknarkeyrslur.

[Eyeglasses geometry research](models/EYEGLASSES/README.md) skilgreinir sérstakt
gleraugnalag með maska, landmarks, symmetric frame-template og HRN depth-anchor,
í stað þess að gleraugun séu máluð inn í andlitsflötinn.

[Staðfesta AC3D/Cockpit `amma` viðmiðið](runs/2026-09-04-ac3d-cockpit-amma-reference/README.md)
endurbyggir standard GLB úr innbyggðu `.ci` triangle-mesh-i, aðgreinir 198.063
triangle master frá 4.435.041 punkta DXF og ber reference saman við frozen v3.1
endurkeyrslu. [AC3D-líka portrait planið](methodology/AC3D-LIKE-PORTRAIT-PIPELINE-PLAN.md)
breytir mælingunum í okkar eigin region-based reconstruction, gleraugnalag,
local backfill, oversized master og crystal-trim flæði.

[ACM Crystal Studio Windows + Blender planið](plans/2026-09-04-ACM-CRYSTAL-STUDIO-BLENDER-PLAN.md)
skiptir fyrsta installable forritinu í vertical slice, Blender bridge,
crystal/laser toolchain og installer/recovery áfanga.

[Local workbench v2 + `amma-2`](runs/2026-09-02-local-2.5d-workbench-v2/README.md)
staðfestir fjögurra skrefa flæðið, BiRefNet portrait background removal og
fyrstu full-size CUDA-keyrsluna án kristalforms.

[`amma-2` 10/20 mm + sjálfkeyrt samþykkt v3](runs/2026-09-02-amma-2-deep-and-approved-v3/README.md)
gerir PARE→ICON→ECON→MoGe→depth-skirt v3 að keyranlegu profile-i fyrir nýjar
myndir og varðveitir gamla tveggja-manneskju artifactið sem óbreytt viðmið.

[Close-portrait HRN + MoGe-2 v3.1](runs/2026-09-02-portrait-hrn-moge-v31/README.md)
staðfestir að PARE full-body prior er rangt routing fyrir nærmynd. HRN endurgerir
höfuð/andlit, MoGe varðveitir raunverulegan jakka og bounded multi-ring
útlínustrekking klárar ytri brún án fake handa. V3.1 portrait-outputið var síðar
hafnað vegna tapaðs face-detail og rangrar hair-rim geometry.

[Portrait v3.2-a head-lock](runs/2026-09-02-portrait-v32-head-lock/README.md)
staðfestir að MoGe og generic smoothing geti verið 100% útilokað frá höfði/andliti.
Heightfield-afbrigðinu var samt hafnað; næsta skref er direct HRN native front patch.

[V3.0/v3.2 tilraunaáætlunin fyrir 2026-09-03](plans/2026-09-03-V30-V32-EXPERIMENT-PLAN.md)
frystir gömlu hjónin sem v3.0 two-person baseline og skilgreinir controlled
sliding-stretch matrix ásamt direct-head v3.2 portrait-rannsókn.

[SMPL-X + HRN + hair + deeper portrait prófið fyrir 2026-09-04](plans/2026-09-04-SMPL-X-HRN-HAIR-DEPTH-EXPERIMENT.md)
hækkar höfuðdýpt í 0,60, frystir bolinn við 0,26, bætir við +0,12 feathered
shoulder-only boost og skilgreinir controlled SMPL-X neck,
locked-head, Blender 10/300-shape og source-derived watertight hair-shell run.

[Portrait v3.3 direct HRN + original-source MoGe](runs/2026-09-03-portrait-v33-direct-hrn-original-moge/README.md)
aðskilur BiRefNet semantic maska frá raunverulegri dýpt, keyrir MoGe á opaque
2K source og normaliserar aðeins innan manneskjunnar. Native HRN closed-head +
MoGe body með aukinni 0,60 höfuðdýpt, staðbundnum öxlum og frame-cut
bakfyllingu er nú kandidat; háls–fatasaumur, hár og gleraugu þurfa enn sérlög áður en profile
má verða samþykkt preset.

[`amma-2` v3.0 rewind og v3.1–v3.3 samanburður](runs/2026-09-04-amma2-v30-rewind-comparison/README.md)
staðfestir að v3.0 var fyrsta fullkláraða candidate-ferlið en er ekki betra
portrait-output á erfiðu gleraugnamyndinni. Það varðveitir skarpara local relief,
en PARE full-body routing og óbundin silhouette-strekking mynda rangt form og
lárétta profile-gadda. Næsta leið heldur native HRN head volume úr v3.3 og fær
sér source-aligned gleraugnalag með staðbundinni backfill/strekkingu.

## Reglur um baseline

1. Hrátt model-output er aldrei skrifað yfir.
2. Refinement fær nýja run-möppu og vísar í parent-baseline.
3. Model stack, input-hash, config og artifact-hash fylgja hverri niðurstöðu.
4. QA-render má ekki vera kynnt sem geometry-breyting; lýsing, efni og camera placement eru skráð sérstaklega.
5. Research-only leyfi eru ekki sjálfkrafa heimild til commercial production. Leyfisstaða er staðfest áður en líkan verður hluti af framleiðslu.

## Næsta lota

Næstu aðskildu tilraunir eru:

1. Refinement á outer back-edge join fyrir silhouette depth skirt án þess að loka raunverulegum occlusion-bilum.
2. HRN-to-SMPL-X bounded neck stitch með locked-head og v1.1 A/B samanburði.
3. Region-based PIXIE/HRN detail refinement fyrir andlit, hár, gleraugu og hendur.
4. Confidence-weighted transition milli human normals og MoGe scene normals.
5. Crystal scaling og mesh-budget eftir að geometry hefur verið samþykkt.

ECON- og ICON-baseline eru ekki yfirskrifuð; hver viðbót fær nýja run-möppu. Sjá [pipeline-áætlun](methodology/PIPELINE-ARCHITECTURE.md).
