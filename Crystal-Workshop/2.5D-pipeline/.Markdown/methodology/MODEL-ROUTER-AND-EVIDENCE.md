<!--
File: .Markdown/methodology/MODEL-ROUTER-AND-EVIDENCE.md
Purpose:
 - Define auditable per-image model routing for single-person 2.5D generation.
-->

# Model router og source-evidence

## Umfang

Ein keyrsla merkir:

```text
ein ljósmynd
  -> ein manneskja
  -> val á model stack út frá því sem sést í source
  -> eitt source-facing 2.5D output
```

Routerinn má ekki giska á ósýnilega líkamsparta og kynna þá sem source-derived. Hann skráir fyrst mælanlegt evidence og velur síðan profile.

## Það sem er skráð fyrir hverja mynd

- source SHA-256 og pixel-stærð;
- alpha-components og stærsti samfelldi foreground-flötur;
- fjöldi andlita, face-box, confidence og stærð andlits miðað við mynd;
- staðfestir pose-landmark hópar: höfuð, axlir, olnbogar, úlnliðir, mjaðmir, hné og ökklar;
- valið profile og confidence;
- ástæður fyrir vali;
- profile sem var hafnað og hvers vegna;
- model ownership per sýnilegt svæði;
- mannlegt QA eftir keyrslu: rétt/rangt routing, samþykkt artifact og failure notes.

Vél-læsilega skráin heitir `model-route.json` og notar schema `acm-2.5d-model-route/v1`.

## Fyrstu routing-reglur

### Close portrait

Eitt stórt andlit, axlir/efri búkur sjást en fætur eru ekki staðfestir:

- HRN: sýnilegt höfuð, andlit og eyru;
- MoGe-2: sýnilegur háls, axlir, bolur og fatnaður;
- source alpha: silhouette;
- bounded multi-ring backfill: útlínustrekking;
- original B/W luma: appearance.

Source contract fyrir depth og maska:

- MoGe fær original opaque/upscaled photograph, aldrei transparent-black cut-out;
- BiRefNet output er merkt `semantic_mask_not_depth` og má ekki birtast sem depth;
- MoGe depth dynamic range er mælt aðeins innan stærsta alpha-components;
- p99-p1 metric span undir skilgreindum quality threshold stoppar samsetningu;
- direct native HRN geometry er valið fram yfir rasterað HRN heightfield þegar
  face fidelity skiptir máli.

`amma-2` v3.3 sýndi 0,2563 m subject-only MoGe p99-p1 range. Full native HRN
head leysti opna side/profile skel front-patch leiðarinnar, en ownership seam
við háls/fatnað þarf enn sértækt stitch/remesh. Sjá
[v3.3 runnið](../runs/2026-09-03-portrait-v33-direct-hrn-original-moge/README.md).

PARE/ICON/ECON full-body prior er hafnað sem sýnilegur source-flötur vegna hættu
á að búa til faldar hendur eða fætur. SMPL-X má þó prófa sem afmarkaðan, falinn
háls-/líkamsstuðning undir HRN og MoGe. Slíkt próf má aðeins verða sjálfgefið ef
það bætir ownership-seam í öllum þremur QA-sjónarhornum án þess að breyta
andlitsauðkenni. Sjá [SMPL-X evaluation plan](SMPL-X-EVALUATION-PLAN.md).

### Full-body

Axlar, mjaðmir, hné og ökklar eru staðfest source-visible:

- PARE/ICON/ECON má prófa sem structural prior;
- HRN má refina andlit;
- MoGe-2 heldur scene/global depth.

### Óljóst medium shot

Ef evidence styður ekki öruggt val eru tvö output gerð sem A/B, aldrei blanduð fyrirfram. Human QA velur og skráir hvað reyndist rétt.

## Hvernig reglurnar verða betri

Routerinn er ekki lokaður AI-dómari. Hann er rekjanlegt decision layer sem batnar með prófunum:

1. keyra mismunandi myndir;
2. varðveita route-evidence fyrir hverja;
3. skoða neutral front/30°/profile QA;
4. merkja routing `correct` eða `incorrect`;
5. skrá nákvæm failure regions;
6. breyta threshold/reglum aðeins þegar fleiri en eitt run styður breytinguna.

Þannig byggist valið á staðfestum ACM-niðurstöðum en ekki almennum fullyrðingum um að eitt líkan sé alltaf best.
