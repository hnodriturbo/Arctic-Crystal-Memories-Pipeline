<!--
File: .Markdown/runs/2026-09-02-portrait-v32-head-lock/README.md
Purpose:
 - Record the first HRN-exclusive portrait head-lock experiment and why it remains unapproved.
-->

# Portrait v3.2-a — HRN-exclusive head lock

## Staða

**REJECTED / INFORMATIVE.** Reglan er staðfest, en heightfield-útfærslan er ekki lokaútfærslan.

## Model ownership

- Official ModelScope HRN Head v0.1: höfuð og andlit.
- Source-luma high-frequency residual: mjög lítið hair microdetail.
- MoGe-2 ViT-L: aðeins svæði neðan head-lock, bolur og fatnaður.
- MoGe pixels innan head-lock: `0`.
- Almennt fillet/smoothing á loka-heightfield: `0 mm` / disabled.

## Niðurstaða

- Nose prominence eftir smooth local correction: `0,1577` normalized.
- Við 20 mm working relief samsvarar það um `3,15 mm` fram yfir cheek reference.
- 363.105 vertices.
- 722.732 triangles.

Nefið er nú kúptara og profile réttara en í v3.1. Andlitsdetail er samt of mjúkt vegna þess að HRN native 37.587-vertex mesh var rasterað í depth-map og síðan endurbyggt sem reglulegt heightfield. Hárbrún er tennt vegna source-alpha/nearest-depth extension.

## Artifacts

Undir `output/local-workbench/a3c0aadb7e3c/`:

- `18-hrn-locked-head-moge-body/hrn-locked-head-stats.json`
- `18-hrn-locked-head-moge-body/hrn-exclusive-head-mask.png`
- `18-hrn-locked-head-moge-body/hrn-locked-head-moge-body-depth.png`
- `19-hrn-locked-head-mesh/portrait-hrn-locked-head.glb`
- `19-hrn-locked-head-mesh/qa/`

## Ákvörðun

V3.2-b skal nota direct HRN native front mesh patch. MoGe og almennt depth-smoothing mega aldrei vinna höfuð eða andlit. Hair silhouette og sliding stretch eru prófuð aðeins eftir að direct face geometry hefur verið samþykkt.

Sjá [áætlun 2026-09-03](../../plans/2026-09-03-V30-V32-EXPERIMENT-PLAN.md).
