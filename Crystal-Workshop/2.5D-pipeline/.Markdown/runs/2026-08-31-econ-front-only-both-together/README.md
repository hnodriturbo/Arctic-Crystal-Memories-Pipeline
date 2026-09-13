<!--
File: .Markdown/runs/2026-08-31-econ-front-only-both-together/README.md
Purpose:
 - Preserve the exact successful ECON front-only experiment and its conclusions.
-->

# Run: ECON front-only — AI-enhanced `both_together`

## Niðurstaða

Þetta er fyrsta staðfesta baseline-ið sem nálgast AC3D-markmiðið: þétt source-facing 2.5D mannslíkan með sannfærandi höfði, andlitsdýpt, hálsi, líkama, fatnaði og höndum. Engin ACM geometry/refinement pipeline var keyrð ofan á það.

## Input

```text
input-testers/amma-og-afi/for3d/both_together.png
```

- Tegund: AI-enhanced `both_together`, tveir einstaklingar.
- Stærð: 1,939,663 bytes.
- SHA-256: `A39599AF402AAB74726C9276BAC593A44039408050E00EDE934E267AA8F0F2F1`

## Model stack sem var raunverulega notað

1. PIXIE + SMPL-X: person detection, pose/camera og body/head/hand prior.
2. Official ECON `normal.ckpt`: front/back clothed-human normals.
3. d-BiNI: normal integration.
4. Sérstakt `--front-only`: export á `F_trimesh` áður en 360° IF-Net/Poisson completion hefst.

Ekki notað: Sapiens, HRN, MoGe-2, IF-Net, Poisson fusion, ACM Composer eða eldri depth-relief refinement.

## Stillingar

| Stilling | Gildi |
|---|---:|
| Multi-person | já (`-multi`) |
| SMPL-X fit iterations | 50 |
| `force_smpl_optim` í final run | `False` — endurnýtti staðfest cache |
| `bni.k` | 4 |
| `bni.lambda1` | `1e-4` |
| `bni.boundary_consist` | `1e-6` |
| `bni.thickness` | `0.02` |
| `bni.hps_type` | `pixie` |
| `bni.texture_src` | `image` |
| Sapiens | `False` |

## Keyrsluskipun

Frá pipeline-rót, með absolute paths leystum af PowerShell launcher:

```powershell
.\code\research\run_econ_windows.ps1 `
  -cfg .\code\research\econ-front-rtx3060-6gb.yaml `
  -in_dir .\output\research\econ-front-only\both-together-ai-enhanced\input `
  -out_dir .\output\research\econ-front-only\both-together-ai-enhanced\result `
  -multi -novis --front-only
```

Athugið: upstream ECON skilgreinir `-multi` með `store_false`; flaggið þýðir því í reynd `single=False`.

## Geometry output

| OBJ | Vertices | Þríhyrningar | Extents XYZ | Z/depth span | SHA-256 |
|---|---:|---:|---|---:|---|
| `both_together_0_F.obj` | 66,131 | 128,435 | `0.945312, 1.804688, 0.915539` | 0.915539 | `4FD51B64BE4091EA8F1B1A8E93EAB6A560CF04E31DBAA60693DC84588B9F6183` |
| `both_together_1_F.obj` | 60,516 | 117,663 | `0.914062, 1.613281, 0.847476` | 0.847476 | `764DA306AB946F56E8F49E00269B040FB4AE2CC4A3227CAD5EAA7F575CBB7173` |

Samtals: **126,647 vertices** og **246,098 þríhyrningar**. Bæði OBJ innihalda source-derived vertex colors.

## Blender QA, ekki geometry-refinement

`render_econ_front_qa.py` flytur OBJ inn með ECON Y-up -> Blender Z-up conversion, smooth shading og neutral gray material. Þar sem ECON normalizes-ar hvert person crop sér eru mesh sett tímabundið í `x=-0.48` og `x=+0.48`; konan fær `z=+0.01`. Þetta endurskapar vinstri/hægri röð til sjónmats en er ekki full source-camera registration.

- Front camera: `(0, -5, 0.25)`, orthographic scale `2.55`.
- 45° camera: `(3.6, -3.6, 0.25)`.
- Target: `(0, 0, 0.25)`.
- Render: Blender EEVEE, 1600x1000, AgX Medium High Contrast.
- Blender: 5.1.2.

## Mat

Sterkt:

- recognizable andlit og persónueinkenni;
- raunveruleg dýpt í enni, nefi, kinnum, höku og hálsi;
- bolur, ermar, hendur og fellingar í fatnaði;
- geometry er nægilega þétt til að prófa áframhaldandi 2.5D fusion.

Óleyst:

- eðlileg occlusion-bil milli handleggs/handar og bols eiga að haldast; aðeins örfínar óæskilegar seam-línur/mask-göt við sum mörk þarf að laga;
- hár, gleraugu og fín identity-smáatriði;
- source-camera fusion á tveimur person crops;
- sófi/bakgrunnur og sameiginleg print mask;
- silhouette depth skirt/backfill sem líkir eftir geometry-rendunum sem AC3D teygir aftur frá útlínunni.

## Tími

- Upphafleg 50-step fitting-keyrsla tók um 12 mínútur.
- Endurkeyrsla meðan runtime var sannreynt tók um 6 mínútur og 36 sekúndur.
- Final cached front-only keyrsla tók um 2 mínútur og 18 sekúndur.

Tímar eru wall-clock athuganir úr þessari rannsóknarlotu, ekki benchmark með hreinsuðu cache.

## Skrár

- [Uppsetning og bilanagreining](INSTALLATION-AND-TROUBLESHOOTING.md)
- [Artifact skrá](ARTIFACTS.md)
- [Runtime versions](requirements/RUNTIME-VERSIONS.md)
- [Frozen requirements](requirements/requirements-econ-windows-py38.txt)
- [Checksums](CHECKSUMS.sha256)
- `code-snapshot/`: read-only afrit af nákvæmum launcher, config, renderer og breyttum ECON skrám.
- `references/`: varðveitt AC3D sjónræn viðmið frá notanda.
