<!--
File: .Markdown/runs/2026-09-01-icon-official-pixie-both-together/ARTIFACTS.md
Purpose:
 - Map every local ICON run artifact to its meaning and preservation rule.
-->

# ICON run artifacts

Local artifact root, ignored by Git:

```text
output/research/icon-official/both-together-ai-enhanced-pixie/
```

## Inntak

- `input-source/both_together.png`: exact AI-enhanced source copy.
- `input-persons/man.png`: deterministic square man canvas.
- `input-persons/woman.png`: deterministic square woman canvas.

## Official ICON output

- `result/icon-filter/obj/*_recon.obj`: raw 256³ implicit marching-cubes reconstruction; aðal full-3D rannsóknarartifact.
- `result/icon-filter/obj/*_remesh.obj`: upstream 50k remesh fyrir cloth optimization; ekki aðal density output.
- `result/icon-filter/obj/*_smpl.obj`: fitted SMPL-X prior.
- `result/icon-filter/obj/*_smpl.npy`: fitted parameters.
- `result/icon-filter/png/*_smpl.png`: official 5×2 fitting/normal grid.
- `result/icon-filter/png/*_overlap.png`: source og predicted front-normal overlay.
- `result/icon-filter/png/*_cloth.png`: raw reconstruction normal views þegar cloth loop er 0.
- `result/icon-filter/refinement/*_smpl.gif`: 100-step fitting QA.
- `icon-official-pixie-run.log`: console transcript frá fullu runni.

## Extracted normal visualization

- `normals/man_normal_F.png`
- `normals/man_normal_B.png`
- `normals/woman_normal_F.png`
- `normals/woman_normal_B.png`

Þetta eru exact 512×512 cells úr official QA-gridinu, ekki raw tensor files. Upstream label er innan background-svæðis.

## Blender QA

- `qa/both_together_icon_official_pixie_front.png`
- `qa/both_together_icon_official_pixie_45deg.png`
- `qa/both_together_icon_official_pixie_profile.png`
- `qa/both_together_icon_official_pixie_raw_recon.glb`
- `qa/both_together_icon_official_pixie_raw_recon_qa.blend`

Blender importaði raw OBJ, setti smooth shading og neutral material og færði normalized mesh til vinstri/hægri fyrir samanburð. Þetta er ekki source-camera registration og breytir ekki innri vertex geometry.

Status: **rejected as production geometry; retained as diagnostic evidence**. Front/45°/profile render, GLB og `.blend` sýna tap sem verður milli predicted normals og lokaðs 256³ mesh. Samþykkt ICON-milliniðurstaða er `normals/*_normal_F.png`; næsta run þarf raw normal tensor og front-only integration.

## Preservation

Smoke-output undir `smoke-*` er tæknileg staðfesting og ekki final baseline. Final input, result, normals, QA, log og checksums eiga ekki að vera yfirskrifuð; næsta PARE, 512³ eða front-integration próf fær nýja run-möppu.

Tracked `code-snapshot/` geymir read-only afrit af nákvæmum run-skriftum, requirements og tveimur Windows-patch-skrám. `references/` geymir read-only afrit af sex ICON-kynningarskjáskotum sem fylgdu rannsóknarbeiðninni; þau eru ekki local output.
