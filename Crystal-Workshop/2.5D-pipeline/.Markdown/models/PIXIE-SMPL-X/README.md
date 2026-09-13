<!--
File: .Markdown/models/PIXIE-SMPL-X/README.md
Purpose:
 - Record the body/head/hand prior used by the successful ECON baseline.
-->

# PIXIE + SMPL-X

## Hlutverk í baseline

PIXIE metur pose, shape og camera fyrir hvern einstakling. SMPL-X gefur sameiginlegan líkams-, höfuð- og handprior sem ECON notar við normals og surface integration. Þetta er ástæðan fyrir að pipeline-ið skilur manneskjulögun betur en almennt depth map eitt og sér.

## Staðfest notkun

- `hps_type: pixie`
- Multi-person mode virkt.
- 50 SMPL-X fitting iterations í upphaflegri fitting-keyrslu.
- Cache skrár `both_together_smpl_00` og `both_together_smpl_01` voru endurnýttar í final front-only run.
- Local ICON asset audit: SMPL-X, PIXIE, PARE og PyMAF eru `READY`.

## Nákvæmni og mörk

Priorinn gefur anatomy og pose, en source image/normals þarf að stjórna sýnilegum fatnaði og identity. Hann leysir ekki sjálfur hár, gleraugu eða source-aligned samruna margra person crops.

Sérstakt prófunarfylki fyrir v1.1, locked-head, Blender 10/300-shape,
SMPLify-X og Unity pakkana er skráð í
[SMPL-X evaluation plan](../../methodology/SMPL-X-EVALUATION-PLAN.md).
