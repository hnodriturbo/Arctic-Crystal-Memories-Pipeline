<!--
File: Learning/Markdown/3D-Model-Repair-Course/modules/00-safety-and-versioning.md
Purpose:
 - Teach a recoverable, non-destructive editing workflow before Blender operations.
-->

# 00 — Öryggi, afrit og útgáfur

## Af hverju þetta skiptir máli

Handvirk mesh-vinna verður fljótt óafturkræf ef vertices eru eydd, remesh er keyrt eða modifiers eru applied. Baseline-ið er rannsóknargagn og má aldrei verða æfingaskrá.

## Örugg byrjun

1. Opnaðu baseline `.blend`.
2. Veldu `File > Save As` áður en þú breytir nokkru.
3. Vistaðu undir:

```text
converter/2.5D-pipeline/output/learning/<mynd>/<dagsetning>-manual-repair-v001.blend
```

4. Hækkaðu útgáfunúmer fyrir hvert stórt skref: `v002`, `v003`.
5. Ekki vista yfir `both_together_econ_front_qa.blend`.

## Innri afrit í senunni

Áður en geometry er breytt:

1. Veldu object.
2. `Shift+D`, síðan hægrismelltu til að skilja afritið eftir á sama stað.
3. Nefndu original `SOURCE_LOCKED_<nafn>`.
4. Nefndu vinnuafrit `WORKING_<nafn>`.
5. Færðu source í collection `00_SOURCE_DO_NOT_EDIT` og slökktu á selection fyrir collection í Outliner.

## Breytingaskrá

Skráðu fyrir hverja útgáfu:

- hvaða object og svæði var breytt;
- hvaða tool/modifier var notað;
- tölugildi, til dæmis brush radius eða extrusion depth;
- fyrir/eftir screenshot frá front og 45°;
- hvort source silhouette og identity héldust.

## Hvenær á að hætta og fara aftur

Farðu aftur í síðustu útgáfu ef:

- nefið, augnlok eða varir verða mýkri en source;
- hönd festist óeðlilega við bol;
- silhouette fær bungu sem er ekki í ljósmyndinni;
- vertex/face count breytist mikið án skýrrar ástæðu;
- export virkar aðeins í vinnusenunni en ekki eftir re-import.
