<!--
File: .Markdown/runs/2026-09-04-portrait-v34-source-structured/README.md
Purpose:
 - Record the portrait v3.4 source-structured control and stress-test runs.
 - Separate verified improvements from remaining rejected geometry.
-->

# Portrait v3.4 — source-structured HRN, gleraugu og hair pullback

Status: **RESEARCH CANDIDATE — ekki samþykkt preset**

## Niðurstaða

V3.4 sannar að hægt er að bæta sjálfstæðu, opnu gleraugnalagi ofan á native
HRN-andlit án þess að búa til þykka linsudiska. Sama sex-hringja tapered
backfill aðferð virkaði bæði á `amma-1` control-myndinni og erfiðu `amma-2`
stress-test myndinni. Gleraugnin sjást nú sem sér geometry í front, 30° og
profile QA.

Heildardýptin var líka bundin við mælt AC3D viðmið:

| Run | Fyrri dýpt | V3.4 dýpt | Dýpt/hæð | AC3D viðmið |
| --- | ---: | ---: | ---: | ---: |
| `amma-1` control | 0,7464 | 0,3863 | 0,2270 | 0,2266 |
| `amma-2` stress | 0,6242 | 0,3811 | 0,2274 | 0,2266 |

Þetta styður hugmyndina um fyrirfram ákveðið portrait-depth envelope: lögun
andlitsins má haldast fyrir framan fast front-anchor en bakhliðin er þjöppuð að
stýrðu dýptarbili. PARE/full-body completion er ekki notað í hvorugu runni.

## Hvað batnaði frá v3.3

- MediaPipe 468 punktar staðsetja augu, nef, varir og andlitsramma á báðum
  myndum þrátt fyrir gleraugu.
- Source edge/darkness score velur rounded lens-rönd innan líffræðilega
  raunhæfs gleraugnabils; það forðast fyrri tilraun sem festist á augnlokunum.
- Hver rammi er mjó opin ribbon-skel, lyft `0,016` working units frá HRN-húð.
- Sex tapered hringir fylla aðeins bilið frá andliti að ramma. Miðja linsunnar
  er opin og enginn þykkur diskur lokar auganu.
- Source-luminance detail er nú aðeins `±0,0015` og er sléttað áður en það
  færist yfir á HRN. Fyrsta `±0,006` tilraunin varð gróf steináferð og er því
  varðveitt sem hafnað milliskref.
- Hair-shell notar aðeins source-alpha fyrir hárarea utan HRN og dregst
  samfellt aftur að staðbundnu scalp-anchor í stað óbundinna edge-spíka.

## Af hverju þetta er ekki samþykkt

`amma-1` var valin sem auðveldari control-mynd vegna þess að hún sýnir eina
manneskju, beinna andlit og meiri búk. Hún sýnir samt skýran eldri v3.3 galla:
HRN-höfuðið og MoGe-búkurinn mætast sem tvö lög og skilja eftir láréttan seam
undir kjálkanum. V3.4 breytir ekki þeirri ownership-samskeytingu.

Fleiri takmörk:

- rammarnir eru source-stýrðir en enn parametric/idealized, ekki nákvæm
  segmentation á hverjum original ramma;
- temple arms eru einfaldar source-plane línur;
- hair-shell er hreinni en getur enn lesist sem þunn afturdráttarrönd í hreinu
  profile-renderi;
- native HRN höfuðið er enn almennara en AC3D andlitsbyggingin;
- útlínur fatnaðar eru áfram MoGe heightfield og neðri source-crop er opinn.

Því er v3.4 **framför í gleraugum og dýptarstýringu**, en ekki heildarlausn.
Næsta afmarkaða geometry-verkefni er að stitcha/remesha HRN-neðri mörk við
MoGe háls/búk áður en meira micro-detail er bætt við.

## Runtime athugasemd

HRN keyrslan þurfti ekki nýtt módel eða netniðurhal. WSL hafði GCC 13 á meðan
frosna CUDA 11.8 umhverfið styður GCC ≤11 fyrir endurbyggingu `nvdiffrast`.
`run_hrn_head_modelscope.py` getur nú tekið explicit staðbundið, áður samsett
`nvdiffrast_plugin.so`. Það endurnýtir staðfest binary og forðast ósamhæfa
endurbyggingu; módelið og HRN geometry-kóðinn haldast óbreytt.

## Samanburður og gögn

- [Myndasamanburður](artifacts/gallery/README.md)
- [Artifact kort](ARTIFACTS.md)
- AC3D reference: `28,9007 / 127,5276 = 0,2266` depth/height
- `amma-1` MoGe subject p99-p1: `0,2380 m`
- `amma-1` HRN/source registration median: `1,139 px`
- Gleraugnalag í hvoru runni: `6.446` þríhyrningar
