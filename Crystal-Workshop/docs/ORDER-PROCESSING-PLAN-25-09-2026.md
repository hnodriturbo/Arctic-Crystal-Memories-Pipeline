<!-- Current implementation update -->
## Staða 25-09-2026 eftir útfærslu

Staðbundinn grunnur er nú í CCM-Crystal-Production/CCM-Web-Production. Cockpit3D-Files og media-library eru flutt undir CCM-Crystal-Production með sannprófuðum SHA-256 og samhæfingartengingum á gömlu slóðunum. Sjá nýjustu stöðu í ../../..//CCM-Crystal-Production/CCM-Web-Production/docs/STORE-WORKFLOW-25-09-2026.md og VERIFICATION-25-09-2026.md. Allar raunverulegar pantanir eiga uppruna í CCM-Web-Main; staðbundna síðan er framleiðsla/sýningarsalur án greiðslu- eða bókhaldstengingar. Eldri áætlun hér að neðan lýsir einnig óloknum seinni áföngum.

<!--
Purpose: Owner-requested plan for local order production, Windows files and private R2 backup.
Date: 25-09-2026. Planning only; no buckets, application or folder migration created by this document.
-->
# Vinnuferli pantana — staðbundið vinnusvæði og R2-afrit

## Samþykkt markmið

Eigandi valdi heitið CCM-Crystal-Production. Aðalgögn eru á Windows-tölvu eiganda; R2 geymir endurheimtanlegt afrit. Umfangsáætlun er 1–2 þúsund pantanir eftir 1–2 ár, ekki krafa um einstakar skrár yfir 5 GB. Stærð DXF fer eftir punktamagni og útflutningi; mæla skal raunverulegt heildarmagn á pöntun, þar með taldar myndir, PSD, ZIP, senur og DXF, áður en geymsluþörf er áætluð. Ekki bæta multipart-vinnu við fyrstu útgáfu eingöngu vegna heildarstærðar safns.

Vinnuferlissíðan keyrir locally á þessari tölvu. Hún listar staðbundnar skrár beint í gegnum eigin Node-þjón og getur leitað að pöntunum og tengdum skrám í núverandi R2-buckets. Upprunaleg pöntunargögn koma úr vefverslun/SalesCloud; staðbundin framleiðslugögn eru aðalvinnueintak og R2 afrit þeirra. Backup er ekki tvíátta samstilling sem yfirskrifar sjálfkrafa vinnu eiganda.

## Möppur

Rót: D:\Hnodri\Repos\Crystal_Clear_Memories\CCM-Crystal-Production

- CCM-Web-Orders/YYYY/MM/<óbreytt-pöntunarnúmer>/ — ár/mánuður miðast við stofnun pöntunar samkvæmt samþykktri tímabeltisreglu, ekki niðurhalsdag. Gömul ACM-númer haldast.
- SalesCloud-Orders/YYYY/MM/<upprunalegt-auðkenni>/ — sérstakt upprunakerfi kemur í veg fyrir árekstur númera.
- Cockpit3D-Files/ — allt núverandi safn fært heilt hingað; ný söfn mega bætast við.
- Custom-Projects/, Samples-And-Tests/, Showroom-Projects/ — sjálfstæð verkefni utan pantana.
- Photo-Library/, Templates/, Shared-Assets/, Machine-Profiles/, Inbox/, Guides-And-Checklists/ — tillögur úr umræðu, ekki enn stofnaðar.

Innan pöntunar: Order Info, Downloaded ZIPs/Order, Downloaded ZIPs/Cockpit3D, Original Photos, Photo Editing, Processed Photo, Exported DXF, Converted DXF, Other Exports og Production. Cockpit-scene og fylgiskrár má afpakka í rót pöntunar með innri slóðum varðveittum. Margar vörur/senur innan pöntunar þurfa aðskilin Items/<stöðugt-vöruauðkenni>/ vinnusvæði. ZIP-innlestur hafnar slóðaflótta og skrifar aldrei yfir fyrirliggjandi senur í blindni.

## Ný R2-buckets — tillaga, ekki stofnað

| Tillöguheiti | Hlutverk |
|---|---|
| ccm-crystal-production-backup | Einkageymsla afrita alls framleiðsluvinnusvæðisins, með endurheimtanlegum fyrri útgáfum og skráaskrám. |
| ccm-crystal-production-test | Aðskildar tilbúnar prófunarpantanir og endurheimtarpróf; engin raunveruleg viðskiptavinagögn sjálfgefið. |

