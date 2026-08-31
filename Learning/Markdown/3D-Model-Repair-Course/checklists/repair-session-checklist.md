<!--
File: Learning/Markdown/3D-Model-Repair-Course/checklists/repair-session-checklist.md
Purpose:
 - Provide a reusable checklist for every manual mesh-repair session.
-->

# Checklist — handvirk mesh-lagfæring

## Fyrir vinnu

- [ ] Baseline-hash og run-skráning fundin.
- [ ] `Save As` gert í `output/learning/`.
- [ ] Source object afritað og læst.
- [ ] Source ljósmynd sýnileg til samanburðar.
- [ ] Front og 45° „before“ screenshots tekin.

## Greining

- [ ] Vandamálið flokkað: occlusion, seam, mask-gat, depth, anatomy, strekking eða shading.
- [ ] Staðfest að bilið/línan sé ekki eðlileg í source.
- [ ] Skoðað í Solid, Wireframe og með neutral material.
- [ ] Side-view og axis direction staðfest.

## Breyting

- [ ] Aðeins lítið staðbundið svæði valið.
- [ ] X-Ray slökkt nema þörf sé á vali í gegnum mesh.
- [ ] Engin global remesh/decimate/fill keyrsla.
- [ ] Eðlileg bil milli handar, handleggs og bols varðveitt.
- [ ] Ný útgáfa vistuð áður en modifier er applied.

## Eftir vinnu

- [ ] Front, 15°, 30° og 45° skoðað.
- [ ] „After“ screenshots tekin með sama camera/material.
- [ ] Export re-importað í tóma senu.
- [ ] Scale, axes, normals og face count staðfest.
- [ ] Breytingar og tölugildi skráð.
- [ ] Ný artifact-hash skráð.
