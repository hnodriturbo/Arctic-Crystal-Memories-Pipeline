<!--
Tilgangur: Varðveita niðurstöður staðbundinna v3.5 prófana og leiðréttingar notanda.
-->

# Pabbi-Bleikja: v3.5 samanburður

## Viðmið notanda

- **Leiðrétting eftir myndasamanburð: samþykkti grunnurinn er E-face**, þ.e. `06-face-variants/D-transition/relief.glb`. Notandi valdi seinni myndina í AC3D/E-samanburðinum sérstaklega. F og G eru ekki samþykktur grunnur, þótt hlutar þeirra þættu vel gerðir. Fyrri túlkun aðstoðarmanns á samþykki F var röng.
- Ný ósk: smá viðbótarstrekking við alla enda, laga koll og endurvinna andlit, með líkama og fiski úr E áfram.
- Mynd: `reference-gallery/original-images/Pabbi-Bleikja-Upscaled.png`.
- Höfuðið þarf sléttan koll, ekki upphleypta háráferð.
- Notandi segir strekkingu við hendur og fisk einnig koma fram í AC3D-módelinu. Hún er því ekki sjálfkrafa höfnunarástæða og skal haldast í kollprófuninni.
- Þetta er tilraun með samsetta vinnslukeðju, ekki nýþjálfað tauganet.

## Keyrslur og niðurstöður

Allar afurðir eru undir `output/research/2026-09-05-portrait-v35-single-surface/`.

1. Tvær dad-fish Cockpit-skrár voru lesnar án breytinga. Viðmið voru skráð og annað afmarkað við forgrunn upprunamyndarinnar með SIFT. Viðmiðið gaf z/y-halla -0.09377 fyrir forgrunninn. Bakgrunnurinn breytir þeirri mælingu verulega.
2. MoGe-2 gaf grunnlögun og normalvigra. A–D prófuðu grunn, dýpt, normal integration og mjóa jaðaraðlögun. Andlit varð of flatt.
3. MoGe-andlitsútskurður bætti andlitið í E, en lögunin var enn ófullnægjandi við enni og fisk.
4. PIXIE með SMPL-X, 50 aðlögunarskref, ICON-normalar og ECON d-BiNI gáfu F. Þetta var raunveruleg staðbundin keyrsla; opinber SMPLify-X var ekki keyrður. Einungis framsvæði var flutt út.
5. F var skráð aftur í myndhnit upprunamyndar: 134/144 SIFT-inliers, miðgildi skráningarvillu 0.318 pixlar. Módel: `pabbi-bleikja/08-icon-source/person_01_source_camera.glb`.
6. G er afmarkað kollpróf af F: `pabbi-bleikja/09-smooth-scalp/person_01_smooth_scalp.glb`. Það sléttar aðeins Z með nágrannavegnu meðaltali innan handstillts svæðis ofan augna og eyrna. Þetta er ekki sjálfvirk skallagreining. XY og þríhyrningar haldast; hendur og fiskur breytast ekki.

## Staðfesting á G

- 78.976 hnútar og 155.796 þríhyrningar.
- 1.665 hnútar breyttust. Hámarksbreyting 2.675 mm við 80 mm sýnilega hæð.
- Sannreynt með assertions: allir hnútar utan svæðis óbreyttir, XY óbreytt, GLB endurlesið með sömu þríhyrningum og hnitum innan float-villu.
- Þar sem XY er varðveitt lagar þessi prófun ekki sagtennur í sjálfri útlínunni. Hún sléttar dýpt kollsins.
- Fyrri fjögur rúmfræðipróf í `tests/test_portrait_v35.py` höfðu staðist.
- Samanburðarmyndir: `gallery-icon/` fyrir F og `gallery-scalp/` fyrir G, sömu myndavélar og sýnileg hæð 80 mm.

## Endurkeyrsla kollprófs

Keyrið úr rót 2.5D-pipeline með nýrri úttaksmöppu:

```powershell
& .venv/Scripts/python.exe code/research/smooth_v35_scalp.py --mesh output/research/2026-09-05-portrait-v35-single-surface/pabbi-bleikja/08-icon-source/person_01_source_camera.glb --output-dir output/research/2026-09-05-portrait-v35-single-surface/pabbi-bleikja/09-smooth-scalp-repeat
```

Rannsóknaráætlun: `.Markdown/plans/2026-09-05-RANNSOKN-OG-FRAMKVAEMDAAAETLUN.md`.
F/G er varðveitt til samanburðar; eftir skýrt val notanda er E grunnurinn fyrir næstu vinnu. Ekki yfirfæra handstillta afmörkun á aðrar myndir án greiningar.

## E1 og E2 eftir staðfestingu notanda

Keyrsla: `code/research/refine_v35_accepted_e.py`.
Úttak: `pabbi-bleikja/10-accepted-e-refinement/` undir sömu afurðarót.

- E1-edge bætir allt að 1 mm afturfærslu í Z innan 5 reita viðbótarbands við alla maskajaðra. Fyrri 0,6 mm jaðaraðlögun E er áfram til staðar. Ekki er búið til lokað bak eða falin líffærafræði.
- E2-head-edge bætir staðbundinni höfuðlögun frá áður reiknuðum ICON/d-BiNI framfleti. Höfuðdýptin er löguð að E með skala 0,7883 og hliðrun; kollur er sléttaður, andlitsatriði varðveitt úr gjafafletinum. Þetta er endursamsetning höfuðs úr fyrirliggjandi keyrslu, ekki ný tauganetskeyrsla.
- Höfuðsvæðið er handstillt fyrir þessa mynd. 33 reitir innan þess notuðu næsta gilda ICON-hnit þar sem línuleg brúun náði ekki til.
- Mesta höfuðbreyting: 2,005 mm. Heildardýpt E1: 20,083 mm; E2: 20,737 mm, við sýnilega hæð 75,618 mm.
- Bæði GLB voru endurlesin: sömu XY-hnit og sömu 251.183 þríhyrningar og E. Engir þríhyrningar með núllflatarmál eða ómanifold-brúnir. Dýpt líkamans utan jaðarbands og höfuðsvæðis er nákvæmlega óbreytt.
- SHA256 á varðveittum E-dýptargrunni: `37a96fb69a97a2dc780b58e8c3d48ec6fc57f243ac39cdf91a44f415eaeafaaa`.
- Myndir í `gallery-accepted-e/` nota sömu myndavélar og fyrri samanburður. Skoðað +30° og +90° á E2: ennisrönd E horfin, líkams- og fisklögun E varðveitt. Rifflur/sagtennur við jaðra enn sýnilegar og meira áberandi eftir viðbótarstrekkingu. Útlínur XY voru ekki sléttaðar.
- Staða: prófafbrigði til sjónræns mats notanda, **ekki samþykkt lokamódel**.