Staðfesta heitaaðgengi, svæðisval/lögsögu og raunverulegar heimildir við stofnun. Ekki eitt bucket á pöntun eða ár. Tillaga að lykilskipulagi: current/CCM-Web-Orders/2026/09/CCM-2026-00035/..., current/Cockpit3D-Files/..., revisions/<innihaldshash>/<relative-path> og manifests/<run-id>. Manifests skrá hlutfallslega slóð, stærð, SHA-256, útgáfu, tíma og uppruna; þau mega ekki innihalda leyndarmál.

Núverandi customer/order-, Workshop-, Pipeline- og bókhaldsbuckets haldast á sínum stað fyrst. Lesadapterar tengja aðeins heimilaðar pöntunarslóðir og hafa read-only aðgang þar sem við á. Nýja backup-bucket fær afrit af staðbundinni framleiðslu; ekkert núverandi bucket er tæmt eða endurnefnt sjálfkrafa.

Mikilvægt við flutning Cockpit3D-Files: núverandi sync-scene-files.mjs vísar á workspace-root. Uppfæra þarf staðbundna rót og aðrar virkar slóðir samtímis flutningi. Núverandi R2-prefix Cockpit3D-Files/ og eldri model/showroom-tenglar haldast virkir. Nýja backup-geymslan má bætast við án þess að rjúfa Workshop-safnið. Aðskilja síðar rekstrarsafn Workshop frá framleiðsluafritum með skýrri skráningu á hlutverki hvors eintaks.

## Staðbundna vefsvæðið

Tillaga: sérstakt Next.js/JavaScript forrit í kóðamöppu aðskildri frá framleiðslugögnum, með staðbundinni SQLite-skrá fyrir vísitölu og verkstöðu. Endurnýta viðeigandi Workshop-einingar í stað afritunar alls kerfisins. Vísitala styður síuskiptingu eftir uppruna, pöntun, dagsetningu og verkstigi; hún á að endurbyggjast úr skráaskrám og upprunagögnum.

Node-þjónn bundinn við 127.0.0.1, start/stop-flýtileið og skýr stöðuvísun. Hann getur lesið og skrifað aðeins innan stilltrar framleiðslurótar. Síðan er ekki birt á VPS eða netinu sjálfkrafa. Vernda aðgerðaleiðir með innskráningu/setu, Origin/Host-prófun og CSRF-vörn; loopback eitt og sér kemur ekki í veg fyrir óheimilar beiðnir frá öðrum vefsíðum. R2-lyklar eru eingöngu á þjónshlið, utan Git.

Viðmót:
1. Pöntunalisti með leit, uppruna og vinnslustöðu. Vefverslunarupplýsingar lesnar úr afmörkuðu API; R2 eitt og sér er ekki pöntunagagnagrunnur.
2. Pöntunarsíða með staðbundnum skrám og tengdum remote-skrám. Sýna hvaðan hver skrá kemur og hvort hún sé sótt locally.
3. Sækja alla pöntun: ZIP eða bein örugg innlestur í pöntunarmöppu, með manifesti og skýrslu um vantar skrár. Endurtekið niðurhal býr ekki til tvítekna pöntun.
4. Skref: móttekin → myndvinnsla → tilbúin fyrir 3D → Cockpit-sena móttekin → snið/staðsetning → DXF útflutningur → valfrjáls umbreyting → tilbúin í vél → framleidd.
5. Adobe-vinnsla helst staðbundin. Processed Photo er sérstaklega samþykkt fyrir 3D; frummynd varðveitt. Að opna möppu eða skrá notar afmarkaða staðbundna aðgerð, ekki frjálsar shell-skipanir úr vafra.
6. Velja input úr staðbundnu safni eða tilgreindu R2-safni; converter vistar nýtt output hjá sömu pöntun án þess að skipta út upprunalegu DXF.
7. Backup-staða á pöntun: óafritað/bíður/í vinnslu/staðfest/villa og síðasti staðfesti tími. Greina sérstaklega skrár sem breyttust eftir síðasta afrit.

