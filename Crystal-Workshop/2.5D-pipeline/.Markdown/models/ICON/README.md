<!--
File: .Markdown/models/ICON/README.md
Purpose:
 - Record ICON's validated behavior and its role in the ACM source-aligned 2.5D pipeline.
-->

# ICON — Implicit Clothed humans Obtained from Normals

## Hlutverk hjá ACM

ICON notar human pose/shape prior, spáir front/back normals fyrir klædda manneskju og byggir lokað implicit 3D-mannslíkan. Það er sterkt whole-human rannsóknarlíkan, en lokað 360° output er ekki sjálfkrafa besta 2.5D-outputið fyrir kristal.

Staðfesta local keyrslan sýnir rétta hlutverkaskiptingu:

```text
PIXIE + SMPL-X
  -> pose, camera, body/head/hand prior
  -> ICON front/back clothed-human normals
  -> implicit occupancy + marching cubes
  -> closed full-3D human
```

Fyrir okkar pipeline er verðmætasta efnið líklega **front normal + source-facing surface fyrir implicit closure**. Full-3D möskvinn er gagnlegur sem anatomy/depth prior og samanburður, en ekki lokaoutput.

## Staðfest local próf

- Opinber ICON source keyrir á Windows og RTX 3060 Laptop GPU 6 GB.
- PIXIE/SMPL-X leiðin endurgerir báða sitjandi einstaklingana aðskilið.
- Predicted front normals varðveita fellingar, líkamsstöðu, háls, hendur og coarse andlit mjög vel.
- Hrái 256³ `*_recon.obj` er lokaður, watertight og um 210k–230k triangles á mann.
- Full-3D marching-cubes möskvinn missir sýnilega meiri identity/fatnaðardetail en predicted front normal-kortið og sýnir lárétta voxel/ring artifacta.
- Hár og gleraugu eru ekki trygg geometry.

Staðfest run: [2026-09-01 official ICON + PIXIE](../../runs/2026-09-01-icon-official-pixie-both-together/README.md).

## ICON samanborið við ECON front-only

| Eiginleiki | ICON full 3D | ECON front-only |
|---|---|---|
| Human prior | PIXIE/SMPL-X eða PARE/SMPL | PIXIE/SMPL-X í frysta runinu |
| Front/back normals | já | já |
| Lokaoutput | lokað implicit 3D | opinn source-facing d-BiNI front-flötur |
| Óstaðfest bakhlið | búin til | sleppt |
| Immediate 2.5D gæði | of slétt við 256³ | sterkari baseline |
| Best notkun hjá ACM | normal/anatomy prior og rannsókn | núverandi aðal front-surface baseline |

## Upplausn og mesh-budget

`configs/icon-filter.yaml` segir nominalt `mcube_res: 512`, en opinbera `apps/infer.py` override-ar inference í `mcube_res=256`. Því er staðfesta outputið ekki 512³ demo-gæði.

Samtals gáfu tveir hráir möskvar 220.269 vertices og 440.630 triangles, innan núverandi 250k–1M triangle rannsóknarsvæðis þegar fólkið er metið saman. Upplausn verður aðeins hækkuð í nýju runni; frysta 256³ baseline-inu verður ekki breytt.

## PARE og multi-person

Opinbera ICON `TestDataset` styður `hps_type: pare` beint, auk `pixie`, `pymaf`, `hybrik` og `bev`. PARE er því næsti hreini A/B samanburður innan ICON.

ICON velur aðeins hæst skoraða person detection úr hverri inntaksmynd. Tveggja manna mynd þarf því deterministic person canvases eða upstream multi-person adapter, og mesh-in þarf síðar að varpa aftur í sameiginlega source camera.

## Næsta 2.5D skref

1. Vista hrátt `normal_F` tensor án texta/QA-grid.
2. Samþætta það í source-facing front-flöt með d-BiNI eða sambærilegri normal integration.
3. Nota full-3D ICON aðeins sem depth/anatomy regularizer.
4. Varpa báðum person surfaces aftur í upprunalegu myndavélina.
5. Bæta non-human scene depth og útlínustrekkingu við í aðskildu runni.
6. Meta PARE gegn PIXIE og aðeins síðan prófa 384³/512³ implicit reconstruction.

## Leyfi

ICON/PIXIE/SMPL-X assets eru notuð í local rannsókn samkvæmt skráðum aðgangi. Commercial notkun krefst sérstakrar leyfisstaðfestingar áður en þessi research stack fer í framleiðsluforrit.
