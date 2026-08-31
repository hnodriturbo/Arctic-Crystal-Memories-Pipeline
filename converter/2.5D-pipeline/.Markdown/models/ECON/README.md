<!--
File: .Markdown/models/ECON/README.md
Purpose:
 - Record ECON's role, validated behavior, limitations, and local implementation status.
-->

# ECON

## Hlutverk hjá ACM

ECON er nú aðal human front-surface baseline. PIXIE/SMPL-X gefur líkamsprior og camera/pose estimate, ECON spáir front/back normals fyrir klædda manneskju og d-BiNI samþættir normal-kortin í fleti. Fyrir 2.5D kristal stöðvum við eftir front-surface export.

## Staðfest í local prófi

- Multi-person input með tveimur sitjandi einstaklingum virkar.
- Andlit, háls, bolur, föt, handleggir og hendur verða þekkjanleg 2.5D geometry.
- Source-derived vertex colors fylgja OBJ.
- Front-only output er mun nær markmiðinu en eldri generic depth-relief pipeline.
- Tvö person-crop outputs þarf enn að varpa aftur í sameiginlega source camera.

## Takmarkanir

- Eðlileg occlusion-bil sjást milli handleggs/handar og bols og eiga að vera varðveitt. Aðeins örfínar óæskilegar seam-línur eða mask-göt við sum mörk þarf að laga.
- Hár, gleraugu og fín face identity geometry eru ekki nógu trygg.
- PIXIE/SMPL-X er prior, ekki fullkomin staðfest anatomy úr einni mynd.
- Research/commercial leyfisstaða verður að vera staðfest áður en production-notkun hefst.

## Local útgáfa

- ECON source commit: `d8f4e8b7171e30868acd94a1d1f6fcc1238e3e32`
- Windows front-only patch: varðveitt með hverri keyrslu og í `code/research/patches/`.
- Staðfest run: [2026-08-31 ECON front-only](../../runs/2026-08-31-econ-front-only-both-together/README.md).
