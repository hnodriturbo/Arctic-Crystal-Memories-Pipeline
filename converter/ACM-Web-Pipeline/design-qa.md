<!--
File: converter/ACM-Web-Pipeline/design-qa.md
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

## Production converter workflow — 2026-09-02

- Scope: retain the existing `Image → Meshy → Converter` operator sequence.
- 2.5D research is not exposed or imported by the production web application.
- Converter remains its own third-step page rather than introducing another workflow.
- The page accepts uploaded, handed-off, and R2 model inputs; it lists local and durable R2 conversion results.
- Common model outputs, millimetre sizing, axis slicing, printer DXF, and multi-output ZIP are rendered from the existing operation catalogue.
- Functional evidence: lint, production build, headless Blender conversion tests, and the converter API SSE flow passed.

final result: passed
