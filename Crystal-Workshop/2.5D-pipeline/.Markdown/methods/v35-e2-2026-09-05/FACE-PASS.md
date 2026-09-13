<!--
Purpose: Specify the adaptive final face stage and distinguish verified capabilities from open work.
-->

# Andlitsyfirferð í lok mótunar

Kóði: `face_support_v35.py` og `finalize_v35_faces.py` í `code/research/`.

Þetta er nýtt forritað lokastig sem nýtir fyrirliggjandi HRN/MediaPipe niðurstöður. Það er ekki nýþjálfað tauganet og ekki staðfest lausn fyrir öll andlit.

## Hvað stigið gerir

1. Les hvert greint andlit sérstaklega. Tekur við breytilegum fjölda XYZ-punkta með lyklunum `landmarks_3d`, `dense_landmarks` eða `dense_landmarks_468`.
2. Fjarlægir ógild hnit, punkta utan myndar og punkta utan foreground-alpha. Ef `landmark_visibility` eða `landmark_confidence` fylgja er gildi undir 0,5 útilokað.
3. Reiknar vinnslusvæði og mýkingarbreidd út frá þessu andliti. Þarf a.m.k. sex ólínulega punkta; ófullnægjandi stuðningur skilur grunnandlitið óbreytt og skilar ástæðu.
4. Nýtir source-skráða HRN-framfleti þegar þeir eru fyrir þessa mynd og skráning stenst mörkin: ≥15 inliers og miðgildisvilla ≤2 px. Flytur ekki inn lokaðan haus, hár eða háls.
5. Án HRN er notuð grófari lögun úr þrívíðu landmark-dýptarmati. Það er merkt sérstaklega; það hefur ekki sömu smáatriði og sérstök andlitsendurbygging.
6. Samræmir staðsetningu og halla við mörkin, dregur úr breiðum mismun milli flata og færir staðbundin form augna, nefs og munns inn í sama myndnet. Hámarksbreyting er bundin.
7. XY, UV, þríhyrningar og allir punktar utan andlitssvæðisins eru sannreyndir óbreyttir. Punktaský er búið til eftir þetta stig með 0,08/0,09 mm stillingunni.

## Hulin andlit og sýnileiki

468 spáðir MediaPipe-punktar þýða ekki að 468 punktar sjáist á ljósmyndinni. Núverandi gögn hafa ekki áreiðanlegt sýnileikamat fyrir hvern punkt; niðurstöður merkja það `needs_occlusion_review`.

Stigið getur tekið við sýnileikaskorum eða `--visibility-mask` í upprunalegri myndstærð. Svört svæði í þeim maska eru varin, t.d. hönd eða hlutur fyrir framan andlit. Án slíkra gagna greinir kerfið **ekki sjálfkrafa allar skyggingar/hulanir**. Andlitsrammi er afmarkaður út frá tiltækum punktum; convex hull eitt og sér greinir ekki holur eða hluti innan andlits.

Augna-/nefasamhverfa er skráð sem einfalt sjónarhornsvísbending, ekki mæld yaw-gráða eða sjálfvirkur sönnunargagn um sýnileika. Frekari myndbundin skyggingargreining þarf að bæta við áður en kalla má þetta fullsjálfvirkt fyrir hvers konar andlit.

## Prófað

- Amma-1: 468 innlesnir, 465 gildandi punktar eftir alpha/hnitaskoðun; eigin HRN framlögun, SIFT miðgildisvilla 1,139 px.
- Hreiðar: 468 gildandi punktar, landmark-fallback þar sem eigin HRN framflötur var ekki tilbúinn. Þetta er minni endurbót en dedicated HRN/normal-vinnsla gæti gefið.
- Fyrsta beina HRN-blöndun gaf sýnilega rönd við andlitsmörk. Mýkri andlitssértæk blöndun minnkaði röndina; augnsvæði/gleraugu og nákvæm líkindi þurfa áfram sjónrænt mat. Ekki merkja sem samþykkt lokagæði án mats notanda.
- Tíu afmörkuð próf stóðust, þar á meðal hlutaandlit með sex gildum punktum, útilokaðir punktar og höfnun þegar stuðningur dugar ekki.

## Endurkeyrsla

`run_v35_transfer.py` lýkur nú hverri nýrri keyrslu með `05-final-face` og `06-point-review`. Það tekur valfrjáls `--hrn-assets`, `--hrn-registration` og `--visibility-mask`. Nýjar keyrslur varðveita dýptarbil sjálfgefið; eldri klipping er aðeins samanburðarkostur.

Varðveitta Pabba E2 og 537.418 punkta viðmiðið voru ekki endurmótuð með þessu stigi.
