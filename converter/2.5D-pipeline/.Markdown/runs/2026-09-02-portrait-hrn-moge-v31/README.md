<!--
File: .Markdown/runs/2026-09-02-portrait-hrn-moge-v31/README.md
Purpose:
 - Freeze the close-portrait v3.1 diagnosis, model stack, settings, and accepted research output.
-->

# Close portrait: HRN + MoGe-2 v3.1

> **Staða: REJECTED sem portrait-output.** Runnið er varðveitt sem mikilvægt failure-evidence. HRN native head var góður, en raster-depth fusion, head-wide MoGe/blending og hair backfill minnkuðu andlitsdetail og mynduðu ranga hárbrún.

## Niðurstaða

Samþykkta v3-leiðin keyrði til enda, en hún er röng leið fyrir þessa nærmynd. PARE túlkaði myndina sem heila sitjandi manneskju og hallucinated krosslagðar hendur yfir bringunni. ICON normals og ECON d-BiNI gerðu síðan þetta ranga prior að samfelldri geometry. Svarthvíta contrast-appearanceið olli þessu ekki.

V3.1 portrait-tilraunin fjarlægði PARE/ICON/ECON úr nærmyndinni:

```text
RGBA ljósmynd
  ├─ MoGe-2 ViT-L: raunverulegur bolur, jakki og source-aligned grunndýpt
  ├─ Official ModelScope HRN Head v0.1 (BFM+FLAME): höfuð og andlit
  ├─ SIFT + RANSAC: HRN varpað í nákvæma source-camera
  ├─ feathered HRN/MoGe depth fusion
  ├─ 0,01 mm edge/boundary fillet
  └─ afmörkuð multi-ring útlínustrekking
       ↓
dense source-aligned 2.5D triangular geometry + B/W vertex appearance
```

## Server-greining

Dev-serverinn hrundi ekki í keyrslunni. Job `a3c0aadb7e3c` kláraðist og skrifaði `relief-crystal.glb`. Bæði API á porti 8425 og UI á porti 3000 svöruðu HTTP 200 við greiningu. `/api/health` skilaði 404 vegna þess að sú route er ekki skilgreind, ekki vegna þess að serverinn væri niðri.

`start-local-workbench.ps1` keyrir API falið en UI í foreground. Ef UI-processinn eða terminal-tabbið lokast fer scriptið í `finally` og stöðvar API. Þess vegna skal halda terminalinum opnum eða ræsa aftur úr `converter/2.5D-pipeline` með:

```powershell
.\start-local-workbench.ps1
```

## Staðfest orsök rangrar dýptar

- PARE/SMPL body prior bjó til hendur og arma sem eru ekki í source-myndinni.
- Ranga formið sést þegar í ECON front-depth preview, áður en texture eða contrast er sett á.
- Mesh-ið var einn samfelldur flötur; þetta var ekki duplicate face eða aðskildir saumaðir mesh-hlutar.
- Source-camera registration gamla v3-runsins var nákvæm: 464/478 inliers og 0,167 px miðgildisvilla.
- Dýptarþjöppun og local Gaussian ramps sléttuðu rangt prior en gátu ekki lagað merkingarfræðilega hallucination.

Þetta leiðir að föstu routing-reglunni:

- full-body eða medium shot: PARE/ICON/ECON má vera structural baseline;
- close portrait: HRN + MoGe-2, án full-body HPS-priors.

## Mælingar nýju leiðarinnar

- HRN/source registration: 42 inliers af 57 matches.
- Inlier ratio: 0,7368.
- Miðgildi reprojection error: 1,148 px.
- 95% reprojection error: 3,051 px.
- Alpha components: 8; stærsti person-component varðveittur.
- Varðveitt alpha-svæði: 1.258.947 px.
- Ótengdu 24.165 px hent, þar með talið aðskilinn hlutur fyrir ofan hárið.
- HRN-weighted fusion: 512.947 pixels.
- Mesh fyrir backfill: 243.258 vertices / 483.690 triangles.
- Mesh eftir bounded backfill: 265.842 vertices / 523.254 triangles.

## Model routing fyrir þessa einu mynd

Þetta er ein-myndar/ein-manneskju portrait keyrsla. Source-evidence er túlkað svona:

