<!--
File: .Markdown/plans/2026-09-05-RANNSOKN-OG-FRAMKVAEMDAAAETLUN.md
Purpose:
 - Tengja nýjustu v3.5 ákvörðun við opinberar rannsóknir og framkvæmanlegt dagsverk.
 - Skilgreina leið að áreiðanlegu ACM relief-kerfi, eigin líkani og Windows-forriti.
-->

# ACM 2.5D: rannsókn og framkvæmdaáætlun, 5. september 2026

Staða: **ÁÆTLUN — engin ný v3.5 geometry-keyrsla framkvæmd við þessa rannsókn.**

## Niðurstaða og raunhæft markmið

Byggjum eigið myndtengt relief-kerfi með MoGe-grunni, afmörkuðum sérfræðistigum og mælanlegu gæðamati. Næsta verkefni er v3.5 single-surface tilraunin sem var skilgreind í síðustu lotu. Markmið dagsins er endurtekningarhæft GLB á `dad-fish`, síðan `amma-1`, sem stenst fyrirfram ákveðið sjónrænt og tölulegt mat. Ekki er hægt að lofa samþykktu líkani áður en tilraunin hefur verið keyrð.

Ein ljósmynd ákvarðar ekki ótvírætt falda lögun, hlið gleraugna, dýpt hárs eða líkamann undir fötum. Því getur ekkert kerfi tryggt rétt líkan fyrir allar myndir. Hagnýtt gæðamarkmið er hátt hlutfall samþykktra mynda innan skilgreinds umfangs, ásamt áreiðanlegri merkingu á tilvikum sem þurfa yfirferð. Vélrænt confidence-gildi er ekki sjálfkrafa líkindamat á því að geometry sé rétt.

## Hvað var skoðað og hvað gildir nú

- Aðal-README, benchmark, local-workbench README og rannsóknarsafnið í `.Markdown`.
- V3.3/v3.4 niðurstöður, router-aðferðafræði, AC3D-greining og nýjasta v3.5 handoff.
- Vistaðar AC3D- og v3.4-hliðarmyndir: sýnilegur munur er á samfelldu relief-viðmiði og facettuðu HRN-bakhöfði/hálsmörkum v3.4.
- Windows- og Blender-áætlanir frá 4. september.
- Staðbundið skjákort staðfest: RTX 3060 Laptop, 6144 MiB. Keyra líkön í röð og endurnýta vistuð intermediate-gögn; ekki halda öllum sérfræðilíkönum í VRAM samtímis.

Nýjasta [v3.5-áætlunin](2026-09-05-V35-SINGLE-SURFACE-PORTRAIT-WARP.md) ræður þessari tilraun. Eldri router-texti mælir með direct HRN closed-head og eyeglasses-síðan sérstöku gleraugnalagi. Það eru eldri tilraunaleiðir, ekki sjálfgefin loka-geometry v3.5. Aðal-README og gamla MoGe-benchmarkið lýsa ekki allri nýjustu stöðunni. Við innleiðingu þarf að uppfæra virkt profile/router sérstaklega; skjal eitt breytir ekki keyrandi hegðun.

## Rannsóknir sem nýtast

Þetta er markviss samanburður við verkefnið, ekki mæling á því hvaða aðferð sé vinsælust eða tæmandi úttekt á öllum nýjum líkönum.

| Aðferð | Hvað hún leggur til | Ákvörðun fyrir ACM |
| --- | --- | --- |
| MoGe-2 | Almenn myndrúmfræði; ViT-L normal útgáfan gefur einnig yfirborðsnormal | Halda sem fyrsta grunninum; til eru staðbundnar keyrslur og samanburðargögn. |
| Depth Anything 3 | Einmyndar- og fjölmyndar-dýpt; mismunandi sérhæfðar útgáfur | Prófa DA3MONO-LARGE síðar sem einn challenger gegn MoGe við sömu meshing-stillingar. |
| ECON | Klæddir líkamar með body prior, spáðum normals og normal integration | Gagnleg rannsókn á fatnaði; lokaúttak ACM þarf aðeins sýnilegan framflöt. |
| PIFuHD / ICON | Þekktar rannsóknarleiðir fyrir endurgerð klædds fólks | Ekki hefja nýtt uppsetningarverkefni í dag; fyrirliggjandi ICON/ECON niðurstöður nægja til samanburðar. |
| Layered depth inpainting | Aðskilur dýptarfleti og fyllir lit/dýpt þar sem hreyfing myndavélar afhjúpar áður hulin svæði | Gagnleg seinni leið fyrir raunveruleg occlusion-bil; ekki nauðsynlegt að innleiða allt kerfið til að prófa mjóa gleraugnastrekkingu. |

