<!--
Purpose: Record point-cloud delivery, transferable-stage trials and observed limitations.
-->

# Punktaský, varðveisla og yfirfærslupróf v3.5

## Viðmið sem notandi valdi

Pabbi-Bleikja E2 er sjónræna gæðaviðmiðið. Notandi telur það sambærilegt AC3D og myndi prenta það í kristal. Grátónapunktaský er sjálfgefin skoðun; 120 mm kubbur sjálfgefinn rammi og 150 mm valkostur. Sjálf mótun hefur forgang umfram skölun.

Aðferðin og óbreytt kóðaafrit voru vistuð í `.Markdown/methods/v35-e2-2026-09-05/` með SHA256, E/E2 stillingum og endurkeyrsluleiðbeiningum.

## Skoðari og skrár

- Ræsing: `start-v35-point-review.ps1` úr rót pipeline. Þjónn bindst aðeins 127.0.0.1, sjálfgefið port 8427.
- Afurðir og staðbundinn Three.js-skoðari: `output/research/2026-09-05-v35-point-review/`.
- Grátóna-PLY og litað PLY nota mm; GLB notar metra. GLB afritið af E2 er byte-fyrir-byte sama skrá og notandi valdi.
- PLY voru lesin aftur inn: hnit, punktatalning og RGB gildi staðfest.
- Skoðari hefur grátóna, RGB, hvíta punkta, litað mesh, grátt yfirborð og vírnet. Hann breytir ekki útfluttum gögnum þegar skjápunktastærð eða sýnilegur punktafjöldi breytist.
- 120/150 mm rammi sýnir stærðarhlutföll með óbreyttum mesh-hnitum, ekki sjálfvirka þjöppun dýptar.
- Staðfest með vafraskoðun: grátónar sjálfgefnir, skipting yfir í vírnet, 30° sjónarhorn, módelaskipting Pabbi/Amma og 120/150 mm stjórntæki. Mjór Codex-gluggi fær myndsvæði efst og stjórntæki neðar.

## Fleiri myndir

| Mynd | Punktar í fyrsta útflutningi | Þríhyrningar | Stærð mm |
|---|---:|---:|---|
| Pabbi E2 | 126.832 | 251.183 | 46,45 × 75,62 × 20,74 |
| Hreiðar | 75.326 | 148.497 | 53,83 × 74,62 × 16,91 |
| Amma-1 | 128.580 | 255.441 | 36,81 × 67,86 × 19,62 |

Hreiðar og Amma-1 fengu nýja MoGe-2 ViT-L normal keyrslu, resolution 9, á staðbundinni RTX 3060. YuNet fann aðalandlit á hvorri mynd og MediaPipe mældi 468 punkta. Eigin MoGe-andlitsútskurður, screened normal integration, eitt UV-net og viðbótarjaðarstrekking voru keyrð með sömu almennu stillingum og E.

Handstilltur skallareitur og ICON-höfuð Pabba voru ekki flutt yfir. Því er þetta yfirfærsla almennu E-stiganna; sjálfvirkur E2-höfuðhluti er ekki fullgerð almenn lausn. Engin ný tauganetsþjálfun fór fram.

- Hreiðarsmyndin er samsett mynd með stórum gítar og dökku bakgrunnsandliti. Aðalandlitið og myndin varðveitast í framvörpun en hliðarlögunin er flöt og strekkir umhverfi höfuðsins. Hún stenst ekki enn Pabba E2-viðmiðið.
- Amma-1 varðveitir andlit, gleraugu og föt, en hafði afmarkaðar flatar skellur á enni/hári og enn rifflur við útlínur.
- Módelin voru skoðuð í sömu Blender-myndavélum og Pabbi; afurðir í `output/research/2026-09-05-v35-transfer/gallery/`.

## Afmörkuð athugun á dýptarklippingu

`amma-1-range-preserved` notar sömu upphaflegu float-MoGe-gögnin. Breytt var tveimur klippingarstigum: 16-bita normalisering tekur allt gilt dýptarbil og robust quantile-mörk eru aðeins notuð fyrir skala, ekki til að klippa rúmfræðina sjálfa. Andlitsstigið var keyrt aftur.

Flötu ennis-/hárskellurnar minnkuðu sjónrænt. Dýpt jókst úr 19,62 í 25,09 mm við óbreytt XY. Þetta styður að klipping stuðli að skellunum, en aðgreinir ekki áhrif stiganna tveggja. Ekki yfirfæra breytinguna sjálfkrafa á samþykkta E2-skrá. Næst þarf að stýra heildardýpt án þess að gera litla hluta andlits flata.

## Þéttari strekkifletir

