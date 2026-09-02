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

## Reglur um baseline

1. Hrátt model-output er aldrei skrifað yfir.
2. Refinement fær nýja run-möppu og vísar í parent-baseline.
3. Model stack, input-hash, config og artifact-hash fylgja hverri niðurstöðu.
4. QA-render má ekki vera kynnt sem geometry-breyting; lýsing, efni og camera placement eru skráð sérstaklega.
5. Research-only leyfi eru ekki sjálfkrafa heimild til commercial production. Leyfisstaða er staðfest áður en líkan verður hluti af framleiðslu.

## Næsta lota

Næstu aðskildu tilraunir eru:

1. Refinement á outer back-edge join fyrir silhouette depth skirt án þess að loka raunverulegum occlusion-bilum.
2. Region-based PIXIE/HRN detail refinement fyrir andlit, hár, gleraugu og hendur.
3. Confidence-weighted transition milli human normals og MoGe scene normals.
4. Crystal scaling og mesh-budget eftir að geometry hefur verið samþykkt.

ECON- og ICON-baseline eru ekki yfirskrifuð; hver viðbót fær nýja run-möppu. Sjá [pipeline-áætlun](methodology/PIPELINE-ARCHITECTURE.md).