- eitt ráðandi andlit;
- höfuð, andlit, eyru, háls og axlir sjást;
- sýnilegur efri búkur og jakki eiga að koma beint úr myndinni;
- hendur, hné, ökklar og fullur neðri líkami eru ekki staðfest source-visible;
- þess vegna á full-body HPS ekki að completion-a þá inn í outputið.

Valið region ownership er HRN fyrir sýnilegt höfuð/andlit, MoGe-2 fyrir sýnilegan háls/axlir/bol/jakka, source alpha fyrir silhouette og original B/W luma fyrir appearance. PARE→ICON→ECON var hafnað fyrir þetta portrait eftir að PARE bjó til ósýnilegar krosslagðar hendur.

Nýjar keyrslur skrifa þetta í `model-route.json`; human-review reitirnir eru fylltir eftir neutral QA svo routing-reglurnar byggist upp út frá staðfestum niðurstöðum.

## Stillingar

- `grid=900`
- `edge-fillet-mm=0.01`
- `boundary-fillet-mm=0.01`
- `HRN depth span=0.34`
- `HRN feather fraction=0.035`
- vertical HRN fade `0.72 → 0.87`, svo raunverulegur jakki komi frá MoGe
- backfill: 8 rings, inset `0.65`, depth `0.35 → 2.5`
- outer-boundary smoothing: 32 iterations, weight `0.52`
- B/W luma er vertex appearance; það breytir ekki geometry

`100x220x40`, 20 depth og 0,1 border eru neutral research-working space, ekki endanleg kristalstærð. Crystal fitting á að koma eftir geometry approval.

## Artifacts

- Upprunalegt v3 output: `output/local-workbench/a3c0aadb7e3c/relief-crystal.glb`
- HRN native head: `12-hrn-head/source-prepared/hrn-head.obj`
- HRN/MoGe fusion diagnostics: `14-hrn-moge-portrait-fusion/`
- Dense base mesh: `15-hrn-moge-portrait-mesh/portrait-hrn-moge.glb`
- Núverandi bounded-backfill candidate: `17-hrn-moge-bounded-backfill/portrait-with-silhouette-backfill.glb`
- Neutral QA: `17-hrn-moge-bounded-backfill/qa/`

Allar slóðir fyrir ofan eru undir `converter/2.5D-pipeline/output/local-workbench/a3c0aadb7e3c/`.

## Endurkeyrsla

Endurvinnsluscriptið tekur varðveitt HRN OBJ og MoGe raw-depth og skrifar alltaf í nýja tóma möppu:

```powershell
.\code\research\run_portrait_hrn_moge_refinement.ps1 `
  -Source .\output\local-workbench\a3c0aadb7e3c\source-prepared.png `
  -MogeDepth .\output\local-workbench\a3c0aadb7e3c\05-moge-scene-depth\depth_raw.npy `
  -HrnObj .\output\local-workbench\a3c0aadb7e3c\12-hrn-head\source-prepared\hrn-head.obj `
  -OutputDir .\output\research\portrait-hrn-moge-v31-rerun
```

Scriptið býr til manifest með source/result SHA-256, model stack, stillingum og QA-slóðum. Það neitar að skrifa í möppu sem inniheldur fyrri baseline.

Beinar runtime-útgáfur keyrslunnar eru frystar í [requirements.txt](requirements.txt). HRN keyrði í aðskildu WSL micromamba environment; Windows fusion/mesh/router keyrði í pipeline `.venv` og QA í Blender 5.1.

## Takmörk og næsta refinement

Þessi rejected candidate fjarlægði fake hendur og mestu öfugu dýptarsaumana, en náði ekki samþykktum portrait-gæðum:

1. fínar alpha/hair-edge sveiflur eru enn við efstu útlínu;
2. HRN geometry endurgerir ekki gleraugu eða augn-op sem sjálfstæða geometry; B/W appearance varðveitir þau sjónrænt;
3. útlínustrekkingin þarf áfram QA gegn AC3D frá 30–45°;
4. endanleg mm-dýpt og kristalstærð koma aðeins eftir samþykki á source geometry.

Næsta skref er v3.2 direct HRN head/face ownership. Sjá [v3.0/v3.2 tilraunaáætlun](../../plans/2026-09-03-V30-V32-EXPERIMENT-PLAN.md).
