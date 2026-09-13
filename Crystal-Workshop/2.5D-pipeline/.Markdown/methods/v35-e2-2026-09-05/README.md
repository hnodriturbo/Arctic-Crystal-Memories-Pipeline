<!--
Purpose: Preserve the user-selected E2 method, exact source snapshot and review conventions.
-->

# v3.5 E2 — varðveitt viðmið

Nýjasta samþykkta viðmiðið, með andlitsyfirferð Ömmu/Hreiðars og varðveittu Pabba E2, er [v35-best-2026-09-05](../v35-best-2026-09-05/README.md). Þar eru sjálfstæð afurðaafrit og SHA-256 skrá. Upprunalega E2-uppskriftin hér heldur gildi sínu.

Notandi valdi E sem grunn og samþykkti síðan E2 með endurunnu höfði og meiri jaðarstrekkingu. Hann metur Pabba-Bleikju E2 sjónrænt sambærilegt AC3D og myndi prenta það í kristal. Það er nú gæðaviðmið okkar. F/G er ekki grunnurinn.

## Varðveisla

- `manifest.json`: SHA256 á E2 GLB og tólf skrám vinnslukeðjunnar.
- `code-snapshot/`: afrit þessara skráa á þeim tíma sem E2 var samþykkt. Seinni rannsóknir mega breyta virkum kóða en ekki þessum afritum.
- `e-baseline-settings.json`: mælingar og stillingar E-grunnsins.
- `e2-head-edge-settings.json`: nákvæm höfuð- og jaðaraðlögun E2.
- Afurð: `output/research/2026-09-05-portrait-v35-single-surface/pabbi-bleikja/10-accepted-e-refinement/E2-head-edge/relief.glb`.
- Skoðunarafrit með sama SHA256: `output/research/2026-09-05-v35-point-review/pabbi-e2/relief.glb`.

Þessi skjöl og kóði eru í verkefninu. Stóru model-/output-skrárnar eru staðbundnar og geta verið útilokaðar með `.gitignore`; þetta er ekki staðfest ytra afrit eða GitHub-upphleðsla.

## Aðferðin

1. Halda upprunamynd, alpha, myndhnitum og UV-hnitum aðskildum frá áætlaðri dýpt. Hlutverk hvers hnútspunkts er sýnilegt myndsvæði.
2. MoGe-2 ViT-L normal, resolution 9, gefur dýpt og normalvigra. Innsetning á gráan bakgrunn er skráð forsenda fyrir afskornar myndir.
3. YuNet og MediaPipe finna andlit; MoGe vinnur andlitsútskurð til meiri staðbundinnar lögunar.
4. E myndar einn opinn flöt á 640-reita háu myndneti með hallamælingu og dýptarstíl úr dad-fish viðmiði. Normal integration er bundin við ±0,6 mm. Engin lokuð höfuðskel.
5. E2 notar aðeins höfuðsvæði úr PIXIE/SMPL-X → ICON → ECON d-BiNI keyrslu sem hefur verið skráð aftur í sömu myndhnit. Búkur, fætur og fiskur úr E halda sér. Þetta er **samsett vinnslukeðja**, ekki nýþjálfað tauganet.
6. Handstillt höfuðsvæði fyrir Pabba-Bleikju; dýptarskali 0,7882629102, hliðrun -9,8500822034 mm, breytingarmörk ±4 mm (raunverulegt hámark 2,005 mm). Kollur sléttaður sérstaklega þar sem notandi bað um slétta höfuðlögun.
7. Viðbótarjaðarstrekking allt að 1 mm innan 5 myndnetsreita, ofan á fyrri 0,6 mm jaðaraðlögun E. XY-hnit, UV-hnit og þríhyrningar eru varðveitt.

Nákvæmar leiðir, upprunaskráahash og mælingar eru í JSON-skránum. MoGe-checkpoint SHA256: `280741fd09bc3f403ccff9967784c2a391b52d2c0742ae3efdb21d9f90cc1a01`.

## Endurkeyra síðasta E2-skrefið

