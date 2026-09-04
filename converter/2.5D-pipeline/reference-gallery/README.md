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
  cockpit-files/    # AC3D/Cockpit projects, scene ZIPs og exports
  original-images/  # original tester inputs afrituð úr ACM-Company
  README.md         # tracked lýsing og source-manifest
```

`cockpit-files/` og `original-images/` eru local-only og skilgreind í root
`.gitignore`. Þannig fara stórar Cockpit-, ZIP- og einkamyndaskrár ekki óvart á
GitHub, en uppbygging og rekjanleiki safnsins helst skjalfestur.

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

## Notkunarreglur

1. Tester-keyrslur lesa mynd úr `original-images/` en yfirskrifa hana aldrei.
2. Unnin source-image, maskar, depth og GLB fara í nýja `output/research/`
   run-möppu.
3. Cockpit-skrár eru aðeins lesnar sem external AC3D-viðmið.
4. Hver skjalfest keyrsla skráir source-skrá og SHA-256 svo samanburður sé
   endurtekningarhæfur.
5. Nýjar reference-myndir og samsvarandi Cockpit-project fá lýsandi heiti áður
   en þær eru notaðar sem fast control.
