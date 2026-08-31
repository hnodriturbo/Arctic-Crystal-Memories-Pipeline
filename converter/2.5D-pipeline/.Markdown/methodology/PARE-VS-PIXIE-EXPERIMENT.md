<!--
File: .Markdown/methodology/PARE-VS-PIXIE-EXPERIMENT.md
Purpose:
 - Define a fair, reproducible PARE-versus-PIXIE body-prior experiment for ECON.
-->

# Tilraunaáætlun: PARE vs PIXIE

## Markmið

Finna hvort PARE gefur betra body pose/shape prior en PIXIE þegar hendur, handleggir og bolur skarast, án þess að rugla saman HPS-gæðum og ECON normal/surface-gæðum.

## Control

Frysta ECON-baseline 2026-08-31 er PIXIE-control. Hrá OBJ, config, input og checksum breytast ekki.

## Tæknileg hindrun

Local ECON styður beint `pixie` og `pymafx`, ekki `pare`. PIXIE gefur SMPL-X whole-body/head/hand prior. PARE gefur fyrst og fremst SMPL body/camera estimate. Til sanngjarns samanburðar þarf því:

1. standalone PARE inference á sömu person crops;
2. varðveislu raw PARE output og attention/visibility diagnostics;
3. mapping á global orientation, body pose, betas og camera í sameiginlegt HPS-record;
4. annaðhvort SMPL-to-SMPL-X body mapping eða ECON precomputed-HPS input;
5. hlutlaus face/hand meðferð svo PIXIE fái ekki ósýnilegt forskot í body-only mælingu;
6. aðskilið hybrid-próf þar sem PARE body er sameinað PIXIE/HRN face/hands.

## Mælingar áður en ECON keyrir

- 2D joint reprojection error gegn source-landmarks;
- silhouette overlap/IoU fyrir bol, handleggi og hendur;
- left/right og depth-order consistency við occlusion;
- camera/crop alignment aftur í original image;
- sjónræn villa í öxlum, olnbogum, úlnliðum og bol.

## Mælingar eftir ECON

- continuity í normals og front-surface;
- óæskilegar örfínar seam-línur;
- varðveisla eðlilegra occlusion-bila;
- head/hand alignment við source;
- vertex/triangle count, runtime og peak VRAM;
- neutral-material front, 15°, 30° og 45° QA.

## Samþykkt

PARE tekur ekki sjálfkrafa við af PIXIE. Það er samþykkt sem body-prior eða hybrid aðeins ef mæld source alignment batnar og ECON-flöturinn verður að minnsta kosti jafn góður án þess að face/hands versni.
