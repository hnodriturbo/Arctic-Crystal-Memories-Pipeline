<!--
File: Learning/Markdown/3D-Model-Repair-Course/modules/07-face-hair-ears-hands.md
Purpose:
 - Establish conservative manual-editing rules for high-identity body regions.
-->

# 07 — Andlit, hár, eyru og hendur

## Andlit

Forgangsröð:

1. silhouette höfuðs og kjálka;
2. nefbrú og nefbroddur í side view;
3. enni, kinn og haka;
4. augnlok og varir;
5. high-frequency hrukkur og húðdetail.

Notaðu source ljósmynd og hlutlaust material. Texture getur látið flatan eða rangan flöt líta rétt út.

## Eyru

Eyru eru oft lítil í source og við silhouette, þannig þau eru viðkvæm fyrir mask-loss. Lagaðu fyrst ytri outline með Grab. Innri eyraform skiptir minna máli fyrir front-facing kristal nema það sjáist greinilega í source.

Ekki nota full 360° head completion sem óskeikulan sannleika; HRN/SMPL-X bakhlið er prior.

## Hár

Hár þarf þrjú lög:

- coarse head/hair volume;
- silhouette clumps;
- source texture/high-frequency contrast.

Ekki sculpt-a hvert hár. Varðveittu source silhouette og bættu aðeins við stærri clumps sem skipta máli í side/45°.

## Hendur

Hendur þurfa sérstaka varúð vegna occlusion:

- ekki merge-a fingur sem eru aðskildir í source;
- ekki loka bilinu milli handar og bols sjálfkrafa;
- meta palm/finger depth frá fleiri en einu sjónarhorni;
- nota SMPL-X sem prior, en source image ræður sýnilegri silhouette.

## HRN refinement síðar

HRN face geometry verður sett sem source-aligned patch, ekki sem heilt nýtt höfuð án pose alignment. Blend band verður fyrir utan mikilvægustu identity-svæðin og mælt gegn ECON-frontfletinum.