Fyrsta útgáfa þarf ekki að stjórna Cockpit3D-vefnum eða Adobe sjálfvirkt. Innlestur/útflutningur og skrefastaða nægja til að halda ferlinu saman. Rembg er valfrjáls síðar; vélapróf eiganda ákvarða hvort DXF-converter sé yfirleitt nauðsynlegur.

## Afritunarhegðun og umfang

Tengja nýja afritun sem sjálfstætt verk við núverandi run-daily-r2-sync.ps1; villa má ekki fela niðurstöður annarra afritunarverka. Sameiginleg læsing kemur í veg fyrir samtímis daglega og handvirka keyrslu. Byrja með núverandi dagskrá og hnappi Afrita núna; ákveða tíðari keyrslu sérstaklega.

- Vinna úr breytingarvísitölu/röð og staðfesta með hash; ekki hlaða öllum gögnunum aftur upp daglega. Regluleg heildaryfirferð finnur glataðar breytingatilkynningar.
- Skrá sem Adobe/Cockpit er að vista bíður þar til stöðug; stöðugt snapshot er sent. Takmarka samhliða upphleðslu og sýna framvindu.
- Varðveita fyrri innihald áður en ný útgáfa tekur við; nota skilyrt skrif gegn samhliða breytingum. Staðfesta afrit áður en það telst öruggt.
- Eyðing locally eyðir ekki R2-afriti sjálfkrafa. Endurheimt er sér aðgerð og fer sjálfgefið í nýja möppu til samanburðar.
- Loknar pantanir og einstök vinnslugögn eru varanleg gögn. Almenn regla um fjölda DB-afrita á ekki að eyða pöntunum eða einstökum framleiðsluskrám. Stefna um eldri skráaútgáfur þarf sérstaka ákvörðun áður en hreinsun er virkjuð.
- Við rofið net heldur local vinnsla áfram; afrit bíður og er ekki sýnt sem staðfest. Takmarka niðurhal frá R2 við valda pöntun/skrár.

Dæmi um stærð, aðeins reiknidæmi: 2.000 pantanir × 250 MB ≈ 500 GB; 2.000 × 1 GB ≈ 2 TB, áður en eldri útgáfur bætast við. Mæla raunverulegt meðaltal fyrsta hóps pantana og laust diskpláss; ekki áætla kostnað út frá óstaðfestu DXF-meðaltali.

## Framkvæmdarröð og samþykktarpróf

1. Full slóðaúttekt og manifest núverandi safns; stofna rót og flytja Cockpit3D-Files heilt. Uppfæra executable slóðir/skjöl og sannreyna sömu skrár/hashes fyrir og eftir. Dry-run sannar sömu gömlu R2-lykla.
2. Stofna ný einkabuckets og afmarkaða lykla. Prófa með tilbúinni pöntun, síðan staðfesta raunverulegt afrit og endurheimt áður en ferlið er talið virkt.
3. Staðbundið app: lista núverandi skrár, sýna pöntunarsnið og vista verkstöðu; engin skýjaflutningur nauðsynlegur til að nota local gögn.
4. Bæta við read-only pöntunauppflettingu og R2-adapterum með manifesti yfir öll tengd gögn. Prófa gömul ACM- og ný CCM-númer ásamt SalesCloud-auðkennum.
5. Heilt pöntunar-ZIP, Adobe-handoff, Cockpit-innlestur og valfrjálst converter-output.
6. Prófa 2.000 tilbúnar pöntunarfærslur án 2 TB prófunargagna, síðuskiptingu, rofið net, truflaða upphleðslu, opnar vinnsluskrár, árekstra og endurheimt einnar heillar pöntunar.

## Staða og áminning

25-09-2026: áætlun skráð; engin möppufærsla, bucket-stofnun, nýtt app eða afritun nýs bucket framkvæmd. Ein áminning stofnuð í þessari Codex-lotu fyrir 27-09-2026 kl. 17:26 (Atlantic/Reykjavik). Næsta skref er að hefja framkvæmdarröðina með staðbundnu slóðaúttektinni.

## Heimildir fyrir R2-útfærslu

- https://developers.cloudflare.com/r2/buckets/ — bucket og object-key skipulag.
- https://developers.cloudflare.com/r2/api/tokens/ — R2-aðgangslyklar og afmarkaðar heimildir.
- Núverandi scripts/sync-scene-files.mjs og CCM-Web-Workshop/scripts/run-daily-r2-sync.ps1 — raunveruleg staðbundin afritun.
