<!-- Purpose: Record exercised Workshop R2 workflow and remaining production-quality boundaries. -->
# Workshop R2 workflow verification

Initial tested release: `20260913T211317Z-workshop-r2-flow-b5fe5b9f`.
Follow-up source adds the owner-approved 0.09 mm layer-spacing default.

## Automated checks

- Workshop webpack production build passed locally; Turbopack build passed on VPS.
- Focused ESLint passed.
- R2 scope/auth/download and temporary-directory expiry tests passed.
- Same-origin GLB upload guards, exact bytes and cleanup tests passed.
- Eight reconstruction regressions passed.
- Two absolute-pose override tests passed.
- Three real Blender converter integration tests passed, including textured GLB
  in metres to POINT DXF, black/white UV density, resizing, slicing and formats.
- Point defaults regression: spacing 0.08 mm, minimum distance 0.08 mm,
  layer spacing 0.09 mm, points 0 (spacing-driven).

## Normal signed-in Chrome session on production

- Sidebar no longer numbers chapters; Reconstruct precedes converter.
- Collapse/reopen works. Browser Back restores the workspace.
- DXF selector stays disabled until Cockpit selection.
- Fresh R2 pair: group-photo.cockpit + group-photo-full-aligned.dxf.
- Imported pose reported rotation 0/0/0 and position 0/0/0.
- Reconstruction continued while visiting R2 File Browser and returning with Back.
- Job `20260913-211817-0be326e9`: 721,968 source points, 191,650 vertices,
  380,475 triangles. Photo model rendered in full-width bounded-height preview.
- Saved GLB into original folder, without publishing/replacing a showroom exhibit:
  `Cockpit3D-Files/56789-group-photo/b3c72570-41e7-4e15-bd81-179abea0abc1-20260913-211817-0be326e9.glb`.
- Download link switched to direct R2 download route after saving.
- Send to converter opened the generated temporary GLB, with input unit m.
- At desktop 1362 px and narrow 391 px, document scroll width stayed within viewport.
  Narrow selectors measured about 302 px; viewer about 301 × 547 px.
- Viewport override reset after testing. No local dev server started for this QA.

## Boundaries

This verifies file flow and geometric/export contracts, not manufactured crystal
quality. Photo-driven point sampling is experimental and off by default. Compare
against Cockpit3D-generated point clouds and machine guidance before production.
Physical multi-touch was not exercised by the viewport test.

The separate ACM-Web-Main task owns further showroom design, Admin controls,
original-photo thumbnails/lightbox and intro image selection. Existing public
exhibits were preserved during Workshop testing.
