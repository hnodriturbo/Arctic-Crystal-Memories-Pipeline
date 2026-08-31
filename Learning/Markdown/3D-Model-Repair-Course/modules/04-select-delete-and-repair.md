<!--
File: Learning/Markdown/3D-Model-Repair-Course/modules/04-select-delete-and-repair.md
Purpose:
 - Teach localized topology edits without broad destructive cleanup.
-->

# 04 — Val, eyðing, göt og seams

## Nákvæmt val

Í Edit Mode:

- `1`, `2`, `3` efst á lyklaborði velja vertex, edge eða face selection.
- `L` yfir geometry velur tengdan mesh-hluta.
- `Alt` + smellur á edge getur valið edge loop þegar topology leyfir.
- `B` gerir box select; `C` circle select.
- `H` felur val; `Shift+H` felur allt nema val; `Alt+H` sýnir allt.

Slökktu á X-Ray áður en þú velur aðeins sýnilegan frontflöt.

## Eyða rusli

1. Veldu örugglega aðeins óæskilega faces.
2. Ýttu `X`.
3. Veldu `Faces`, ekki vertices, ef nærliggjandi geometry á að lifa.
4. Skoðaðu side og back view áður en þú samþykkir.

## Laga lítið óæskilegt gat

1. Staðfestu að gatið sé ekki eðlilegt occlusion-bil.
2. Veldu boundary edges.
3. Fyrir einfalt lítið gat: `F` til að fylla.
4. Fyrir stærra reglulegt gat: leitaðu með `F3` að `Grid Fill`.
5. Reiknaðu normals með `Shift+N` ef shading snýst rangt.
6. Smooth-a aðeins nýja svæðið og bera við source.

## Sameina örfína seam-línu

Ef tveir edge-bakkar eiga sannarlega að vera sama yfirborð:

1. Veldu fáa samsvarandi vertices í einu.
2. Notaðu `M` til að merge-a á viðeigandi stað, eða Bridge Edge Loops ef tvær hreinar raðir eiga að tengjast.
3. Forðastu global `Merge by Distance` á dense face/hand geometry; það getur eytt örsmáum eðlilegum bilum.

## Ekki gera þetta á fyrsta vinnudegi

- Global voxel remesh.
- Decimate á andliti eða höndum.
- Fill All Holes yfir allt front-only mesh.
- Global Laplacian smoothing.
- Apply-a modifiers áður en vistað hefur verið nýtt version.
