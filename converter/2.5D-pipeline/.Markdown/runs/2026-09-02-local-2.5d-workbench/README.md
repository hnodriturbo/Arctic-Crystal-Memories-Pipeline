<!--
File: .Markdown/runs/2026-09-02-local-2.5d-workbench/README.md
Purpose:
 - Record the local Leið A → 2.5D generation → Leið B workbench milestone.
-->

# ACM 2.5D local workbench

Status: **candidate interface with accepted v3 reference**.

Þetta er ný, einangruð local-only rannsóknarsíða undir
`converter/2.5D-pipeline/local-workbench`. Hún breytir ekki production ACM
vefnum, Meshy, image enhancer eða converter-job flæðunum.

## Flæði

1. **Leið A** velur mynd, Cockpit3D kristalform og mm stærðir.
2. **2.5D generation** velur keyrslusnið eftir CPU/CUDA umhverfi.
3. **Leið B** hleður GLB inn í valinn gagnsæjan kristal með Three.js og
   OrbitControls fyrir músarsnúning og zoom.

Samþykkta v3 viðmiðið er birt í perceptual svarthvítu án þess að breyta
geometry eða scene nodes: 193.551 vertices í 5 lögum.

![Workbench gallery](artifacts/gallery/00-contact-sheet.jpg)

## Keyrslusnið

- `approved-v3-reference`: opnar samþykkta artifactið án endurkeyrslu.
- `cuda-preview`: hraðpróf með MoGe ViT-B 5/9.
- `cuda-quality`: MoGe ViT-L 9/9, face refinement og normal detail.
- `cpu-safe`: Depth Anything V2 Small fallback án CUDA.

## Gagnamörk

- API bindast eingöngu `127.0.0.1:8425`.
- Myndir og stór outputs fara undir git-ignored
  `output/local-workbench/<run-id>/`.
- Browserinn geymir ekki uploaded myndina.
- Engin R2-, production- eða deploy-tenging er í þessari rannsóknarsíðu.

Sjá [artifact skrá](ARTIFACTS.md).
