<!--
File: .Markdown/runs/2026-09-04-ac3d-cockpit-amma-reference/README.md
Purpose:
 - Preserve the verified AC3D/Cockpit reference extraction and the controlled
   rerun of the frozen portrait v3.1 method on the same source photograph.
-->

# AC3D/Cockpit `amma` viðmið og okkar v3.1 endurkeyrsla

Staða: **staðfest ytra viðmið; v3.1 endurkeyrsla hafnað sem lokaúttak**.

## Markmið

1. Lesa núverandi `amma.cockpit` án þess að breyta original-skránni.
2. Endurbyggja staðlað, textúrað GLB úr innbyggðu triangle-mesh-i.
3. Greina editable yfirborðið frá þunga laser-point-cloud exportinu.
4. Endurkeyra vistaða portrait v3.1 aðferð á sömu `amma-2.jpeg` eftir
   BiRefNet Portrait bakgrunnsfjarlægingu.
5. Nota niðurstöðuna sem mælanlegt viðmið fyrir eigið 2.5D pipeline.

## Inntak

- Original ljósmynd: `input-testers/amma-og-afi/amma-2.jpeg`
- Bakgrunnsfjarlægð mynd: `output/local-workbench/preprocess/898dfc7155e0/03-background-removed.png`
- Cockpit verkefni: `cockpit-files/amma.cockpit`
- Cockpit export: `cockpit-files/exported/amma-exports/`

Originalmyndin og sýnileg crop-mörk hennar eru sannleikurinn. Þessi rannsókn
má ekki outpaint-a líkama, fatnað eða önnur ljósmyndarmörk sem sjást ekki.

## Staðfest Cockpit/CI uppbygging

`amma.cockpit` er venjulegur ZIP-container. Hann inniheldur:

- `CockpitScene.xml` með scene transform og Rectangle 80 × 120 × 60 mm;
- eitt `CIBF/CRUN` `.ci` triangle-mesh;
- svarthvíta JPEG-textúru;
- PNG print/silhouette maska.

Innbyggða `.ci` yfirborðið var lesið í hlutlausan vertex/index buffer og síðan
vistað sem standard GLB. Original `.cockpit`, `.ci` og export-skrár voru aðeins
lesnar.

| Mæling | Niðurstaða |
|---|---:|
| Vertices | 99.614 |
| Triangles | 198.063 |
| Scene-breidd | 67,304 mm |
| Scene-hæð | 127,528 mm |
| Scene-dýpt | 28,901 mm |
| Valinn kristall | Rectangle 80 × 120 × 60 mm |

Hæð geometry er því um 7,53 mm meiri en 120 mm kristallinn. Það styður
athugunina að portraitið sé fyrst byggt stærra og síðan trimmað við valið
kristalform.

## Point-cloud er annað úttak

`amma-1.dxf` inniheldur **4.435.041 POINT entities** og engin `3DFACE`, `MESH`,
`POLYLINE` eða önnur triangle-topology. Talan 4,4 milljónir er því fjöldi
laser-punkta, ekki fjöldi triangles í editable portrait-mesh-inu.

Stillingarnar í reference-keyrslunni voru:

- XY distance: 0,08 mm
- Z/layer distance: 0,09 mm
- Toning: 1,80
- Trim to template: virkt
- Layer shift: óvirkt
- Z jitter: virkt

Þetta verður aðskilið export-skref í okkar kerfi:

```text
GLB triangle master → crystal trim → laser sampling → DXF/XYZ/PLY
```

## Það sem GLB-ið staðfestir sjónrænt

- Framhliðin er source-aligned og heldur mjög miklum andlits- og fataatriðum.
- Höfuð og andlit nota stóran hluta af 28,9 mm heildardýptinni.
- Framhlið flíkurinnar er réttilega miklu þynnri.
- Svartir hlutar textúrunnar merkja óprentað svæði; geometry getur samt verið
  til staðar sem samfelldur depth/base-flötur.
- Gleraugun eru ekki sjálfstæður, fullkominn frame-object. Þau eru að hluta
  mótuð í sama surface og staðbundin strekking fyllir svæði sem opnast fyrir
  aftan framfærðan ramma.
- Crop-brúnir myndarinnar eru varðveittar. Engin ný, ósýnileg hlið manneskjunnar
  er fundin upp.

## V3.1 endurkeyrsla

Frozen `portrait-hrn-moge-v31` var keyrt aftur með sömu varðveittu HRN- og
MoGe-assets og bakgrunnsfjarlægðu portrait-inntaki.

| Stilling | Gildi |
|---|---:|
| Relief depth | 20 working mm |
| Grid | 416 × 900 |
| Boundary tolerance | 0,01 mm |
| Backfill rings | 8 |
| Loka-vertices | 265.842 |
| Loka-triangles | 523.254 |

Endurkeyrslan er reproducible, en sjónræn niðurstaða staðfestir fyrri höfnun:
andlitið verður of slétt/flatt, gleraugu verða að mestu teiknuð á surface,
hárbrúnin fær fringe-artifacts og profile er mun þynnri en AC3D reference.
V3.1 er því áfram varðveitt rannsóknarbaseline en verður ekki sjálfgefið preset.

## Afurðir

- Standard GLB: `output/research/2026-09-04-ac3d-cockpit-amma-reference/ci-glb/amma-ci-scene-mm.glb`
- Conversion report: `output/research/2026-09-04-ac3d-cockpit-amma-reference/ci-glb/report.json`
- AC3D GLB clay/source QA: `output/research/2026-09-04-ac3d-cockpit-amma-reference/qa-*`
- V3.1 GLB: `output/research/2026-09-04-ac3d-cockpit-amma-reference/our-v31-rerun/04-bounded-silhouette-backfill/portrait-with-silhouette-backfill.glb`
- [Artifact index](ARTIFACTS.md)

## Niðurstaða og næsta próf

Næsta portrait-run á ekki að vera einföld dýptarhækkun á v3.1. Það á að taka
mælda dýptaruppbyggingu reference-módelsins og sameina:

1. direct/native head surface fyrir andlit og höfuð;
2. MoGe/scene depth fyrir sýnilegan fatnað;
3. sér gleraugnalag með local occlusion backfill;
4. þunna flík við crop-brún;
5. oversized reconstruction sem er trimmað eftir á.

