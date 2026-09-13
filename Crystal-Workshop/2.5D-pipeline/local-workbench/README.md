<!--
File: local-workbench/README.md
Purpose:
 - Explain the local-only four-step image-to-GLB workflow and its data boundaries.
-->

# ACM 2.5D Local Workbench

Þessi síða keyrir eingöngu á `127.0.0.1`. Hún er ekki hluti af production-vefnum
og tengist hvorki R2, Meshy né converter-job queue.

## Keyrsla

```powershell
cd converter/2.5D-pipeline
.\start-local-workbench.ps1
```

Opnaðu síðan `http://localhost:3000`. Ef annar local vefur notar port 3000
velur dev-serverinn næsta lausa port, yfirleitt `http://localhost:3001`.

Gallery-contact-sheetið opnast annaðhvort með **Opna gallery** efst til hægri
eða beint á `http://127.0.0.1:8425/api/gallery/workbench.jpg`.

## Flæði

1. **Mynd og form:** veldu ljósmynd, keyrðu valfrjálst image prep og veldu
   kristal eða `Ekkert form` fyrir full-size output.
2. **Módelval:** veldu run-profile sem passar við CPU/CUDA umhverfið.
3. **Generate:** staðfestu source, profile, output-form og dýpt.
4. **GLB output:** skoðaðu svarthvítt GLB sem flöt eða laser dots; kristall
   birtist aðeins þegar form var valið.

Image prep endurnýtir óbreytt `converter/image-pipeline` sem local worker í
röðinni `enhance → upscale → remove_bg`. Original, unnin PNG og mask eru vistuð
local. Sjálfgefið er 2K upscale + ISNet; face enhancement er óvirkt til að
vernda source-likeness. Fyrir erfiða portrait-kanta má velja BiRefNet portrait.

Stórar skrár fara undir `output/local-workbench/<run-id>/`, sem er git-ignored.
Tracked vefkóðinn geymir hvorki persónulegar myndir né generated GLB.

## Run profiles

- `approved-v3-reference`: keyrir nýja mynd í gegnum PARE + ICON + ECON
  d-BiNI + exact source-camera + MoGe + samþykkta depth-skirt v3 uppskrift.
  Sjálfvirk Mask R-CNN person-greining undirbýr allt að fjóra aðskilda
  einstaklinga og stöðvar downstream skref ef gæðahlið bregst.
- `cuda-preview`: MoGe ViT-B 5/9, svarthvítt tone og 384-grid GLB.
- `cuda-quality`: MoGe ViT-L 9/9, face refinement, normal detail og 512-grid GLB.
- `cuda-quality-deep`: sama og CUDA quality en 20 mm relief fyrir sterkara
  dýptarsvið og beinan samanburð við 10 mm baseline.
- `cpu-safe`: Depth Anything V2 Small fallback án CUDA.

Gamla samþykkta tveggja-manneskju v3 artifactið er alltaf aðgengilegt í
run-history spjaldinu; ný self-service run skrifa það aldrei yfir.
