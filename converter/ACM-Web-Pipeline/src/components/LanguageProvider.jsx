"use client";

/*
 * ═══════════════════════════════════════════════════════════════
 * Language Provider
 * ═══════════════════════════════════════════════════════════════
 * Path: src/components/LanguageProvider.jsx
 * Purpose: Provide persistent Icelandic/English UI language selection and
 *          one shared translation catalogue for every pipeline.
 */

import { createContext, useContext, useEffect, useState } from "react";

export const LANGUAGE_STORAGE_KEY = "acm-pipeline-language";

const IS = {
  "Operator workspace": "Vinnusvæði stjórnanda",
  "Pipeline navigation": "Valmynd vinnslulína",
  "Close pipeline navigation": "Loka valmynd vinnslulína",
  "Open pipeline navigation": "Opna valmynd vinnslulína",
  "Image pipeline": "Myndavinnsla",
  "Photograph in · prepared PNG out": "Ljósmynd inn · tilbúin PNG út",
  "Inputs and library": "Inntök og myndasafn",
  "Prepare images": "Undirbúa myndir",
  "Meshy pipeline": "Meshy-vinnsla",
  "Images or text in · 2D/3D assets out": "Myndir eða texti inn · 2D/3D gögn út",
  "Image to 3D": "Mynd í þrívídd",
  "Multi-Image to 3D": "Margar myndir í þrívídd",
  "Text to 3D": "Texti í þrívídd",
  "Text to Image": "Texti í mynd",
  "Image to Image": "Mynd í mynd",
  "Jobs and review": "Verk og yfirferð",
  "Pipeline converter": "Skráabreytir",
  "3D/CAD in · DXF, OBJ and point clouds out": "3D/CAD inn · DXF, OBJ og punktaský út",
  "Convert and export": "Umbreyta og flytja út",
  System: "Kerfi",
  "What this machine can actually do": "Raunveruleg geta vélarinnar",
  "Python environments": "Python-umhverfi",
  "Upload source photographs and see the files available to the image and Meshy pipelines.":
    "Hladdu upp frummyndum og skoðaðu skrár sem myndavinnslan og Meshy geta notað.",
  "Restore, upscale and remove the background, then send the chosen result directly to Meshy.":
    "Endurbættu, stækkaðu og fjarlægðu bakgrunn; sendu síðan valda niðurstöðu beint í Meshy.",
  "Upload a separate Meshy image or use an image-pipeline result to generate a 3D mesh.":
    "Hladdu upp sérstakri Meshy-mynd eða notaðu niðurstöðu myndavinnslunnar til að búa til þrívítt mesh.",
  "Use several angles of the same subject to generate one more complete mesh.":
    "Notaðu nokkur sjónarhorn af sama myndefni til að búa til fullkomnara mesh.",
  "Generate a mesh directly from a written description.":
    "Búðu til mesh beint úr skriflegri lýsingu.",
  "No usable photograph? Have Meshy draw the reference instead.":
    "Engin nothæf ljósmynd? Láttu Meshy teikna viðmiðsmynd.",
  "Reference photos plus a prompt — re-light, re-frame, or clean up.":
    "Viðmiðsmyndir og fyrirmæli — breyttu lýsingu, ramma eða hreinsaðu myndina.",
  "Review every Meshy result, download its files, or hand an OBJ directly to the converter.":
    "Farðu yfir allar Meshy-niðurstöður, sæktu skrár eða sendu OBJ beint í skráabreytinn.",
  "Create printer DXF from Meshy OBJ, convert CAD/DXF to OBJ, or inspect and repair point clouds.":
    "Búðu til prent-DXF úr Meshy OBJ, breyttu CAD/DXF í OBJ eða skoðaðu og lagfærðu punktaský.",
  "Which engines are installed, and what 'auto' resolves to here.":
    "Hvaða vinnsluvélar eru uppsettar og hvað „auto“ velur á þessari vél.",
  "Not included in the current Meshy subscription.": "Ekki innifalið í núverandi Meshy-áskrift.",
  locked: "læst",

  Auto: "Sjálfvirkt",
  Light: "Ljóst",
  Dark: "Dökkt",
  "Colour theme": "Litastilling",
  Language: "Tungumál",
  Icelandic: "Íslenska",
  English: "Enska",

  Review: "Yfirferð",
  "Drag to orbit, scroll to zoom. Check the back of the head and the sides before sending anything to the converter — one view of a photograph is all Meshy had to work from.":
    "Dragðu til að snúa og skrunaðu til að þysja. Skoðaðu bakhlið höfuðs og hliðar áður en nokkuð fer í skráabreytinn — Meshy hafði aðeins eitt sjónarhorn ljósmyndarinnar.",
  All: "Öll",
  Finished: "Lokið",
  Failed: "Mistókst",
  refresh: "endurnýja",
  succeeded: "tókst",
  failed: "mistókst",
  "Nothing generated yet.": "Ekkert hefur verið búið til enn.",
  "Send to converter →": "Senda í skráabreyti →",
  download: "sækja",
  "Use for 3D →": "Nota í þrívídd →",
  "Review the local GLB, then keep or discard this complete project.":
    "Skoðaðu local GLB-skrána og veldu síðan að geyma eða henda öllu projectinu.",
  "This project failed. Discard its local files before starting another 3D job.":
    "Projectið mistókst. Hentu local skránum áður en ný þrívíddarkeyrsla hefst.",
  "Keep in R2 and clear VPS": "Geyma í R2 og hreinsa VPS",
  "Discard this project": "Henda þessu projecti",
  "Archiving and verifying…": "Vista og sannreyna…",
  "Discarding…": "Eyði…",
  "R2 archive": "R2-geymsla",
  "awaiting review decision": "bíður ákvörðunar eftir yfirferð",
  "No GLB in this job, so there is nothing to turn. Add glb to the download formats to get one.":
    "Engin GLB-skrá fylgir þessu verki og því er ekkert snúanlegt preview. GLB er skylduskrá í nýja ferlinu.",
  "No OBJ in this job. The converter reads OBJ and mesh DXF only.":
    "Engin OBJ-skrá fylgir verkinu. Skráabreytirinn les aðeins OBJ og mesh-DXF.",

  "Crystal Converter": "Kristal-skráabreytir",
  "Upload a model, choose what happens to it, download something the SSLE engraver reads.":
    "Veldu 3D-skrá, stilltu vinnsluna og búðu til skrá sem SSLE-grafarinn les.",
  "Meshy projects · R2 source library": "Meshy-project · R2 frumgagnasafn",
  "Finished Meshy models live in private R2 storage; choosing one copies a working file into the converter.":
    "Geymd Meshy-model eru í private R2; valin skrá er afrituð tímabundið inn í skráabreytinn.",
  "refresh library": "endurnýja safn",
  "refreshing…": "endurnýja…",
  "Reading the Meshy archive…": "Les Meshy-safnið…",
  "R2 is not available on this server.": "R2 er ekki tiltækt á þessum þjóni.",
  "No OBJ or DXF models are archived yet.": "Engin OBJ- eða DXF-model hafa verið vistuð enn.",
  "Durable R2 converter outputs": "Varanleg converter-úttök í R2",
  "No converter results are archived yet.": "Engar converter-niðurstöður hafa verið vistaðar enn.",
  "Source file": "Frumskrá",
  "Click to choose a file": "Smelltu til að velja skrá",
  "Stored in private R2 first, then streamed into the converter; large OBJ files bypass the website proxy limit":
    "Vistað fyrst í private R2 og síðan streymt í skráabreytinn; stórar OBJ-skrár fara fram hjá stærðarmörkum vefþjónsins",
  Operation: "Aðgerð",
  Options: "Stillingar",
  Results: "Niðurstöður",
  "Run conversion": "Keyra umbreytingu",
  "Converting…": "Umbreyti…",
  Stop: "Stöðva",
  "Nothing in output/ yet.": "Ekkert er komið í output/ enn.",
  "Physical blank": "Stærð kristals",
  "Effective margin": "Virk spássía",
  "Usable volume": "Nýtanlegt rúmmál",
  "Depth reference": "Dýptarviðmið",
  "on every side": "á öllum hliðum",
  "continuous depth (no layer spacing)": "samfelld dýpt (ekkert layer spacing)",
  "up to about": "allt að um",
  "planes across usable depth": "plön yfir nýtanlega dýpt",
  "or pick one of": "eða veldu eina af",
  "files already in input/": "skrám sem eru þegar í input/",
  "wrong type for this operation": "rangt skráarsnið fyrir þessa aðgerð",
  "Large meshes take a few minutes; progress appears below as it happens.":
    "Stór mesh geta tekið nokkrar mínútur; framvindan birtist hér fyrir neðan.",
  "Output appears here once a conversion starts.":
    "Úttak birtist hér þegar umbreyting hefst.",
  running: "í vinnslu",
  idle: "bíður",
  lines: "línur",
  "Point spacing controls XY density. Depth-dot spacing thins Z before layering; 0 reuses XY. Layer spacing then defines the final focus planes. “UV” below means mesh texture coordinates—not laser wavelength—so DXF output is equally suitable for a green-beam engraver.":
    "Point spacing stjórnar XY-þéttleika. Depth dot spacing grisjar Z fyrir lagskiptingu; 0 endurnotar XY. Layer spacing skilgreinir síðan fókusplönin. „UV“ merkir texture coordinates í meshinu, ekki bylgjulengd lasers; DXF hentar því jafnt fyrir green-beam grafara.",

  "Convert, resize, and slice a 3D model": "Umbreyta, stærðarsetja og sneiða 3D-model",
  "Reads common Blender-compatible 3D files, reports their geometry, sizes them in millimetres, optionally slices them, and writes every selected format. Multiple formats are also packaged as ZIP.":
    "Les algeng 3D-snið sem Blender styður, greinir formið, stærðarsetur í millimetrum, sneiðir valfrjálst og skrifar öll valin snið. Mörg snið fara einnig saman í ZIP.",
  "Model dimensions": "Mál models",
  "Declare source units and size the result in millimetres.": "Veldu einingu frumskrár og stærðarsettu niðurstöðuna í millimetrum.",
  "Source coordinate unit": "Hnitaeining frumskrár",
  "Coordinates are converted to millimetres before sizing or slicing.": "Hnitum er breytt í millimetra áður en modelið er stærðarsett eða sneitt.",
  "Millimetres (mm)": "Millimetrar (mm)",
  "Centimetres (cm)": "Sentimetrar (cm)",
  "Metres (m)": "Metrar (m)",
  "Inches (in)": "Tommur (in)",
  "Maximum model width (mm)": "Hámarksbreidd models (mm)",
  "Maximum model height (mm)": "Hámarkshæð models (mm)",
  "Maximum model depth (mm)": "Hámarksdýpt models (mm)",
  "0 keeps the converted source width. Multiple limits preserve aspect ratio and use the tightest fit.":
    "0 heldur umbreyttri frumbreidd. Mörg mörk varðveita hlutföll og þrengsta markið ræður.",
  "Placement before slicing": "Staðsetning fyrir sneiðingu",
  "Center at origin": "Miðja við núllpunkt",
  "Center X/Y and place bottom at Z=0": "Miðja X/Y og setja botn við Z=0",
  "Keep imported coordinates": "Halda innfluttum hnitum",
  "Slice model": "Sneiða model",
  "Keep geometry between optional millimetre boundaries on one axis.": "Halda formi milli valfrjálsra millimetramarka á einum ás.",
  "Slice axis": "Sneiðingarás",
  "Do not slice": "Ekki sneiða",
  "X · width": "X · breidd",
  "Y · height": "Y · hæð",
  "Z · depth": "Z · dýpt",
  "Keep from coordinate (mm)": "Halda frá hniti (mm)",
  "Keep through coordinate (mm)": "Halda að hniti (mm)",
  "Blank leaves this side open. Coordinates are measured after unit conversion, fitting, and placement.":
    "Tómt gildi skilur þessa hlið opna. Hnit eru mæld eftir einingabreytingu, stærðarsetningu og staðsetningu.",
  "Cap cut surfaces": "Loka skurðflötum",
  "Fills closed cut loops when the source topology allows it.": "Fyllir lokaðar skurðlykkjur þegar topology frumskrár leyfir.",
  "Output formats": "Úttakssnið",
  "DXF uses ACM's SSLE POINT-cloud writer. Two or more selections also produce one ZIP.":
    "DXF notar SSLE POINT-punktaskýsskrifara ACM. Tvö eða fleiri val búa einnig til eina ZIP-skrá.",
  "DXF sampling target (0 = spacing)": "DXF sampling-markmið (0 = spacing)",
  "Only used when DXF is selected.": "Aðeins notað þegar DXF er valið.",
  "DXF point spacing (mm)": "DXF punktabil (mm)",
  "DXF minimum dot distance (mm)": "DXF lágmarks punktabil (mm)",
  "DXF depth-dot spacing (mm)": "DXF dýptarpunktabil (mm)",
  "DXF final point cap": "DXF hámarksfjöldi lokapunkta",
  "DXF sampling seed": "DXF sampling-seed",

  "Crystal size": "Kristalstærð",
  "Aspect ratio is always preserved.": "Hlutföll modelsins haldast alltaf óbreytt.",
  "Crystal blank": "Kristall",
  "Width x height x depth in mm.": "Breidd × hæð × dýpt í millimetrum.",
  "Custom width (mm)": "Sérsniðin breidd (mm)",
  "Custom height (mm)": "Sérsniðin hæð (mm)",
  "Custom depth (mm)": "Sérsniðin dýpt (mm)",
  "Custom border (mm)": "Sérsniðin spássía (mm)",
  "Crystal margin (mm)": "Bil frá kristalbrún (mm)",
  "0 keeps the blank above.": "0 notar valda kristalstærð.",
  "Usually the limit for a full 3D subject. Raise it to get the model bigger.":
    "Dýptin takmarkar venjulega fullt 3D-myndefni. Hækkaðu gildið til að stækka modelið.",
  "Unengraved margin on every side. 0 keeps the blank preset; 0.1 mm is allowed for a precisely calibrated laser.":
    "Ógrafið bil á öllum hliðum. 0 notar sjálfgefna spássíu kristalsins; 0,1 mm er leyft fyrir nákvæmlega kvarðaðan laser.",
  "Unengraved margin on every side. The standard is 1 mm; enter any value down to 0.1 mm.":
    "Ógrafið bil frá hverri kristalbrún. Staðalgildið er 1 mm; hægt er að skrifa inn hvaða gildi sem er niður í 0,1 mm.",
  "Dot density": "Punktaþéttleiki",
  "How many laser dots, and how close together.": "Fjöldi laserpunkta og bil þeirra á milli.",
  "Sampling target (0 = spacing)": "Sampling-markmið (0 = spacing)",
  "Point spacing (XY, mm)": "Point spacing (XY, mm)",
  "Minimum dot distance (mm)": "Lágmarks punktabil (mm)",
  "Depth dot spacing before layers (mm)": "Dýptarpunktabil fyrir lög (mm)",
  "Final point cap": "Hámarksfjöldi lokapunkta",
  "Depth layers": "Dýptarlög",
  "Snap depth onto planes the laser focuses on.": "Festa dýptarpunkta á fókusplön lasersins.",
  "Fixed plane count (alternative)": "Fastur fjöldi plana (valkostur)",
  "Layer spacing (mm)": "Layer spacing (mm)",
  Stagger: "Hliðrun laga",
  "Offsets alternate layers so dots do not stack into visible columns.":
    "Hliðrar lögum til skiptis svo punktar staflist ekki í sýnilegar súlur.",
  "Texture toning": "Texture-tónun",
  "Drive dot density from image brightness.": "Láta birtu myndar stjórna punktaþéttleika.",
  "Texture image": "Texture-mynd",
  "Lookup mode": "Texture-vörpun",
  "Mesh UV coordinates": "UV-hnit meshsins",
  "Front projection": "Vörpun að framan",
  Toning: "Tónun",
  "Density floor": "Lágmarksþéttleiki",
  "Invert brightness": "Snúa við birtu",
  Orientation: "Snúningur og stefna",
  "Which way the subject sits in the glass.": "Hvernig myndefnið snýr inni í kristalnum.",
  "Keep upright": "Halda uppréttu",
  "Axis facing the viewer": "Ás sem snýr að áhorfanda",
  "Auto-orient for biggest fit": "Sjálfvirk stefna fyrir stærstu fyllingu",
  "Swap Y and Z": "Víxla Y og Z",
  "Mirror axes": "Spegla ása",
  Output: "Úttak",
  Seed: "Seed",
  "Also write XYZ preview": "Skrifa einnig XYZ-preview",
  "The seed fixes pseudo-random surface sampling. The same input, settings and seed reproduce the same cloud; changing any of them can change the dots.":
    "Seed festir slembiúrtak yfirborðsins. Sama inntak, sömu stillingar og sama seed endurskapa sama punktaský; breyting á einhverju þeirra getur breytt punktunum.",
  "UV means the mesh's 2D texture coordinates, not an ultraviolet laser. It is unrelated to UV versus green-beam engraving.":
    "UV merkir tvívíð texture-hnit meshsins, ekki ultraviolet laser. Þetta tengist ekki UV- eða green-beam gröfun.",

  Photo: "Ljósmynd",
  "Reference images": "Viðmiðsmyndir",
  "Click to add images": "Smelltu til að bæta við myndum",
  "Or run the image pipeline first and send the result here":
    "Eða keyrðu myndavinnsluna fyrst og sendu niðurstöðuna hingað",
  remove: "fjarlægja",
  "Generate 3D": "Búa til þrívídd",
  "Generating…": "Bý til…",
  "This run": "Þessi keyrsla",
  "open jobs and review →": "opna verk og yfirferð →",
  "Download formats": "Niðurhalssnið",
  "Chooses which files Meshy generates and this server downloads. GLB is mandatory for the local review gate; OBJ enables direct converter handoff.":
    "Velur skrárnar sem Meshy býr til. GLB er skylduskrá fyrir local yfirferð; OBJ gerir beina sendingu í skráabreytinn mögulega.",
  "Generate texture": "Búa til texture",
  "Texture resolution": "Texture-upplausn",
  "Texture prompt": "Texture-fyrirmæli",
  "PBR maps": "PBR-kort",
  "Transparent thumbnail": "Gegnsæ thumbnail-mynd",
  "Four-view thumbnails": "Thumbnail-myndir frá fjórum hliðum",
  Origin: "Uppruni",
  "Scale the model to that size": "Skala modelið í þessa stærð",
  "Generation model": "Meshy-model",
  "Which Meshy engine builds the geometry.": "Hvaða Meshy-vél býr til formið.",
  "Mesh and topology": "Mesh og topology",
  "What the surface is made of.": "Hvernig yfirborðið er byggt upp.",
  Texture: "Texture",
  "Leave off for engraving - the glass has no colour.": "Hafðu slökkt fyrir gröfun — kristallinn notar ekki liti.",
  "Crystal fit": "Aðlögun að kristal",
  "Which blank this model is destined for.": "Fyrir hvaða kristal modelið er ætlað.",
  "AI model": "AI-model",
  "Model type": "Gerð models",
  "Smart Topology face count": "Fjöldi flata í Smart Topology",
  "Ultra mode": "Ultra-hamur",
  "Meshy image enhancement": "Myndabæting Meshy",
  "Remove baked lighting": "Fjarlægja fasta lýsingu",
  "Force pose": "Þvinga líkamsstöðu",
  "Content moderation": "Efnisöryggisskoðun",
  Remesh: "Endurbyggja mesh",
  Topology: "Topology",
  "Target polycount": "Markfjöldi flata",
  "Adaptive decimation": "Aðlagandi fækkun flata",
  "Keep the pre-remesh model too": "Geyma einnig modelið fyrir remesh",
  "Image model": "Myndamodel",
  "Aspect ratio": "Myndhlutföll",
  "Generate multiple views": "Búa til mörg sjónarhorn",
  "Transparent background": "Gegnsær bakgrunnur",
  Prompt: "Fyrirmæli",
  "Chooses the standard geometry engine. Latest currently resolves to Meshy 7; Smart Topology selects Meshy T2 automatically instead.":
    "Velur hefðbundna form-vél. Latest notar nú Meshy 7; Smart Topology velur Meshy T2 sjálfvirkt.",
  "Standard preserves maximum surface detail. Smart Topology automatically uses Meshy T2, costs 5 credits, and caps the directly generated mesh at 15,000 faces.":
    "Standard varðveitir mest yfirborðssmáatriði. Smart Topology notar Meshy T2, kostar 5 credits og takmarkar mesh við 15.000 fleti.",
  "Meshy T2 generates directly at this approximate face count. Higher preserves more form; 15,000 is the API maximum.":
    "Meshy T2 býr modelið til með um það bil þessum fjölda flata. Hærra gildi varðveitir meira form; 15.000 er hámark API.",
  "Meshy 7 only. Adds 5 credits and generates finer geometry natively; it improves surfaces, not texture resolution.":
    "Aðeins Meshy 7. Bætir við 5 credits og býr til nákvæmara form; þetta bætir yfirborð en ekki texture-upplausn.",
  "Lets Meshy optimize the reference before reconstruction. It is independent of the local image pipeline; turn it off only when exact source appearance matters.":
    "Leyfir Meshy að bæta viðmiðsmyndina fyrir þrívíddarvinnslu. Þetta er óháð local myndavinnslunni; slökktu aðeins þegar nákvæmt útlit frummyndar skiptir máli.",
  "Meshy 6 texture option that removes highlights and shadows from base colour. It does not repair geometry and is omitted for other models.":
    "Meshy 6 texture-stilling sem fjarlægir glampa og skugga úr grunnlit. Hún lagar ekki form og er ekki notuð með öðrum modelum.",
  "Constrains a full-body character to an A- or T-pose. Leave off for portraits, busts, pets, objects and buildings.":
    "Setur heila manneskju í A- eða T-stöðu. Hafðu slökkt fyrir portrett, brjóstmyndir, dýr, hluti og byggingar.",
  "Screens image and prompt content before generation. Keep it on for customer material; a rejected task does not proceed.":
    "Öryggisskoðar mynd og fyrirmæli fyrir vinnslu. Hafðu kveikt fyrir efni viðskiptavina; hafnað verk er ekki keyrt.",
  "Rebuilds and decimates the surface. Leave it off for crystal engraving so the converter receives Meshy's raw high-density geometry.":
    "Endurbyggir og fækkar flötum. Hafðu slökkt fyrir kristalgröfun svo skráabreytirinn fái óskert háþéttniform Meshy.",
  "Triangle creates a decimated triangle mesh; quad creates a quad-dominant mesh. This applies only when Remesh is enabled.":
    "Triangle býr til fækkað þríhyrningsmesh; quad býr til að mestu fjórhyrningsmesh. Gildir aðeins þegar Remesh er virkt.",
  "Approximate face count after remeshing, from 100 to 300,000. Higher preserves more detail but creates larger files and slower conversion.":
    "Áætlaður fjöldi flata eftir remesh, 100–300.000. Hærra gildi varðveitir meiri smáatriði en býr til stærri skrár og hægari umbreytingu.",
  "Adaptive decimation overrides Target polycount: 1 is ultra, 2 high, 3 medium and 4 low. Leave off to use an exact target.":
    "Adaptive decimation tekur yfir Target polycount: 1 er ultra, 2 hátt, 3 miðlungs og 4 lágt. Hafðu slökkt til að nota nákvæmt markgildi.",
  "Also returns the dense GLB from before remeshing, so the reduced result can be compared or bypassed. Applies only when Remesh is on.":
    "Skilar einnig þéttu GLB fyrir remesh svo hægt sé að bera saman eða sleppa fækkuðu útgáfunni. Gildir aðeins þegar Remesh er virkt.",
  "Adds a colour-texture pass (normally 10 credits). Crystal engraving reads geometry only, so leave this off unless you also need a rendered model.":
    "Bætir við litatexture-vinnslu (venjulega 10 credits). Kristalgröfun les aðeins form, svo hafðu slökkt nema einnig þurfi litað render.",
  "Controls base-colour texture size. 2K and 4K cost the same; 8K adds 5 credits and substantially increases downloads.":
    "Stjórnar stærð grunnlita-texture. 2K og 4K kosta jafnt; 8K bætir við 5 credits og stækkar niðurhal verulega.",
  "Adds metallic, roughness and normal maps (and emission where supported). These improve rendered materials but have no effect in engraved glass.":
    "Bætir við metallic-, roughness- og normal-kortum. Þau bæta renderuð efni en hafa engin áhrif í gröfnum kristal.",
  "Up to 600 characters describing colours and materials. It guides only the texture pass and does not change the generated shape.":
    "Allt að 600 stafir um liti og efni. Þetta stýrir aðeins texture-vinnslu og breytir ekki formi modelsins.",
  "Recorded on the job and pre-selected when you hand the model to the converter.":
    "Vistað með verkinu og forvalið þegar modelið er sent í skráabreytinn.",
  "Physical crystal height. Meshy subtracts the top and bottom margin before resizing; 0 uses the selected blank.":
    "Raunhæð kristalsins. Meshy dregur margin efst og neðst frá áður en modelið er skalað; 0 notar valda kristalstærð.",
  "Physical crystal width carried into the converter. Set 0 to use the selected blank.":
    "Raunbreidd kristalsins sem flyst yfir í skráabreytinn. 0 notar valda kristalstærð.",
  "Physical crystal depth carried into the converter. Depth usually limits a full 3D subject.":
    "Raundýpt kristalsins sem flyst yfir í skráabreytinn. Dýptin takmarkar yfirleitt stærð fulls þrívídds myndefnis.",
  "Carried over to the converter. Depth is what usually limits a full 3D subject.":
    "Flyst yfir í skráabreytinn. Dýptin takmarkar yfirleitt stærð fulls þrívídds myndefnis.",
  "+5 credits for a Meshy remesh that resizes the export to real millimetres. Off is fine - the converter refits it anyway - but it makes the downloaded file measure correctly in Blender or a slicer.":
    "+5 credits fyrir Meshy-remesh sem skalar útflutning í raunmillimetra. Slökkt er í lagi því skráabreytirinn aðlagar modelið; virkt gefur rétta stærð í Blender eða slicer.",
  "+5 credits. Meshy resizes by usable height only; the converter later enforces the same margin across width, height and depth.":
    "+5 credits. Meshy skalar aðeins eftir nýtanlegri hæð; skráabreytirinn tryggir síðan sama margin á breidd, hæð og dýpt.",
  "Requests a transparent preview image when Meshy supports it. This affects only the thumbnail, never the model geometry.":
    "Biður um gegnsæja preview-mynd þegar Meshy styður það. Hefur aðeins áhrif á thumbnail, aldrei form modelsins.",
  "Requests front, right, back and left review renders. They are the quickest way to spot missing or collapsed geometry before conversion.":
    "Biður um preview að framan, hægri, aftan og vinstri. Fljótlegasta leiðin til að finna vantað eða fallið form fyrir umbreytingu.",
  "Centre is what the point-cloud sampler expects - it fits a model about its own middle.":
    "Center er það sem punktaskýsvinnslan gerir ráð fyrir; modelið er aðlagað um miðju sína.",
  "Returns three consistent angles and charges for three images. They can be reviewed individually; combining them into one mesh requires Multi-Image to 3D access.":
    "Skilar þremur samræmdum sjónarhornum og rukkar fyrir þrjár myndir. Hægt er að skoða þær hverja fyrir sig; sameining í eitt mesh krefst Multi-Image to 3D aðgangs.",
  "Returns an RGBA PNG with transparency. This is usually the cleanest direct input for Image to 3D.":
    "Skilar RGBA PNG með gegnsæi. Þetta er yfirleitt hreinasta beina inntakið fyrir Image to 3D.",
  "3D model to printable DXF": "3D-model í prentanlegt DXF",
  "Samples an OBJ or triangle-mesh DXF into the evenly spaced POINT cloud the SSLE engraver reads, fitted to a crystal blank.":
    "Umbreytir OBJ eða triangle-mesh DXF í jafndreift POINT-punktaský fyrir SSLE-grafarann og aðlagar það að völdum kristal.",
  "Repair or re-tune a point DXF": "Laga eða endurstilla punkta-DXF",
  "Re-emits an existing POINT cloud in the exact format the printer accepts. Use it when a Cockpit3D export will not load, or to change size, dot spacing and depth layers without going back to the model.":
    "Endurskrifar POINT-punktaský á nákvæmu sniði grafarans. Notað þegar Cockpit3D-skrá opnast ekki eða til að breyta stærð, punktabili og dýptarlögum án upprunalegs models.",
  "Point DXF to standards-compliant DXF": "Punkta-DXF í staðlað DXF",
  "Rebuilds a bare Cockpit3D POINT export as a full AC1015 file with tables, blocks and real handles, so any CAD tool opens it.":
    "Endurbyggir einfalt Cockpit3D POINT-úttak sem fulla AC1015-skrá með töflum, blokkum og handles svo CAD-forrit geti opnað hana.",
  "Point DXF to mesh or cloud": "Punkta-DXF í mesh eða punktaský",
  "Turns a POINT-cloud DXF back into XYZ, PLY, OBJ or STL. The reverse direction, for viewing and 3D printing.":
    "Breytir POINT-DXF aftur í XYZ, PLY, OBJ eða STL fyrir skoðun og þrívíddarprentun.",
  "Cockpit3D CAD to mesh or cloud": "Cockpit3D CAD í mesh eða punktaský",
  "Reads the proprietary CIRasterizer text format and exports XYZ, PLY, OBJ or STL.":
    "Les CIRasterizer textasnið Cockpit3D og flytur út XYZ, PLY, OBJ eða STL.",
  "Inspect a file": "Skoða skrá",
  "Reports what a file actually contains before you convert it. Changes nothing on disk.":
    "Sýnir raunverulegt innihald skráar fyrir umbreytingu án þess að breyta neinu.",
  "Optional sampling target before thinning. Keep 0 for Cockpit3D-style density controlled by point spacing.":
    "Valfrjálst sampling-markmið fyrir grisjun. Hafðu 0 fyrir Cockpit3D-líkan þéttleika sem point spacing stjórnar.",
  "Main Cockpit3D-style density control. 0.08 mm is the reference baseline; smaller values create more dots.":
    "Aðalstýring punktaþéttleika eins og í Cockpit3D. 0,08 mm er viðmið; lægra gildi býr til fleiri punkta.",
  "Safety floor between XY dots. Start at the 0.08 mm Cockpit3D reference and validate any smaller distance on the green-beam machine.":
    "Öryggislágmark milli XY-punkta. Byrjaðu á 0,08 mm Cockpit3D-viðmiði og prófaðu minna bil sérstaklega á green-beam vélinni.",
  "Grid-thinning distance along Z before points are snapped to final layers. 0 reuses XY point spacing; this is not layer spacing.":
    "Grisjunarbil eftir Z áður en punktar festast á lokaplön. 0 endurnotar XY point spacing; þetta er ekki layer spacing.",
  "Cockpit3D reference guardrail. 500,000 limits oversized clouds after spacing and layers; 0 removes the cap.":
    "Cockpit3D-öryggisviðmið. 500.000 takmarkar of stór punktaský eftir spacing og lög; 0 fjarlægir hámarkið.",
  "Alternative to layer spacing. 0 lets the millimetre spacing below decide the number of depth planes.":
    "Valkostur við layer spacing. 0 lætur millimetrabilið hér fyrir neðan ákvarða fjölda dýptarplana.",
  "Cockpit3D layer-spacing equivalent. 0.08 mm is the reference baseline and overrides the fixed plane count.":
    "Samsvarar layer spacing í Cockpit3D. 0,08 mm er viðmið og tekur fram yfir fastan fjölda plana.",
  "auto uses GFPGAN on CUDA and Pillow on CPU. Choose GFPGAN explicitly for slower CPU AI restoration.":
    "auto notar GFPGAN með CUDA en Pillow á CPU. Veldu GFPGAN sérstaklega fyrir hægari AI-andlitsviðgerð á CPU.",
  "auto uses Real-ESRGAN on CUDA and Lanczos on CPU. Choose Real-ESRGAN explicitly for slower CPU AI upscaling.":
    "auto notar Real-ESRGAN með CUDA en Lanczos á CPU. Veldu Real-ESRGAN sérstaklega fyrir hægari AI-stækkun á CPU.",
  Uploaded: "Upphlaðið",
  "Waiting in the image pipeline's input folder.": "Bíður í input-möppu myndavinnslunnar.",
  Cleaned: "Unnið",
  "What the Image pipeline produced. Every stage is kept, so pick the one that looks right.":
    "Niðurstöður myndavinnslunnar. Öll millistig eru geymd svo hægt sé að velja bestu útgáfuna.",
  "Ready for Meshy": "Tilbúið fyrir Meshy",
  "Meshy generation screens pick from this dedicated folder.":
    "Meshy-vinnsluskjáir velja myndir úr þessari sérstöku möppu.",
};

const LanguageContext = createContext(null);

function initialLocale() {
  if (typeof document === "undefined") return "is";
  return document.documentElement.lang === "en" ? "en" : "is";
}

export function LanguageProvider({ children }) {
  const [locale, setLocale] = useState(initialLocale);

  useEffect(() => {
    document.documentElement.lang = locale;
    try {
      window.localStorage.setItem(LANGUAGE_STORAGE_KEY, locale);
    } catch {
      // The language still works for this session when persistence is blocked.
    }
  }, [locale]);

  const t = (text) => (locale === "is" ? IS[text] || text : text);
  return (
    <LanguageContext.Provider value={{ locale, setLocale, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const value = useContext(LanguageContext);
  if (!value) throw new Error("useLanguage must be used inside LanguageProvider.");
  return value;
}
