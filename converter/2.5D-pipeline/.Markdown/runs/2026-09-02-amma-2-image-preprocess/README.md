<!--
File: .Markdown/runs/2026-09-02-amma-2-image-preprocess/README.md
Purpose:
 - Record background-removal candidates for amma-2 before any 2.5D generation.
-->

# Run: `amma-2` image preprocessing

Input: `input-testers/amma-og-afi/amma-2.jpeg`.

Allar tilraunir notuðu 2048 px long-edge Lanczos upscale. Face enhancement var
óvirkt svo source-likeness breyttist ekki.

## Niðurstaða

- **ISNet general — rejected:** hélt síma-overlay og rauðum vegg fyrir ofan hár.
- **BiRefNet portrait + alpha matting — rejected:** rétt silhouette, en of mikið
  hálfgagnsætt background haze fyrir öruggt `mask-from-alpha`.
- **BiRefNet portrait án matting — candidate:** síma-overlay og veggur horfin,
  samfelldar axlir og nytsamlegir hárstrengir. Valin fyrir næsta 2.5D run.

Local preprocess ID: `898dfc7155e0`.

Sjá [visual gallery](artifacts/gallery/README.md).

