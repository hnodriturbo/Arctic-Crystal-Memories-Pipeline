<!--
File: Learning/Markdown/3D-Model-Repair-Course/modules/05-smoothing-and-sculpting.md
Purpose:
 - Teach controlled smoothing and sculpt refinement while preserving identity detail.
-->

# 05 — Smooth, Sculpt og varðveisla smáatriða

## Þrjár ólíkar merkingar „smooth“

1. **Shade Smooth:** breytir aðeins útreikningi normals/shading; færir ekki vertices.
2. **Smooth modifier eða vertex smoothing:** færir geometry og getur eytt detail.
3. **Sculpt Smooth brush:** staðbundin geometry-breyting undir brush.

Byrjaðu alltaf á að prófa Shade Smooth. Ekki breyta geometry ef vandamálið er aðeins shading.

## Örugg Sculpt-aðferð

1. Notaðu `WORKING_` afrit.
2. Farðu í Sculpt Mode.
3. Maskaðu svæðin sem mega alls ekki hreyfast.
4. Hafðu brush lítinn miðað við andlitið.
5. Notaðu lágan strength og margar litlar strokes.
6. Skoðaðu front og side eftir hverjar fáar strokes.

## Tool-hlutverk

- **Smooth:** örfínar óreglur; hættulegt fyrir hrukkur og hár.
- **Grab:** færa silhouette eða eyra með mjúkri falloff.
- **Inflate/Deflate:** staðbundin fylling; mjög lítið strength.
- **Draw/Clay:** byggja upp vantað volume, síðan mjög mild smoothing.

## Detail hierarchy

Vinnaðu frá stærstu formum niður:

1. höfuð/bolur og silhouette;
2. nef, kinn, haka, háls og eyra;
3. varir, augnlok, fingur og fatabrúnir;
4. hár, hrukkur og surface texture.

Ef farið er beint í hrukkur áður en head form er rétt verður refinement rangt þó renderið líti skarpt út.
