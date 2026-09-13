<!--
Purpose: Preserve the owner's approved direction for a future crystal demo.
Status: Planning notes only; implementation waits for approval of the first relief.
-->

# Future crystal demo — owner direction, 2026-09-13

## Gate

Finish and obtain explicit owner approval of the current Amma-og-Afi model first.
Do not begin ACM-Web-Main implementation before that approval. The converter remains
the production and refinement tool for all GLBs.

## Intended result

- Produce and refine approximately 3–4 relief models in Cockpit Reconstruct.
- Store approved GLBs in R2; the eventual demo on ACM-Web-Main loads these assets.
- Render the relief inside a crystal using Three.js.
- Select the appropriate crystal template from the existing Cockpit3D crystal system.
- Support manually entered crystal width, height and depth, drawing the outer
  crystal to those dimensions around the relief.
- Keep model production in the converter and presentation in the public website.

## Future design considerations, not implemented

Record each approved asset's R2 key, template identifier and physical dimensions.
Keep units explicit: source/STL millimetres versus GLB metres. Determine framing,
clearance, orientation and crystal material together with the owner during the
demo task. Reuse the existing crystal/template system after inspecting it; do not
create a second conflicting dimensions catalogue.

No R2 uploads, deployment or ACM-Web-Main changes are authorized by this planning
note alone. The owner explicitly deferred the demo structure until model approval.
