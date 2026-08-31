<!--
File: converter/2.5D-pipeline/TODO-later.md
Purpose:
 - Preserve explicitly deferred ACM 2.5D and Blender workflow ideas without
   interrupting the current face-refinement implementation.
-->

# TODO later

## Cockpit3D-like web and Blender workflow

Deferred at the user's request on 2026-08-30. Do not begin this section until
the native 2.5D depth and face-refinement pipeline is stable and visually
approved.

- Inspect the newest ACM-Web-Main admin **Leið 1** and **Leið 2** work.
- Reuse the already extracted Cockpit3D crystal templates in Blender and the
  ACM Scene Composer.
- Build a similar guided flow around the native 2.5D pipeline:
  1. choose portrait, landscape or unconstrained orientation;
  2. upload, crop, position and scale the photograph;
  3. run native 2.5D conversion and mandatory face refinement;
  4. inspect and approve the completed relief model;
  5. open the approved model in the chosen crystal template;
  6. download/export only after approval.
- Write a practical Blender training manual covering model trimming, layout,
  crystal-template loading, inspection and final export.
- Keep the web flow visually close to Cockpit3D's useful workflow without
  copying its proprietary implementation.