MoGe birtir kóða undir MIT, með DINOv2-hluta undir Apache-2.0. Það eitt staðfestir ekki leyfi allra checkpointa eða þjálfunargagna; skrá skal nákvæma útgáfu og skilmála þess sem er notað. [Opinber MoGe-gögn](https://github.com/microsoft/MoGe).

DA3MONO-LARGE, DA3METRIC-LARGE, BASE og SMALL eru merkt Apache-2.0 í opinberu model-töflunni; DA3-LARGE, GIANT og NESTED eru merkt CC BY-NC 4.0. Velja þarf nákvæman checkpoint, ekki álykta út frá heiti verkefnisins. [Opinber DA3 model-tafla](https://github.com/ByteDance-Seed/Depth-Anything-3#model-cards).

ECON sameinar líkamsgrunn og normal integration til að endurgera meðal annars lausan fatnað. Opinbera leyfið takmarkar notkun við tilgreinda óviðskiptalega notkun. Það verður því ekki sjálfkrafa ókeypis framleiðsluvél fyrir söluvöru ACM. [ECON rannsókn](https://openaccess.thecvf.com/content/CVPR2023/papers/Xiu_ECON_Explicit_Clothed_Humans_Optimized_via_Normal_Integration_CVPR_2023_paper.pdf), [ECON leyfi](https://github.com/YuliangXiu/ECON/blob/master/LICENSE).

Layered depth inpainting býr til staðbundinn lit og dýpt fyrir áður hulin svæði. Það er áætluð fylling, ekki endurheimt á ljósmyndagögnum sem voru aldrei til. [Opinber verkefnissíða](https://shihmengli.github.io/3D-Photo-Inpainting/).

## Framsetningin sem við eigum að prófa

```text
Upprunamynd og varðveitt hnitakerfi
  → mat á sýnilegu innihaldi + aðskilinn foreground/print maski
  → MoGe depth/normals úr upprunamynd með eðlilegum bakgrunni
  → einn myndtengdur foreground-flötur
  → heildarform og halli + afmarkað sýnilegt relief
  → staðbundin gleraugnalyfting + mjó strekking
  → neutral/textured QA + GLB/OBJ úr sömu geometry
  → síðar crystal fit, point cloud og DXF
```

Mikilvægt: halli í AC3D-sýni getur innihaldið bæði listræna dýptarþjöppun og object/camera-transform. Afturkalla þarf skráða scene-transforma og bera líkön saman í sama hnitakerfi áður en hallinn er notaður sem reconstruction-regla. Halli á einni manneskju verður ekki föst regla fyrir allar stellingar.

Fyrsta samsetning getur verið `z = base + low_frequency + local_detail + transition`. Aðskilja tíðnisvið svo base-halli sé ekki talinn aftur í low-frequency depth. Eyða heldur ekki raunverulegri framhalla-stellingu með því að þvinga alla afturábak.

Fyrir normal integration þarf að staðfesta hnitakerfi normals, stefnu z og projection. Normal úr perspective-mynd má ekki nota hugsunarlaust sem orthographic relief-halla eftir dýptarþjöppun. Fyrsta próf notar sléttan flöt, þekktan halla og einfaldan bunguflöt; skörp dýptarmörk mega ekki verða tengibrýr milli handar og bols.

RGB-litur er appearance. Halda luma-displacement óvirku í fyrsta v3.5 samanburði; skuggar og dökkur gleraugnarammi eru ekki sjálfir mæling á dýpt. Síðar má prófa veikt, afmarkað luma-detail sér og hafna því ef það býr til falska áferð.

## Gleraugun og bakfyllingin

Lýsing notandans og vistað AC3D-viðmið styðja að sýnilegi ramminn sé færður fram með mjóu tengisvæði. Þetta segir ekki hvaða net eða kóða AC3D notar.

1. Afmarka sýnilegan ramma með myndgögnum og landmarks; dökk augnlok mega ekki sjálfkrafa verða rammi. Ef sjálfvirk afmörkun bregst má merkja mjóan maska handvirkt fyrir geometry-tilraunina og skrá það skýrt.
2. Færa ramma-vertices fram eftir source-camera stefnu. Undir perspective heldur færsla eftir myndgeisla projection stöðugu; hrein z-færsla með föstu x/y gerir það ekki endilega.
3. Varðveita UV/source-staðsetningu sýnilega rammans. Halda sýnilegu andliti innan linsunnar og forðast upphækkaða linsudiska.
4. Dreifa lyftingu niður í núll yfir mjótt, edge-aware svæði utan rammans. Mæla breidd sem hlutfall af andlitsbreidd og lyftingu í vinnudýpt; engin föst pixel-tala fyrir allar upplausnir.
5. Mæla hallabreytingu, langa þríhyrninga og sjálfsskurði. Aðlaga staðbundna mesh-upplausn áður en meiri lyfting er sett á örmjóan ramma.
6. Bera saman front, ±30°, ±45° og profile. Að framan á ramminn að vera á sama stað; í skámynd á tengingin að vera mjó og án sýnilegra gata eða breiðra teygðra flata.

Eitt heightfield geymir aðeins eina dýpt á hvern myndstað. Það getur því ekki geymt bæði frístandandi ramma og raunverulegt falið andlit á sama myndgeisla. V3.5-strekkingin er meðvituð relief-nálgun. Ef hún stenst ekki samþykkt sjónarhorn er næsta afmarkaða tilraun staðbundinn annar dýptarflötur, ekki stærri extrusion. Einn GLB scene-node einn og sér sannar heldur ekki að undirliggjandi geometry sé eitt heightfield.

## Rétt model-val og mörk sjálfvirkni

| Sýnilegt innihald | Fyrsta leið | Hvenær þarf yfirferð? |
| --- | --- | --- |
| Nærmynd / efri búkur | V3.5 + staðbundið face-depth; engin full-body completion | Óljós andlitsstaða, falinn rammi, klippt hár eða misheppnaður maski. |
| Klædd manneskja, meiri líkami sýnilegur | Sami grunnur; body/cloth prior aðeins í aðskildu, leyfðu samanburðarprofile | Rangt handa/bols-ordering eða prior passar ekki við stellingu. |
| Margir einstaklingar | Instance-maskar, sameiginleg scene-depth og per-person refinement | Skörun, ógreind andlit eða óviss röð fólks. |
| Dýr / hlutir | Almenn depth/normal leið | Aldrei senda í human-head/body leið eingöngu vegna rangrar greiningar. |
| Bakgrunnur varðveittur | Sérstakur background-flötur með sameiginlegri dýptarröð | Ekki normalisera hvert svæði óháð svo röðin snúist við. |

Núverandi `analyze_single_person_2_5d_route.py` notar meðal annars `num_poses=1`; það er ekki almennur multi-person router. Ekki alhæfa samþykkt einsmyndarpróf yfir á hópmyndir.

Skrá per-run: source-hash, preprocessing-transforma, model/checkpoint-hash, route-rök, mask/face evidence, dýptarsvið, viðvörunarsvæði og niðurstöðu QA. Úttak fær stöðuna `CANDIDATE`, `NEEDS_REVIEW` eða `ACCEPTED`; í fyrstu merkir ACCEPTED mannlega yfirferð. Óvissa leiðir í afmarkað A/B eða handvirka leiðréttingu.

Meta router síðar á myndum sem voru ekki notaðar við stillingar. Mæla sérstaklega hlutfall rangra úttaka sem kerfið taldi örugg, auk heildarhlutfalls mynda sem það treysti sér til að afgreiða. Annars getur kerfi virst nákvæmt með því að hafna nánast öllu.

## Dagsverk: áætlaðar vinnulotur, ekki tímalofoð

| Lota | Verk og afhending | Skilyrði til að halda áfram |
| --- | --- | --- |
| 1: 45–75 mín. | Endurnýta útdráttartólin fyrir bæði dad-fish Cockpit-sýnin; staðfesta source og mæla transforms, halla, dýpt og þversnið | Skráð viðmið í sameiginlegu source-rúmi. |
| 2: 90–150 mín. | Nýr v35 research-builder; A mask+base, B +scene-depth, C +face/normal-detail, D +transition | Hver viðbót bætir skilgreindan eiginleika án nýrrar skekkju. |
| 3: 60–90 mín. | Dad-fish front/skásýn/profile gegn báðum AC3D-viðmiðum | Rétt fiskur/hendur/bolur-röð, varðveitt andlit, engir stórir gaddar. |
| 4: 60–120 mín. | Amma-1 með sama grunni; prófa gleraugna-mask/lyftingu/transition sér | Enginn closed-head/hair-shell eða hálsseam; mjó gleraugnatenging. |
| 5: 30–60 mín. | Gallery, mælingar, próf og run-manifest | Skýrt candidate/accepted/rejected mat; engin yfirskrift eldri niðurstaðna. |

Þetta er um 5–8 klst. áætlað þróunarverk ef umhverfið helst virkt. `amma-2`, ný DA3-uppsetning, fjölmennar myndir og Windows-pökkun bíða ef fyrstu loturnar taka lengri tíma. Ef dad-fish bregst fer tíminn í þann galla; ekki framleiða þrjár óstaðfestar niðurstöður í stað einnar greindrar.

Fyrir samanburð skal frysta camera, orientation, hæð og lýsingu. Sýna bæði neutral clay og source-texture: texture getur falið flata geometry. Profile er gagnlegt greiningarsjónarhorn en ekki krafa um raunverulega 360° anatomy.

Við upphaf lotu 1 skal setja mælanleg viðmið áður en v35 er stillt: silhouette-skörun, source-reprojection villa, depth/height, robust z-þversnið og hámarks transition-stærð. Tolerances byggjast á upplausn, skráningarvillu og mun reference-parsins; ekki krefjast að eitt gildi passi nákvæmlega við tvær ólíkar reference-keyrslur. Tvö AC3D-sýni eru ekki tölfræðileg trygging fyrir almennri hegðun.

Próf fyrir builder: rétt depth-stefna; maski fjarlægir ekki lögleg aðskilin svæði; varin occlusion-mörk; núll-stillingar gefa baseline; GLB/OBJ sama geometry; engin NaN eða zero-area triangles. Opinn source-flötur má hafa boundary edges; watertight er ekki sjálfgefin krafa. Að lokum viðeigandi pytest og `git diff --check`.

## Leið að eigin ACM-líkani

Fyrsta eigin afurðin er samhæfður pipeline með eigin samsetningu og QA. Að sameina kóða eða úttök úr ólíkum netum býr ekki sjálfkrafa til nýtt þjálfað líkan; ósamstæð checkpoint er ekki hægt að meðaltalsblanda á merkingarbæran hátt.

1. Safna fyrst litlu, fjölbreyttu regression-safni, t.d. 20–30 myndum, til að uppgötva bilanir. Það er ekki næg þjálfunarsöfnun fyrir almennt portrait-líkan.
2. Vista leiðrétta dýpt, normals, maska, staðbundnar breytingar og samþykkt/hafnað mat. Aðskilja fólk milli train/validation/test svo sama andlit gefi ekki falska alhæfingu.
3. Byggja stærra safn úr eigin/heimiluðum myndum og geometry, ásamt leyfðum synthetic renderum: mismunandi föt, stellingar, gleraugu, ljós og bakgrunnur.
4. Þjálfa fyrst lítið residual/refinement net ofan á frystan backbone. Inntak getur verið RGB + depth + normals + maskar; úttak afmörkuð dýptarleiðrétting og mat á óvissu.
5. Nota tap fyrir depth/normal, silhouette/projection og dýptarröð. Vigta sýnileg gögn hærra en tilbúna bakfyllingu. Staðfesta að netið bæti óséð andlit og fatnað áður en það kemur í stað reglna.
6. Síðari distillation í eitt keyranlegt net er möguleg ef teacher, úttök og gögn heimila þá notkun. Cockpit-viðmið eru samanburðargögn hér, ekki sjálfkrafa leyfilegt þjálfunarsafn. Eigin skrift á wrapper fjarlægir ekki skilmála undirliggjandi líkans.

6 GB kortið hentar núverandi ályktunarprófum í röð. Minni refinement-þjálfun getur verið möguleg með crops og frystum backbone, en VRAM og batch size þarf að mæla. Þjálfun almenns grunnlíkans frá grunni er ekki raunhæft dagsverk.

## Windows-forritið eftir geometry-áfangann

Halda fyrri ákvörðun: Electron + JavaScript/React/Three.js og Python workers. Það nýtir núverandi workbench; Electron hefur aðskilið main/renderer ferlalíkan. [Opinber Electron-skjöl](https://www.electronjs.org/docs/latest/tutorial/process-model).

Fyrsti áfangi: opna GLB, source/clay/normal view, vista/opna `.acmcrystal`, ræsa og stöðva local job og endurheimta eftir villu. Nota takmarkað IPC, renderer án almenns Node-aðgangs og skýra worker-líftímastjórnun.

Annar áfangi: mm-accurate crystal fit, crop og texti; þá mesh-to-pointcloud/DXF með núverandi converter. Preview-punktar mega vera fækkað úrtak en verða merktir þannig. Framleiðsluúttak þarf rétta spacing, mörk og samanburð við samþykkt geometry. GLB er stöðlunarsnið með metraeiningu; skrá og staðfesta umbreytingu úr innri mm-vinnu svo export/import valdi ekki 1000-faldri stærðarvillu.

Blender helst valfrjálst viðgerðar- og QA-rými. Crystal-tónn og punktasýning koma eftir geometry-samþykki og mega ekki fela galla. Engin Windows-shell innleiðing er hluti af rannsókninni sem þessi færsla skráir.

## Næsta beina aðgerð

Framkvæma lotu 1 úr v3.5-planinu: mæla bæði `dad-fish` viðmiðin áður en halli, dýpt eða strekking er kóðuð sem sjálfgefin regla. Varðveita v3.3/v3.4 og upphaflegar myndir. Allt fer fram staðbundið; engin GitHub push.

## Viðbót eftir skýringar notanda: ný mynd, normals og SMPL-X

Notandi samþykkti mjóa strekkingu á sama yfirborði og normal integration fyrir lögun. Valin mynd er `reference-gallery/original-images/Pabbi-Bleikja-Upscaled.png`. Þetta verður næsta v3.5 próf í stað þess að byrja aftur á ömmu-portrettinu. Staðfesta fyrst samsvörun við innbyggðu myndina í dad-fish Cockpit-skránum; upscaling getur breytt stærð og cropi. Ef sama ljósmynd er notuð við stillingu og mat er hún control, ekki sjálfstætt held-out alhæfingarpróf.

### Víðari netrannsókn: val fyrir persónulegar tilraunir

Röð hér er ráðlegging miðað við relief-markmið og 6 GB vélina, ekki staðhæfing um staðbundinn sigur áður en mælingar liggja fyrir.

| Líkan | Mat á gagnsemi | Aðgengi og raunhæf keyrsla |
| --- | --- | --- |
| MoGe-2 ViT-L normals | Fyrsti heildargrunnur fyrir mann, fisk og bakgrunn | Þegar til og áður keyrt á þessari vél. |
| ICON/ECON front normals + integration | Fyrsti samanburður fyrir klæðnað og hendur með líkamsprior | Staðbundin legacy-uppsetning og assets til; rannsóknarnotkun samkvæmt viðeigandi skilmálum. |
| SMPL-X + PIXIE; síðan SMPLify-X | Sérstök forgangstilraun notanda: líkamsstaða, háls, axlir, handleggir og hendur | SMPL-X v1.1 skrár staðfestar á diski; official myndfitting með SMPLify-X er annað verk en að hlaða líkamslíkani. |
| Sapiens2 normal 0.4B | Sterkur nýr kandidat fyrir normals á fólki | Opinber normal-checkpoint til. Þarf sér runtime; ekki staðfest að inference við native upplausn rúmist í 6 GB. |
| DA3MONO-LARGE | Næsti almennur depth-challenger | Apache-2.0 merktur checkpoint; prófa minnisnotkun og sömu relief-samsetningu. |
| DSINE | Sérhæft normal-net til óháðs samanburðar | Opinber kóði/weights; sérleyfi takmarkar meðal annars viðskiptalega vöruþróun. Ekki merkja það almennt MIT/BSD. |
| Lotus normal v1.1 | Annar normal-challenger | Opinberar generative/discriminative útgáfur. Meta dependency- og weight-skilmála og minnisnotkun áður en keyrt er. |
| Lotus-2 | Áhugaverð ný depth/normal rannsókn, en óhentugt fyrsta local-próf hér | Opinber uppsetning krefst að minnsta kosti 40 GB GPU-minnis og FLUX.1-dev aðgangs. |
| SAM 3D Body | Nýr pose/body challenger síðar | Endurgerir parametric líkama/hendur/fætur; er ekki sjálft lausn á ljósmyndartryggum fatnaði, fiski og gleraugum. |

Sapiens2 er ný útgáfa, ekki sama Sapiens 0.3B checkpointið og bilaði áður í Torch 1.12. Opinbera uppsetningin nefnir Python >=3.12 og PyTorch >=2.7; full normal-pipeline þarf meira en backbone-demo. Leyfið er sértækt Sapiens2-leyfi með notkunarskilyrðum, ekki einfalt non-commercial eða Apache merki. [Sapiens2](https://github.com/facebookresearch/sapiens2), [normal-checkpoints](https://github.com/facebookresearch/sapiens2/blob/main/docs/NORMAL.md), [leyfi](https://github.com/facebookresearch/sapiens2/blob/main/LICENSE.md).

DSINE leyfið heimilar tilgreindar rannsóknir en takmarkar einnig rannsóknir til þróunar á vörum til sölu. Persónuleg keyrsla á eigin tölvu og heimil viðskiptanotkun eru ekki sami hluturinn. [DSINE](https://github.com/baegwangbin/DSINE), [leyfi](https://github.com/baegwangbin/DSINE/blob/main/LICENSE).

[Lotus](https://github.com/EnVision-Research/Lotus) gefur sérstakar normal-v1.1 útgáfur. [Lotus-2](https://github.com/EnVision-Research/Lotus-2) skráir 40 GB lágmark fyrir opinberu uppsetninguna; engin óstaðfest low-VRAM leið er lögð til í dag. [SAM 3D Body](https://github.com/facebookresearch/sam-3d-body) er áhugaverður líkamsgrunnur með MHR, sem þarf ekki að blandast sjálfkrafa inn í SMPL-X leiðina.

### Tenglar notanda og ECON runtime-villan

- [SMPLify](https://smplify.is.tue.mpg.de/index.html) er eldri fitting-aðferð fyrir SMPL.
- [SMPL-X](https://smpl-x.is.tue.mpg.de/index.html) er sameinað líkams-, handa- og andlitslíkan; [SMPLify-X](https://github.com/vchoutas/smplify-x) er fitting-kóðinn. Official fitting tekur myndir, OpenPose-keypoints, líkamsgögn og VPoser. Blender-viðbótin er sér leið fyrir skoðun/vinnslu, ekki sjálfvirk ljósmyndalausn ein og sér.
- [ICON á Hugging Face](https://huggingface.co/Yuliang/ICON) er model-safn; síðan segir ekki að virkur inference-provider sé í boði.
- [ECON Space](https://huggingface.co/spaces/Yuliang/ECON) skilaði við skoðun 5. september 2026 runtime error: Open3D import finnur ekki `libGL.so.1`. Þetta er staðfest vöntun á Linux shared library í remote container. Hún sannar ekki CUDA-compiler bilun á Windows og cache-migration skilaboðin ofar í loggnum eru ekki lokavillan. Engin remote viðgerð eða ný myndasending var framkvæmd.

Á diski fundust `models_smplx_v1_1.zip`, útpakkað `SMPLX_NEUTRAL.npz` og eldri `mpips_smplify_public_v2.zip`. Síðasta skráin er ekki SMPLify-X. Staðbundinn `nvcc --version` staðfesti CUDA 11.6.124 í einangraða runtime-inu. Það er compiler-tilvistarmæling, ekki staðfest ný end-to-end ECON keyrsla.

### SMPL-X A/B prófið á Pabba–Bleikju

1. Varðveita source og staðfesta hvaða líkamsliðir sjást; ekki krefjast ósýnilegra fóta.
2. A: v3.5 með MoGe depth/normals og mjórri strekkingu, án SMPL-X.
3. B: fit úr fyrirliggjandi PIXIE + SMPL-X v1.1 leið sem aðskilið QA-líkan. Sýna projected-liði yfir source svo rangt handa-/axlarfit sjáist strax.
4. C: nota samþykkt fit aðeins sem veikan low-frequency prior á sýnilegan búk/hendur; integration notar normal-gögn fyrir sýnileg föt. Fiskurinn heldur sjálfstæðri myndtengdri geometry og má ekki dragast inn í handa/body fit.
5. Bera A og C saman með sama source-camera, meshing og dýptarsviði. C vinnur aðeins ef staða/ordering batnar án taps á andliti, fatnaði eða fiski. Fullt SMPL-X body er ekki loka-relief.
6. Sérstakt SMPLify-X fitting-próf kemur næst þegar OpenPose/VPoser og viðeigandi runtime hafa verið staðfest. Ekki kalla PIXIE-fit SMPLify-X-próf. Gamla locked-HRN seam-planið er ekki default v3.5 verkefni.

SMPL-X leyfið heimilar tilgreinda óviðskiptalega rannsóknar-, náms- og listnotkun; það veitir ekki sjálfkrafa heimild til söluvöru eða þjálfunar á viðskiptalíkani. [Opinberir skilmálar](https://smpl-x.is.tue.mpg.de/modellicense.html). Hér er verið að skipuleggja afmarkað persónulegt rannsóknarpróf og halda uppruna þess sýnilegum.

### Lokastaða aðgangs og næstu niðurhalspakkar

Notandi heimilaði Chrome Work aðgang og innskráningu á SMPL-X og bað um að nota fyrirliggjandi tab group: `econ cuda compiler of 3d work - icon - econ - ceb econ - simplx`. Tvær `cua.getState()` tilraunir og frumstilling varaleiðarinnar `@oai/sky` féllu á tímamörkum. Enginn flipalisti fékkst, engin innskráning var framkvæmd og engin ný model-skrá sótt. Ekki merkja þetta sem aðgangsskort að reikningi; þetta er bilun í stjórntengingu verkfæranna.

Skjáskot notanda staðfesta að nýja Blender 4.5+ viðbótin inniheldur `locked_head` án head bun; v1.1 og SMPL+H eru DLC. Locked-head hefur endurþjálfað shape-space og fær því sér fit; ekki endurnýta v1.1 shape-stika óbreytta.

Þegar vafratenging svarar:

1. Nota þegar opinn SMPL-X download-flipa í Work-prófílnum.
2. Sækja Blender 4.5+ extension með locked-head fyrir skoðun, og locked-head NPZ fyrir sérstakt Python A/B-próf ef ekki til.
3. Endurnýta v1.1 sem er þegar á diski; DLC v1.1 aðeins ef Blender-samanburður þarf það.
4. Staðfesta VPoser v1.0 og `smplx_parts_segm.pkl` fyrir official SMPLify-X leið; ekki velja VPoser v2.0 sjálfkrafa þar sem download-síðan merkir það not-evaluated.
5. Julia, Unity, SMPL+H og EHF dataset eru ekki nauðsynleg fyrir fyrsta Pabbi–Bleikja prófið.

Einfalt beint `import torch, smplx` í econ-py38-cu116 stöðvaðist með `ModuleNotFoundError: smplx`. Það staðfestir að top-level smplx er ekki á sjálfgefnu import-path þessarar keyrslu; það sannar ekki að fyrirliggjandi ECON launcher og vendored model-kóði séu óvirk. Staðfesta import-leið raunverulega launchers áður en pip-pakkar eða compiler eru breytt.
