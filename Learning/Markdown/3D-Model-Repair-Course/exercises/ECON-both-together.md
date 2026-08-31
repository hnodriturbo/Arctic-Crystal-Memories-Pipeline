<!--
File: Learning/Markdown/3D-Model-Repair-Course/exercises/ECON-both-together.md
Purpose:
 - Provide the first guided exercise using the preserved successful ECON scene.
-->

# Æfing 1 — ECON `both_together`

## Baseline

```text
converter/2.5D-pipeline/output/research/econ-front-only/
both-together-ai-enhanced/qa/both_together_econ_front_qa.blend
```

Rannsóknarskráning: [ECON baseline](../../../../converter/2.5D-pipeline/.Markdown/runs/2026-08-31-econ-front-only-both-together/README.md).

## Markmið æfingarinnar

Ekki „laga allt“. Markmiðið er að læra að greina:

- eðlileg bil við hendur og handleggi;
- örfínar óæskilegar seam-línur;
- ytri silhouette sem gæti fengið strekkingu;
- svæði sem þurfa HRN eða almennt depth model frekar en handvirka breytingu.

## Skref

1. `Save As` í `output/learning/both-together/manual-repair-v001.blend`.
2. Búðu til locked source-afrit af báðum ECON objects.
3. Taktu front, right-side og 45° screenshots áður en breytt er.
4. Merktu fimm svæði með annotations eða skriflegum lista:
   - eitt raunverulegt occlusion-bil;
   - eina mögulega seam-línu;
   - eitt ear/hair silhouette svæði;
   - eitt svæði fyrir strekkingu;
   - eitt svæði sem á alls ekki að snerta.
5. Lagaðu aðeins eina örfína seam-línu á vinnuafriti.
6. Vistaðu `v002`.
7. Re-importaðu export í tóma senu og staðfestu breytinguna.

## Lokamat

Æfingin telst heppnuð ef breytingin er lítil, sannanleg og hefur ekki fyllt eðlilega bilið milli handar/handleggs og bols. Það er betra að gera eina rétta breytingu en tíu óstaðfestar.
