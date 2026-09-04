<!--
File: .Markdown/runs/2026-09-02-amma-2-deep-and-approved-v3/README.md
Purpose:
 - Record the 10/20 mm comparison and first self-service approved-v3 portrait run.
-->

# Run: `amma-2` 10 mm, 20 mm og sjálfkeyrt v3

Status: **candidate comparison**.

Sama `BiRefNet portrait` bakgrunnslausa source var notað fyrir þrjár
samanburðarleiðir. Fyrra 10 mm CUDA-runnið var ekki yfirskrifað.

## 20 mm CUDA quality

- Job ID: `1fa37434dc03`.
- MoGe ViT-L 9/9 + face refinement + normal-detail fusion.
- Relief: `136.57 × 296.29 × 20.00 mm`.
- Mesh: 45.350 vertices / 89.578 triangles.
- Physical smooth-flow: 0,03 mm; 0,5% punkta breytt, hámarksbreyting 0,16 mm.

Þetta er sama clean relief-aðferð og fyrri CUDA quality keyrslan en tvöfalt
dýptarsvið. Andlitsútlit og gleraugu halda sér; hliðarsýn sýnir skýrt meiri dýpt.

## Sjálfkeyrt samþykkt v3 ferli

- Job ID: `8a928842c81f`.
- Sjálfvirk Mask R-CNN person-confidence: `0,999375`.
- PARE + official ICON + ECON d-BiNI adaptive fillet.
- Exact source-camera registration: 512/534 inliers, `0,255 px` median villa.
- MoGe ViT-L exact-source depth; gegnsætt source-alpha var virt.
- Depth-skirt: 1.572 boundary edges / 3.144 skirt triangles.
- Final: 91.681 vertices / 178.622 triangles / 3 GLB-lög.
- Heildartími frá queue-start til GLB: um 6 mínútur og 40 sekúndur.

V3 runnið staðfestir að uppskriftin er nú endurkeyranleg á nýja portrait-mynd
án handskrifaðra crop-hnita. Gamla tveggja-manneskju v3 artifactið er áfram
óbreytt viðmið í run history.

![10 mm, 20 mm og v3 gallery](artifacts/gallery/00-contact-sheet.jpg)

Sjá [artifact skrá](ARTIFACTS.md).

