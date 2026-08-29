<!--
File: converter/web-converter/design-qa.md
Purpose:
 - Record visual QA evidence for production-facing pipeline interface changes.
-->

# Design QA

## Meshy review layout — 2026-08-29

- Reference: the supplied production screenshot with a two-column viewer and truncated artifact names.
- Implementation: the GLB orbit viewer now occupies the full card width above the converter action and artifact list.
- Filename check: every test artifact displayed its complete basename and extension; no truncation or internal file-list scrollbar remained.
- Responsive structure: the result content is one column at every breakpoint, while each artifact row stacks its metadata only when horizontal space becomes constrained.
- Functional check: the GLB loaded in the orbit viewer, the converter action remained visible, and every download link remained present.
- Build checks: `npm run lint` and `npm run build` passed.
- Visual evidence: `design-artifacts/2026-08-29/meshy-review-layout/qa/comparison-reference-and-implementation.png`.

## Crystal workflow — 2026-08-29

- Scope: `Leið A → 2.5D → Leið B` in the local web-converter.
- Model A desktop uses two columns and keeps the composer within the shared content width; tablet and mobile collapse to one column without horizontal overflow.
- Rectangle Mini Presidential uses the approved bevel scale and authoritative `10×10×4 mm` border.
- All 27 local 2D Cockpit templates and six crystal families are available.
- Model B uses a 4:3 frame, a closer camera and a fixed `0.08 mm` preview dot size.
- The 2.5D form exposes point budget, XY/Z distance, final cap, layer distance/count, stagger, toning, density floor, inversion and seed.
- Visual evidence: `design-artifacts/2026-08-29/crystal-flow/qa/comparison-reference-and-model-a.png` and the adjacent desktop/mobile captures.

final result: passed
