<!--
Purpose: Preserve the user-approved best v3.5 results, their distinct face routes,
settings and provenance as the comparison baseline for subsequent experiments.
-->

# v3.5 — besta samþykkta viðmið, 5. september 2026

Notandi samþykkti nýjustu andlitsyfirferðina og lýsti sérstaklega niðurstöðu Ömmu sem mjög líkri AC3D-viðmiðinu. Þessi skrá festir þær niðurstöður sem besta sjónræna viðmið hingað til. Samþykkið staðfestir ekki enn raunprófun í kristal.

## Hvað er varðveitt

`artifacts/` geymir sjálfstæð afrit af GLB, grátóna PLY og upprunaskrá fyrir fjórar útgáfur. `manifest.json` geymir SHA-256, upprunastaðsetningu og afritsstaðsetningu. `code-snapshot/` geymir núverandi Python-kóða; `run-records/` geymir fyrri keyrslustillingar og `inputs/` myndbundin inntök. Upprunalegum afurðum er ekki breytt.

| Varðveitt útgáfa | Andlitsleið | Punktar |
|---|---|---:|
| Pabbi E2, samþykkt þétt viðmið | Myndskráð ICON-höfuð, staðbundin sléttun kolls | 537.418 |
| Pabbi E2, fast punktanet | Sama E2-mesh | 593.235 |
| Amma, adaptive face | Eigið HRN-andlit, 465 nothæfir af 468 punktum | 509.099 |
| Hreiðar, adaptive face | MediaPipe-dýptarpunktar, 468 nothæfir punktar | 373.097 |

537.418 punkta útgáfan er varðveitt sérstaklega; hún er eldri yfirborðssýnataka með 0,18 mm stillingu, ekki 0,08/0,09 mm netið. Nýtt fast net notar 0,08 mm í X/Y og 0,09 mm í Z. Punktar eru teknir eftir yfirborði og strekkifletir fá innri punkta; þetta fyllir ekki allt rúmmálið.

## Aðferðin sem leiddi að niðurstöðunum

1. Mynd með forgrunnsmaska; hlutlaus grár bakgrunnur fyrir ályktun. MoGe-2 ViT-L metur dýpt, yfirborðsnormal og myndavélarstika. Myndin sjálf sér um liti/áferð.
2. YuNet og MediaPipe finna andlit og andlitspunkta. MoGe vinnur einnig stækkað andlitsútsnið; upphafleg andlitsblöndun notar `shape_mix=0.8`.
3. Dýpt verður einn myndbundinn 2,5D-flötur með föstum XY/UV-hnitum. Dýptarhlutfall og heildarhalli eru kvarðaðir eftir mælingum á AC3D Pabba-viðmiði. Það er útlitskvörðun, ekki mæld líffræðileg dýpt nýju myndanna.
4. Screened normal integration bætir staðbundnu formi við dýptargrunninn, með allt að 0,6 mm leiðréttingu. Grunnmýking er 1,5 netpunktar. Jaðarfærsla er 0,6 mm á þröngu þriggja netpunkta svæði og síðan 1 mm viðbótarstrekking á fimm netpunktum.
5. Pabbi E2 fékk handafmarkað höfuð úr myndskráðri ICON/ECON d-BiNI leið. PIXIE með SMPL-X var líkamsviðmið í þeirri undirkeyrslu. E-líkaminn, fiskurinn og hendurnar voru áfram grunnurinn. Þessi myndbundna höfuðleiðrétting var ekki flutt yfir á Ömmu eða Hreiðar.
6. Amma fékk varðveitt fullt dýptarbil og lokayfirferð með eigin HRN-framfleti. SIFT tengir hann við ljósmyndina (24 inliers, miðgildisvilla 1,139 px). Hreiðar fékk grófari formleiðréttingu úr þrívíðum MediaPipe-punktum. Ekki var þjálfað nýtt tauganet.
7. Lokayfirferð samræmir andlitsdýpt og halla við grunnflöt, dregur úr breiðum lögunarmismun og blandar leiðréttingunni mjúklega að mörkum andlits. Aðeins Z innan vinnslusvæðisins breytist; XY, UV og þríhyrningar haldast. Hámarksraunbreyting var 1,887 mm hjá Ömmu og 0,475 mm hjá Hreiðari.
8. Punktaský er tekið úr endanlegum þríhyrningum, með þéttingu á löngum strekkiflötum. Fast útflutningsnet er 0,08 × 0,08 × 0,09 mm, einn punktur í hverju uppteknu netrúmi. Grátónn kemur úr upprunamyndinni. GLB er í metrum, PLY í millimetrum. 120/150 mm teningurinn í skoðara er stærðarviðmið.