Notandi benti á of langt bil milli punktaraða við fisk/líkama. Fyrsti útflutningur notaði aðeins fyrirliggjandi mesh-hnúta; þess vegna gátu brött yfirborð haft löng 3D-bil þótt myndnetið væri þétt í XY.

`sample_relief_surface.py` bætir við punktum á sameiginlegum brúnum og í röðum innan langra þríhyrninga. Hnit og UV eru brúuð á fyrirliggjandi þríhyrningum. E2-meshið er óbreytt; þetta eru fleiri punktar á sama strekkifleti, ekki ný lokuð lög eða fylling í gegnum tómt rúmmál.

Fyrsta þéttingarpróf notar 0,18 mm sýnatökubil við varðveitta stærð módelsins. Það er skoðunarstilling, ekki staðfest leysipunktabil. Punktatalning og upprunalegt hámarksbrúnabil eru skráð í `pabbi-e2-dense/manifest.json`.

Sjö rúmfræðipróf stóðust: fjögur eldri v3.5-próf og þrjú ný próf á yfirborðssýnatöku. Nýju prófin sannreyna punktastaðsetningu/UV á þríhyrningum, varðveislu upprunapunkta, hámarksbil eftir löngum brúnum og mörk fjölda/inntaks.

## Endanlegar stillingar eftir frekari fyrirmæli

Notandi bað um 0,08 mm punktabil og 0,09 mm lagabil og staðfesti að þau skyldu fest. 537.418 punkta útgáfan skal áfram varðveitt og sjálfgefin í skoðaranum; ekki fækka henni í 350.000.

Þetta eru tvö varðveitt viðmið, ekki sami útflutningur: 537.418 útgáfan notar eldri 0,18 mm sýnatöku; föstu nýju bilin mynda annað punktaský úr óbreyttu E2-meshi.

Fyrsta 0,08 mm yfirborðssýnatakan gaf 1.884.449 sýni með Z-lögum. Það var milliskref, ekki einn punktur í hverjum föstum XY-reit. Því var bætt við nákvæmu XYZ-neti og einn punktur geymdur fyrir hvern upptekinn reit. Þétta milliskrefið er varðveitt á diski en fjarlægt úr sýnilega vallistanum til að rugla ekki saman sýnafjölda og föstu punktaneti.

| Núverandi afbrigði | Einstakir punktar | Stilling |
|---|---:|---|
| Pabbi E2 varðveitt þétt viðmið | 537.418 | Fyrri 0,18 mm yfirborðssýnataka |
| Pabbi E2 fast net | 593.235 | 0,08 × 0,08 × 0,09 mm |
| Amma eftir lokamótun andlits | 509.099 | 0,08 × 0,08 × 0,09 mm |
| Hreiðar eftir lokamótun andlits | 373.097 | 0,08 × 0,08 × 0,09 mm |

Lokatalning Pabba er fjórum punktum frá bráðabirgðamælingu á PLY vegna float32-afrúnunar við frumuhálfmörk; ofangreind tala er sannreyndi lokaútflutningurinn úr JSON-hnitunum.

GLB-mesh er óbreytt við punktagerð. Punktar eru færðir á fasta reiti: allt að 0,04 mm í X/Y og 0,045 mm í Z frá þéttu yfirborðssýnunum. Þetta er því skýrt afmörkuð punktanetssýnataka, ekki ný líkamsmótun. RGB/grátónar koma frá fyrsta yfirborðssýni í hverjum reit. Engir samsvarandi reitir eru tvítaldir.

## Lokamótun andlita

`finalize_v35_faces.py` og `face_support_v35.py` mynda nýtt andlitssértækt lokastig. Sjá `FACE-PASS.md` undir varðveittu aðferðinni fyrir stuðning við færri en 468 punkta, sýnileikagögn, maska og núverandi takmörk.

Amma notar eigin HRN framlögun og 465 gildandi landmark-punkta; Hreiðar notar 468 punkta og grófara landmark-fallback. Breytingar utan andlitssvæðis eru sannreyndar núll. Fyrsta HRN-útgáfa gaf andlitsrönd, sem minnkaði með aðlagaðri mýkingu. Augnsvæði/gleraugu og nákvæm líkindi eru áfram rannsóknaratriði.

Nýju GLB og punktaskýin eru í `amma-face-grid/` og `hreidar-face-grid/` undir skoðaranum. Nýjar myndir: `output/research/2026-09-05-v35-transfer/gallery-adaptive/`.

Lokaprófun: **11 próf stóðust**. Þar eru sannreynd gildi punktanets og afmörkuð hlutaandlitsvinnsla auk fyrri rúmfræðiprófa. PLY endurlestur og GLB-varðveisla voru einnig prófuð á raunverulegu afurðunum.
