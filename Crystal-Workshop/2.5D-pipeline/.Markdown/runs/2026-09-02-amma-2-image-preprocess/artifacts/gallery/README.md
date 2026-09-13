# amma-2 image preprocessing A/B

Status: **CANDIDATE**

![Contact sheet](00-contact-sheet.jpg)

## Notes

- ISNet kept the phone overlay and red wall above the head.
- BiRefNet with alpha matting removed the object but left translucent background haze.
- BiRefNet portrait without alpha matting is the selected input for the next 2.5D run.
- No face enhancement was applied; likeness remains source-derived.

## Original

![Original](01-original.jpeg)

## ISNet cutout - rejected

![ISNet cutout - rejected](02-isnet-cutout-rejected.png)

## ISNet mask - rejected

![ISNet mask - rejected](03-isnet-mask-rejected.png)

## BiRefNet alpha matting - rejected haze

![BiRefNet alpha matting - rejected haze](04-birefnet-alpha-matting-rejected-haze.png)

## BiRefNet alpha mask

![BiRefNet alpha mask](05-birefnet-alpha-mask.png)

## BiRefNet portrait cutout - candidate

![BiRefNet portrait cutout - candidate](06-birefnet-portrait-cutout-candidate.png)

## BiRefNet portrait mask - candidate

![BiRefNet portrait mask - candidate](07-birefnet-portrait-mask-candidate.png)
