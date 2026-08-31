<!--
File: .Markdown/methodology/PIPELINE-ARCHITECTURE.md
Purpose:
 - Define the intended source-aligned multi-model 2.5D pipeline and evaluation order.
-->

# Fyrirhuguð 2.5D pipeline

## Hlutverkaskipting

```text
Upprunaleg ljósmynd
        |
        +-- PIXIE eða PARE + SMPL-X HPS
        |     pose, camera og body/head/hand prior
        |
        +-- ECON front surface
        |     normals + d-BiNI fyrir líkama, fatnað, háls, axlir, hendur og coarse höfuð
        |
        +-- HRN per face
        |     sýnilegt andlit, eyru, enni og nákvæmara höfuðform
        |
        +-- almennt depth model / MoGe-2
        |     sófi, bakgrunnur og annað sem er ekki manneskja
        |
        +-- source texture + segmentation/silhouette mask
        |
        v
Allt varpað í upprunalegu myndavélina
        |
        v
Dense source-aligned 2.5D triangular geometry
```

## Það sem ECON-baseline staðfestir

ECON getur eitt og sér gefið mjög nytsamlegan front-facing mannflöt. Fyrir kristalþörfina er rétt að stöðva ferlið eftir d-BiNI front-surface og áður en IF-Net/Poisson lokar yfir í 360° volume. Það minnkar óstaðfesta bakhlið, heldur source detail og takmarkar skráarstærð.

Fyrsta baseline notaði PIXIE. PARE verður prófað sem occlusion-aware HPS þar sem part-guided attention getur bætt pose/body-shape mat fyrir skarandi hendur, handleggi og bol. Attention masks PARE eru innri feature-vægi, ekki print-mask.

## Það sem á ekki að blanda saman

- HRN-render er ekki sjálfkrafa source-aligned face patch; pose, projection og seam blending þarf að vera mælanlegt skref.
- MoGe/almennt depth á ekki að ýta manninum úr ECON-forminu. Það fyllir fyrst non-human svæði og gefur global depth anchor.
- Blender-QA placement í fyrstu ECON-senunni er aðeins sjónræn vinstri/hægri uppröðun, ekki endanleg camera calibration.
- Texture-detail má ekki fela lélega geometry. Mat fer fram bæði með hlutlausu efni og source texture.
- Reconstruction á ekki að clamp-a beint í lokastærð kristals. Halda þarf [vinnudýptarrými með fram- og baksvigrúmi](DEPTH-SPACE-AND-CRYSTAL-SCALING.md) þar til fusion og strekking eru lokið.

## Næsta tilraun: almenn dýpkun á varðveittri senu

1. Frysta ECON OBJ, GLB og `.blend` með checksum.
2. Reikna eitt depth output í einu úr sömu input-mynd.
3. Festa depth við source camera og normalize-a með robust percentile, ekki min/max út frá einum outlier.
4. Nota ECON sem human-prior og almennt depth sem global/non-human prior.
5. Meta aðskilið:
   - andlit og nef;
   - háls, axlir og föt;
   - hendur;
   - sófa og bakgrunn;
   - eðlileg occlusion-bil á móti óæskilegum örfínum seam-línum/mask-götum;
   - þríhyrningafjölda og skráarstærð innan crystal-template marka.
6. Vista hvert afbrigði í nýrri run-möppu; ekkert skrifar yfir baseline.

## Refinement-röð

1. Source camera alignment og multi-person placement.
2. Segmentation/mask repair á aðeins óæskilegum örfínum seam-línum við mörk; varðveita raunveruleg bil milli handleggs, handar og bols.
3. General-depth fusion fyrir sófa og bakgrunn.
4. HRN face patch og seam blending.
5. Silhouette depth skirt/backfill sem tengir boundary aftur í relief án flatra 90° veggja.
6. Crystal-template crop, scale og mesh-budget.
7. Composer aðeins fyrir mælanlega loka-fínstillingu; ekki sem staðgengill fyrir reconstruction.

## HPS-samanburður

Current local ECON `TestDataset` tengir `hps_type` beint við `pixie` eða `pymafx`; PARE er ekki plug-and-play option í þessari branch. PARE-checkpoints og config eru til undir ICON `data/pare_data`, en PARE-vs-PIXIE þarf adapter sem mappar PARE body/camera output í það SMPL-X/camera form sem ECON-leiðin notar. Samanburðurinn verður því varðveitt sjálfstæð rannsókn, ekki config-breyting á frysta baseline-inu.
