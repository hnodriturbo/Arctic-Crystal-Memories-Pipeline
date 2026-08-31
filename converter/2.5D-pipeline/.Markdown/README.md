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

## Staðfest baseline

Fyrsta sterka baseline-ið er [ECON front-only keyrslan](runs/2026-08-31-econ-front-only-both-together/README.md). Hún notar PIXIE + SMPL-X, ECON normals og d-BiNI front-surface integration. Hún býr til þekkjanleg andlit, hálsa, líkama, fatnað og hendur án HRN, MoGe-2 eða ACM Composer. [PARE](models/PARE/README.md) verður prófað sem occlusion-aware samanburðar-HPS við PIXIE.

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

Fyrsta verkefni næstu lotu er að prófa almenn dýptarlíkön á varðveittu ECON-senunni. ECON-baseline sjálft verður ekki breytt; hver viðbót verður mæld og vistuð sem afleidd keyrsla. Sjá [pipeline-áætlun](methodology/PIPELINE-ARCHITECTURE.md).
