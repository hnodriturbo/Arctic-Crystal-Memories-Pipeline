<!--
File: reference-gallery/README.md
Purpose:
 - Document the local reference and tester-input collection for the 2.5D pipeline.
 - Keep large/private source assets local while preserving their origin and hashes.
-->

# 2.5D reference gallery

Þessi mappa safnar saman local viðmiðunargögnum sem eru notuð til að þróa og
bera saman 2.5D pipeline-keyrslur.

```text
reference-gallery/
  cockpit-files/     # AC3D/Cockpit projects, scene ZIPs og exports
  original-images/   # original tester inputs afrituð úr ACM-Company
  videos/            # eigin ACM-Company myndbönd
  supplier-videos/   # sýnishorn frá 3dCrystal, HJZ, Kindle og Perfect Laser
  README.md          # tracked lýsing og source-manifest
```

Asset-undirmöppurnar fjórar eru local-only og skilgreindar í root `.gitignore`.
Þannig fara stórar Cockpit-, ZIP-, vídeó- og einkamyndaskrár ekki óvart á GitHub,
en uppbygging og rekjanleiki safnsins helst skjalfestur.

## Original tester inputs

Uppruni afritsins:

```text
D:\Hnodri\Repos\Arctic_Crystal_Memories\ACM-Company\3d_files\Shared_Samples\Original_Images
```

Afritað 2026-09-04. Upprunaskrárnar í `ACM-Company` voru ekki færðar eða
breyttar.

| Skrá | SHA-256 |
| --- | --- |
| `group-photo.jpg` | `802ADA0341BE03FFF64066B2AB814FC4FD64B16EE8748DFF15CE5D8DE6945AA2` |
| `hreidar-upscaled-bg-removed.png` | `5AC16426E691E867EC66037E5F2B9CDF5A66677CC18CB9C1421828F0A4F4D832` |
| `hreidar.jpg` | `97393B1FCBC5A49846BEA93C05C7B9F378E1267E8A95884411C702FC9904C8F5` |
| `my-cat-no-bg-original.png` | `9A9CD9379BB8AD93B4DCF51BAEF3483E64D659ECDEBDEB9C90F93A380F7C1528` |
| `my-cat-no-bg-upscaled-USE-FOR-KEYCHAIN.png` | `74423103E4C6FCF1C8C64E80B23930A09160A068AA10FAD4DDE4CC950AC3FBEE` |
| `Pabbi-Bleikja-Upscaled.png` | `B603EA42362613771B1D2C9F1EF85EB5C2FB6BD92454A0D414FD12B23A3B950F` |
| `Volcanic-Activity-upscaled-nobg.png` | `7C5FA973E09538ACE19000727ABF2859B99B8A441CCB8CFA4E2CCB1D11D65082` |
| `Volcanic-Activity-upscaled.png` | `C0A01B9706C249FD2FCEF10DD96C2B83E4899A15AA6EAECC52FB89EDEC00A3C8` |

## Video reference files

Afritað 2026-09-04 úr `ACM-Company`. Eigin myndbönd fyrirtækisins eru í
`videos/`; utanaðkomandi framleiðenda- og birgjasýnishorn eru aðskilin í
`supplier-videos/`.

| Safn og skrá | SHA-256 |
| --- | --- |
| `videos/crystal-laser-video.mp4` | `36266D916A575AE50252A47ED89C9B7E909550D63DC237BCFA71624C71904F01` |
| `videos/fra-henni-synishorn.mp4` | `59C4BDDCFB2DC52D6D1AE5D4B353699F3376E561FC77E89D9244F56B96C65A6D` |
| `supplier-videos/3dCrystal_Samples/dad-fish-video.mp4` | `618D59609C935B1762F114A3468A1DE4F7762B5377AC4C01586E6A275A7A6CC7` |
| `supplier-videos/HJZ_Laser_Technology_Samples/group-photo-crystal.mp4` | `93B9D3ADDF9159962BF5484AFF7BE20B1AB33ED1A584CA1E1CE8948F148745A7` |
| `supplier-videos/KindleLaser_Samples/dad-fish-crystal.mp4` | `4153E1271F6AD5E7BBA881A9AD5D2830253B83E0CD0D45B2EBAA2520BFA326F6` |
| `supplier-videos/KindleLaser_Samples/group-photo-crystal.mp4` | `BC12FE3C63EBA9D8B4E1199D42BCDA5E66B56F71D9CDA565DF22D83D28260EEE` |
| `supplier-videos/Perfect_Laser_Samples/dad-fish-crystal-video.mp4` | `7084F531BB9333C91572C6C59E947200D7BE5FD33F1B0D62D5C5C24444D0B2E1` |

## Notkunarreglur

1. Tester-keyrslur lesa mynd úr `original-images/` en yfirskrifa hana aldrei.
2. Unnin source-image, maskar, depth og GLB fara í nýja `output/research/`
   run-möppu.
3. Cockpit-skrár eru aðeins lesnar sem external AC3D-viðmið.
4. Hver skjalfest keyrsla skráir source-skrá og SHA-256 svo samanburður sé
   endurtekningarhæfur.
5. Nýjar reference-myndir og samsvarandi Cockpit-project fá lýsandi heiti áður
   en þær eru notaðar sem fast control.
