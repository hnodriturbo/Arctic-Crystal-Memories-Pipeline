<!--
File: .Markdown/models/PARE/README.md
Purpose:
 - Record PARE's occlusion-aware pose/body-shape role in the ACM research stack.
-->

# PARE — Part Attention REgressor

Heimasíða rannsóknar: [pare.is.tue.mpg.de](https://pare.is.tue.mpg.de/)

## Hvað PARE leysir

PARE er human pose and shape estimator sem er sérstaklega hannaður fyrir partial occlusion. Í stað þess að treysta eingöngu á eina global feature representation lærir það body-part-guided attention masks. Fyrir hvern líkamspart metur það hvaða image features eru gagnleg og getur nýtt upplýsingar frá nálægum pörtum þegar hluti er hulinn.

Þetta er mjög viðeigandi fyrir myndina af hjónunum þar sem hendur og handleggir liggja fyrir framan bol og hlutar líkamans skarast.

## „Sensible attention masks“

Attention-maskarnir eru learned feature-space vægi sem hjálpa pose/shape regression. Þeir eru **ekki** sjálfkrafa exportable foreground-, alpha- eða print-mask og koma ekki í stað silhouette segmentation.

Rétt hlutverk í okkar pipeline:

```text
PARE
  -> occlusion-aware pose/body-shape/camera prior
  -> ECON normals + d-BiNI
  -> detailed front-facing clothed-human surface
```

## Samanburður við PIXIE

Fyrsta ECON-baseline notaði PIXIE + SMPL-X og gaf góða niðurstöðu. PARE á því fyrst að vera samanburðar-HPS, ekki ósannað replacement.

Current local ECON branch styður aðeins `hps_type: pixie` og `hps_type: pymafx` í beinu dataset/inference leiðinni. Official ICON `TestDataset` styður hins vegar `hps_type: pare` beint. PARE-checkpoints eru til í local ICON asset tree:

```text
Models/research/ICON/data/pare_data/pare/checkpoints/
```

Því verður fyrsta hreina PARE-vs-PIXIE prófið keyrt beint í ICON með sömu person canvases og sömu ICON checkpoints. Adapter fyrir body, camera, joints og SMPL/SMPL-X mapping þarf aðeins áður en PARE getur stýrt ECON á jafngildan hátt.

Fyrir sama input berum við saman:

- 2D keypoint reprojection error;
- silhouette overlap við source mask;
- alignment handa, handleggja og axla undir occlusion;
- ECON normal/surface continuity sem fæst frá hvorum prior;
- stability milli crops og multi-person placement.

Ef PARE er betra aðeins á ákveðnum líkamspörtum má nota confidence/visibility til að velja eða blanda priors frekar en að skipta allri pipeline blindandi út.

## Staðfest A/B niðurstaða — 2026-09-01

[Official ICON + PARE front-only runnið](../../runs/2026-09-01-icon-front-bni-pare-both-together/README.md)
notaði sömu person-canvases, ICON normals, 100 fitting iterations og d-BiNI/fillet
stillingar og PIXIE-viðmiðið. PARE lækkaði fitting-loss hjá báðum einstaklingum og
gaf samfelldari body/posture flöt, sérstaklega við skarandi handleggi og bol.

PARE varð því structural HPS-vinningsgrunnur fyrir þetta tilvik. PIXIE varðveitti
meiri staðbundna depth-amplitude og er áfram detail-samanburður. Þetta styður
region-based samruna fremur en að velja eitt prior fyrir öll framtíðarinput.

Nákvæm framkvæmd og samþykktarmælingar eru í [PARE-vs-PIXIE tilraunaáætluninni](../../methodology/PARE-VS-PIXIE-EXPERIMENT.md).

## PARE og PIXIE í einföldu máli

- **PARE:** leggur áherslu á robust líkamsstöðu og líkamslögun þegar líkamspartar hylja hver annan. Part-attention reynir að forðast að lítil occlusion eyðileggi allt pose estimate. Aðal parametric target er líkaminn.
- **PIXIE:** expressive full-body estimator sem vinnur með SMPL-X og sameinar líkama, höfuð/andlit og hendur ásamt pose, shape, expression og camera. Það hentar því beint sem whole-body prior í ECON.
- **ECON:** tekur priorinn og bætir source-derived clothed-human normals og surface integration ofan á. Það er ECON/d-BiNI, ekki PIXIE eða PARE eitt sér, sem skilar detailed front-surface baseline-inu.

## Það sem PARE gerir ekki eitt og sér

- býr ekki til hár eða gleraugu;
- býr ekki til high-frequency andlitsidentity;
- býr ekki eitt og sér til detailed fatnaðarflöt;
- býr ekki til sófa eða almennan scene-depth;
- leysir ekki print/silhouette mask.

## Leyfi

Code og data eru merkt fyrir research use á verkefnissíðunni. Local einkarannsókn heldur áfram samkvæmt þeim aðgangi. Áður en commercial app eða greidd þjónusta notar PARE artifacts verður sérstakt leyfi staðfest og skjalfest; sú framtíðarúttekt stöðvar ekki núverandi löglega rannsókn.
