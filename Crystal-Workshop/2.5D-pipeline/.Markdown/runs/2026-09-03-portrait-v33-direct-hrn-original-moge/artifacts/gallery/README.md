# Amma-2 portrait v3.3 — direct HRN + original-source MoGe

Status: **CANDIDATE**

![Contact sheet](00-contact-sheet.jpg)

## Notes

- Candidate, not accepted: the neck-to-garment seam still needs a dedicated stitch/remesh pass.
- BiRefNet produces the binary silhouette only; MoGe-2 ViT-L produces metric depth.
- MoGe was run on the original opaque 2K image and normalized only within the subject mask.
- HRN native topology owns the face and complete shallow head; PARE/ICON/ECON are not used for this close portrait.

## BiRefNet semantic mask (not depth)

![BiRefNet semantic mask (not depth)](01-birefnet-semantic-mask-not-depth.png)

## MoGe subject depth near-is-white

![MoGe subject depth near-is-white](02-moge-subject-depth-near-is-white.png)

## MoGe subject depth far-is-white

![MoGe subject depth far-is-white](03-moge-subject-depth-far-is-white.png)

## Native HRN registered texture

![Native HRN registered texture](04-native-hrn-registered-texture.png)

## Clean candidate front

![Clean candidate front](05-clean-candidate-front.png)

## Clean candidate 30 degrees

![Clean candidate 30 degrees](06-clean-candidate-30-degrees.png)

## Clean candidate profile

![Clean candidate profile](07-clean-candidate-profile.png)

## Rejected experimental hair fringe

![Rejected experimental hair fringe](08-rejected-experimental-hair-fringe.png)