## Stillanleg andlitsyfirferð

Kóði: `code/research/finalize_v35_faces.py` og `face_support_v35.py`.

| Stilling | Núverandi gildi/hegðun | Áhrif |
|---|---|---|
| `--max-change-mm` | 3 mm | Hámark Z-leiðréttingar áður en jaðarblöndun er lögð á |
| `--broad-shape-retention` | 0,2 | Hversu miklu af breiðri lögunarbreytingu er haldið; hærra gildi flytur meira heildarform frá andlitsgjafa |
| `--boundary-width-px` | Sjálfvirkt út frá andlitsbreidd | Mýkt samskeyta, mæld í netpunktum; hægt að yfirskrifa |
| `--visibility-mask` | Valfrjálst | Svört myndsvæði eru varin gegn breytingu |
| `--hrn-assets` og `--registration` | Myndbundin gögn | Velja skráðan HRN-framflöt þegar hann er tiltækur |

Sjálfvirk blendibreidd: `clip(andlitsbreidd * 0.11, 3, 18)` netpunktar. Breið mýking: `clip(andlitsbreidd * 0.055, 1.2, 9)`. Áreiðanleikagildi undir 0,5 eru útilokuð ef þau fylgja gögnunum. Sex ólínulegir punktar eru lágmarksreiknistuðningur, ekki loforð um góð andlitsgæði.

Þetta eru skipanalínu- og kóðastillingar. Skoðarinn hefur ekki enn sérstaka andlitsrenna. Hægt er að tengja þessar stillingar við viðmót síðar og bæta við afmörkuðum nef-/augu-/munnsvæðum sem nýrri tilraun. MediaPipe getur spáð punktum sem eru huldir; núverandi leið greinir ekki sjálfkrafa allar hulanir.

## Varðveisla og næstu tilraunir

- Þetta viðmið er fryst afrit til samanburðar; nýjar tilraunir fara í nýjar möppur. Engar NTFS-læsingar eru settar á skrár.
- Ekki endurkeyra yfir samþykkt GLB/PLY. Skrá nýtt viðmið aðeins eftir nýtt mat notanda.
- Eldri `CANDIDATE`/`NOT_USER_APPROVED` merkingar í afrituðum keyrsluskrám eru sögulegar. Nýtt samþykki er skráð í þessu viðmiði og `manifest.json`.
- Kóðaafritið er núverandi útgáfa eftir keyrslurnar, með síðari inntaksvörnum og tengingu sjálfvirkrar keyrslukeðju. Það er ekki fullyrt að hver kóðabæti sé sá sami og við allar eldri keyrslur. Samþykktar afurðir sjálfar eru varðveittar og hash-staðfestar.
- Í Ömmu-skýrslu er gamla efsta gildið `boundary_width_grid_px: 14.0` greiningartexti; raunbreiddin var `faces[0].support.boundary_width_grid_px: 14.7439712806351`. Hreiðar notaði 4.493306818822056. Þessi gildi eru varðveitt óbreytt.
- Ellefu afmörkuð próf stóðust í fyrri vinnslu. Ný sjálfvirk tenging allra stiga í `run_v35_transfer.py` hefur ekki enn verið keyrð frá upphafi til enda; samþykktu afurðirnar komu úr stökum staðfestum vinnslustigum.

Stór milligögn og módelvigtir eru áfram á upprunastað og lykilinntök skráð með hash. Þetta er staðbundið varðveislusafn, ekki sjálfstæður uppsetningarpakki með öllum módelum og keyrsluumhverfum.
