<!-- Purpose: Separate mesh preparation, SSLE point generation and DXF serialization; record what remains to validate. -->
# GLB → punktaský → DXF

## Þrjú ólík gagnastig

1. **GLB:** yfirborð úr þríhyrningum, UV-hnit og ljósmynd/efni. Hentar til
   lagfæringa í Blender. Fjöldi hornpunkta segir ekki hversu marga laserpunkta
   eigi að mynda.
2. **Punktaský:** valdar staðsetningar í rúmi. Punktagerðin þarf að taka tillit
   til yfirborðs, ljósmyndar, stærðar í mm, punktabils og dýptar.
3. **DXF:** skráarsnið sem getur geymt niðurstöðuna sem POINT-einingar. DXF getur
   einnig geymt 3DFACE/þríhyrninga og aðrar einingar; endingin tryggir ekki
   að skráin sé punktaský.

Autodesk skilgreinir POINT með X/Y/Z-hnitum í group codes 10/20/30.
Þetta lýsir hnitunum, ekki reikniritinu sem ákvað hvar punktarnir ættu að vera.
[Autodesk POINT reference](https://help.autodesk.com/cloudhelp/2024/ENU/AutoCAD-DXF/files/GUID-9C6AD32D-769D-4213-85A4-CA9CCB5C5317.htm)

Cockpit3D lýsir sjálfu sér sem kerfi sem myndar punktaský fyrir innri
lasergrafík. Opinbera síðan birtir ekki nægilega ítarlega lýsingu til að fullyrða
að reiknirit Workshop sé hið sama.
[Cockpit3D](https://cockpit3d.com/)

## Hvað núverandi Workshop gerir

- Reconstruct les alla DXF-punkta með samþykktu stillingunum og áætlar slétt
  2.5D-yfirborð með réttri ljósmynd. Þessi aðgerð er ekki afturkræf að upprunalega
  punktaskýinu: upplýsingar um mörg lög geta sameinast í eitt yfirborð.
- Model converter notar Blender fyrir innlestur, mm-stærðir og yfirborðsbreytingar.
  GLB/glTF hnit eru lesin sem metrar; í viðmóti er því valið m fyrir þau snið.
- mesh_to_pointcloud.py myndar nýja punkta; printer_dxf.py skrifar POINT DXF.
  Þetta eru aðskildar aðgerðir þótt einn vefhnappur geti keyrt báðar.
- Nýr **experimental** valkostur notar UV-ljósmynd fyrir punktþéttleika. Hann er
  sjálfgefið óvirkur og krefst einnar ótvíræðrar myndaráferðar. Svart svæði fær
  enga punkta með density-floor 0. Margar áferðir þarf fyrst að baka í eina í Blender.
  Þetta er prófunaraðferð, ekki staðfest SSLE-framleiðslustilling.

Almenn yfirborðssýnataka er vel skilgreind, en jafndreifðir yfirborðspunktar eru
ekki sjálfkrafa ljósmyndarleg eða vélarsértæk SSLE-gögn. Jafnvel “even” sampling
getur skilað færri punktum en beðið var um vegna bils milli punkta.
[Trimesh sampling documentation](https://trimesh.org/trimesh.sample.html)

## Samanburður sem þarf áður en framleiðslugæði eru samþykkt

Nota sama litla prófverk með tveimur leiðum: Cockpit PointCloudBuilder og
Workshop punktagerð. Varðveita nákvæmar stillingar og báðar DXF-skrár.

- Staðfesta POINT-einingar, mm-stærð, miðju og ásastefnu.
- Bera saman punktatalningu, min/max hnit og punktabil, bæði innan lags og milli laga.
- Skoða björt, grá og svört svæði: varðveitir punktþéttleikinn ljósmyndina?
- Skoða hvort Cockpit myndar mörg dýptarlög eða þykkt um yfirborðið sem GLB hefur ekki.
- Prófa eyru, útlínur, andlit, skörun og aðskildar manneskjur; ekki brúa tómt bil.
- Prófa tvöfalda mm-stærð og mæla punktþéttleika aftur. Fleiri punktar bæta ekki
  sjálfkrafa upplýsingum sem þegar töpuðust við endurgerð yfirborðs.
- Staðfesta vélarsnið, æskilegt punktabil og vinnslumörk við leiðbeiningar vélarinnar.
  Síðasta samþykki krefst samanburðar á raunverulegri prufugrafík í kristal.

Fyrstu samþættingarprófanir athuga GLB í metrum, UV-mynd með svörtum/hvítum
svæðum og að DXF innihaldi eingöngu POINT. Þær staðfesta gagnaleiðina, ekki
að myndgæði jafngildi Cockpit3D eða að tiltekinn punktþéttleiki sé framleiðsluhæfur.

Til að fá native .cockpit verkefni aftur skal flytja niðurstöðuna inn í Cockpit
og vista þar. Workshop gefur ekki loforð um að endurskapa allt sértækt verkefnasnið þess.

## Owner-approved point-cloud baseline

Point spacing: **0.08 mm**. Layer spacing: **0.09 mm**. These are the main
point-cloud settings specified by the owner on 2026-09-13. Keep both in the UI
and Python defaults; do not conflate point spacing with layer spacing.
Photo-driven density remains separate and experimental.

See [verified Cockpit settings](COCKPIT-SSLE-SETTINGS.md) for the owner's five
screenshots, the source scene attributes and the verified Jón Þór job rotation.
New reconstruction GLBs store `asset.extras.acmReconstruction`: SHA-256 source
identities, raw Cockpit settings, applied pose and reconstruction options. The
same metadata is retained in the output JSON report. This does not change the
surface or activate Cockpit's proprietary point-generation algorithms.