Úr rót 2.5D-pipeline, með fyrirliggjandi E og ICON-afurðum:

```powershell
& .venv/Scripts/python.exe code/research/refine_v35_accepted_e.py --baseline-dir output/research/2026-09-05-portrait-v35-single-surface/pabbi-bleikja/06-face-variants --icon-mesh output/research/2026-09-05-portrait-v35-single-surface/pabbi-bleikja/08-icon-source/person_01_source_camera.glb --source reference-gallery/original-images/Pabbi-Bleikja-Upscaled.png --output-dir output/research/e2-reproduction
```

Notið nýja úttaksmöppu. Fyrir nákvæma rúmfræðilega endurtekningu eftir framtíðarbreytingar skal bera virkar skrár saman við varðveitt SHA256/afrit. Byte-fyrir-byte GLB jafngildi er aðeins sannreynt fyrir varðveittu afritin, ekki lofað yfir mismunandi hugbúnaðarútgáfur.

## Punktaský og skoðunarviðmið

**Viðbót síðar í samtalinu:** föst ný útflutningsstilling er 0,08 mm X/Y og 0,09 mm Z, einn punktur í hverjum uppteknum reit. Sjá `point-cloud-profile.json`. Þétt 537.418 punkta samanburðarútgáfa er varðveitt og sjálfgefin í skoðaranum; nýja fasta netið fyrir Pabba hefur 593.235 punkta. Upprunalega 126.832 talan hér að neðan lýsir mesh-hnútum og fyrsta PLY-prófinu.

**Grátónapunktaský er sjálfgefin gæðaskoðun**, samkvæmt ósk notanda. 120 mm kubbur er sjálfgefinn viðmiðunarrammi; 150 mm er valkostur. Þau viðmið eiga ekki að breyta sjálfri mótuninni.

Skoðari: keyrið `start-v35-point-review.ps1` eða opnið `http://127.0.0.1:8427/` meðan þjónninn keyrir. Hann notar aðeins staðbundnar Three.js-skrár. Veljið grátóna, liti, yfirborð eða vírnet og stillið sjónarhorn.

- E2: 126.832 punktar, 251.183 þríhyrningar, 46,45 × 75,62 × 20,74 mm við varðveittan skala.
- Einn punktur fyrir hvern upprunalegan hnút; RGB er brúað úr raunverulegri áferð við UV-hnit.
- Grátónar nota 0,2126 R + 0,7152 G + 0,0722 B. Þetta er einföld skoðunartónun, ekki stilling mæld út frá kristal eða vél.
- PLY: millimetrar, litir/grátónar varðveittir. GLB: metrar.
- Skjápunktastærð í px og sýnilegur punktafjöldi breyta eingöngu skoðun, ekki PLY/GLB.
- Sýnilegur 120/150 mm rammi breytir ekki hnitum eða skala módels. Hann sýnir raunverulegt rúm þess innan rammans.
- E2 hnit og litir hafa verið sannreynd með endurlestri PLY; varðveitta GLB afritið hefur sama SHA256 og valda módelið.

Skoðunin er ekki mæling á ljósbroti eða leysipunktastærð. Þéttleiki raunverulegrar prentskrár þarf síðar að taka mið af vinnsluvél, punktabili og endanlegri stærð. Módellögunin er forgangsverkefnið núna.

## Yfirfærsla á fleiri myndir

Hreiðar og Amma-1 hafa fengið nýja MoGe-keyrslu, eigin andlitsútskurð, normal integration og sömu mjóu jaðaraðlögun. Módel og punktaský eru í sama skoðara.

Handstilltur skallareitur Pabba og ICON-höfuðið hans voru ekki yfirfærð. Þau væru röng fyrir þessar myndir. Því eru þetta yfirfærslupróf almennu E-stiganna, ekki fullyrðing um að allur E2-höfuðhlutinn sé orðinn sjálfvirkur.

Sjá `.Markdown/runs/2026-09-05-v35-point-review-and-transfer/README.md` fyrir niðurstöður og takmörk prófananna.
