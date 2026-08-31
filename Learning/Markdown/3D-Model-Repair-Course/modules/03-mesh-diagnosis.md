<!--
File: Learning/Markdown/3D-Model-Repair-Course/modules/03-mesh-diagnosis.md
Purpose:
 - Teach diagnosis before editing so valid occlusion geometry is preserved.
-->

# 03 — Greining á mesh og topology

## Flokkaðu vandamálið fyrst

Ekki byrja á tool-i. Merktu svæðið sem einn af þessum flokkum:

1. **Eðlilegt occlusion-bil:** source sýnir bakgrunn eða annan flöt milli líkamsparta.
2. **Óæskileg seam-lína:** örfín lína sker samfelldan flöt sem á að vera lokaður.
3. **Mask-gat:** geometry vantar vegna segmentation/mask failure.
4. **Rangt depth:** flötur er til en of framarlega/afturlega.
5. **Rangt anatomy:** coarse prior passar illa við nef, eyra, hönd eða líkamsform.
6. **Strekking/backfill:** front geometry er rétt en vantar útlínustrekkingu aftur í dýpt.
7. **Aðeins shading-vandamál:** geometry er rétt en normals/material láta hana líta illa út.

## Source-próf

Spyrðu alltaf:

- Er línan eða bilið sýnilegt í source ljósmyndinni?
- Er hönd eða handleggur fyrir framan bolinn?
- Heldur silhouette réttum lögun frá front-view?
- Er vandamálið enn sýnilegt með hlutlausu efni og Flat shading?
- Er það geometry eða aðeins texture?

## Topology-próf

Á vinnuafriti í Edit Mode:

1. Veldu `Select > Select All by Trait > Non-Manifold`.
2. Skoðaðu valið, en lagaðu ekki allt í einu.
3. Einangraðu lítið svæði með `H`/`Shift+H`; `Alt+H` sýnir aftur.
4. Athugaðu hvort boundary sé ætlaður silhouette eða óvænt gat inni á samfelldum flöt.
5. Skoðaðu face orientation overlay ef normals virðast snúa rangt.

Non-manifold selection er greining, ekki sjálfkrafa villa. Front-only 2.5D flötur er eðlilega opinn við mörk.
