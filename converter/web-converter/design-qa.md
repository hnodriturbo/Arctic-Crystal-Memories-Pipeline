<!--
File: design-qa.md
Purpose:
 - Record visual and interaction QA for the local crystal workflow.
-->

# Crystal workflow design QA

Date: 2026-08-29  
Scope: `Leið A → 2.5D → Leið B` in the local web-converter.

## Evidence

- Approved bevel reference: `design-artifacts/2026-08-29/crystal-flow/qa/reference-approved-bevel.png`
- Model A desktop: `design-artifacts/2026-08-29/crystal-flow/qa/implementation-model-a-desktop.png`
- Combined comparison: `design-artifacts/2026-08-29/crystal-flow/qa/comparison-reference-and-model-a.png`
- Model A mobile: `design-artifacts/2026-08-29/crystal-flow/qa/implementation-model-a-mobile.png`
- 2.5D settings: `design-artifacts/2026-08-29/crystal-flow/qa/implementation-2.5d-settings.png`
- Model B desktop entry state: `design-artifacts/2026-08-29/crystal-flow/qa/implementation-model-b-desktop.png`

## Checks

- Desktop Model A uses two columns and keeps the full composer within the shared content width.
- Tablet/mobile collapses to one column without horizontal overflow.
- Rectangle Mini Presidential uses the approved 0.64 visual bevel scale and authoritative `10×10×4 mm` border.
- All 27 local 2D Cockpit templates and six families are available.
- The three workflow entries are adjacent in the sidebar and remain independently accessible.
- Model B uses a 4:3 frame, a closer camera and a fixed `0.08 mm` preview dot size.
- The 2.5D form exposes point budget, XY/Z distance, final cap, layer distance/count, stagger, toning, density floor, inversion and seed.
- Keyboard-visible labels and native controls are present for upload, select, numeric and boolean inputs.
- Production build and ESLint both pass.

## Notes

The full-page screenshot stitcher duplicated a portion of the mobile canvas during one capture. The accessibility snapshot contains one composer and one action row, and the non-full-page mobile evidence confirms the live layout has no duplicate DOM content.

Final result: passed
