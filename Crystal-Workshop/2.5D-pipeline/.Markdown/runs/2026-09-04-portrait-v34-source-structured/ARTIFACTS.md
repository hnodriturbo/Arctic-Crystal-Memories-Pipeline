<!--
File: .Markdown/runs/2026-09-04-portrait-v34-source-structured/ARTIFACTS.md
Purpose:
 - Map reproducible v3.4 inputs, intermediate model evidence, and QA outputs.
-->

# Portrait v3.4 artifacts

Allar slóðir eru frá `converter/2.5D-pipeline/`.

## `amma-1` control

- Original: `input-testers/amma-og-afi/amma-1.jpeg`
- BiRefNet source/mask: `output/research/2026-09-04-portrait-v34-controls/amma-1/01-preprocess/`
- MoGe-2 ViT-L raw depth: `output/research/2026-09-04-portrait-v34-controls/amma-1/02-moge-original/depth_raw.npy`
- Native HRN: `output/research/2026-09-04-portrait-v34-controls/amma-1/03-hrn-head/source-prepared/hrn-head.obj`
- HRN registration: `output/research/2026-09-04-portrait-v34-controls/amma-1/05-hrn-closed-head/`
- V3.3 parent: `output/research/2026-09-04-portrait-v34-controls/amma-1/06-v33-base/`
- V3.4 GLB: `output/research/2026-09-04-portrait-v34-controls/amma-1/07-v34-smooth/portrait-v34-source-structured.glb`
- V3.4 statistics: `output/research/2026-09-04-portrait-v34-controls/amma-1/07-v34-smooth/portrait-v34-stats.json`
- Neutral QA: `output/research/2026-09-04-portrait-v34-controls/amma-1/07-v34-smooth/qa/`

## `amma-2` stress test

- BiRefNet source: `output/local-workbench/a3c0aadb7e3c/source-prepared.png`
- V3.3 parent: `output/research/portrait-v33-direct-hrn-original-moge/21-depth060-shoulders-thin-garment/`
- Hafnað gróft detail: `output/research/2026-09-04-portrait-v34-controls/amma-2/01-v34/`
- Gleraugna-fit milliskref: `output/research/2026-09-04-portrait-v34-controls/amma-2/02-v34-refined-fit/`
- V3.4 GLB: `output/research/2026-09-04-portrait-v34-controls/amma-2/03-v34-smooth/portrait-v34-source-structured.glb`
- V3.4 statistics: `output/research/2026-09-04-portrait-v34-controls/amma-2/03-v34-smooth/portrait-v34-stats.json`
- Neutral QA: `output/research/2026-09-04-portrait-v34-controls/amma-2/03-v34-smooth/qa/`

## Kóði

- V3.4 enhancement: `code/research/enhance_portrait_v34.py`
- HRN runner/precompiled-plugin stuðningur: `code/research/run_hrn_head_modelscope.py`
- Unit tests: `tests/test_enhance_portrait_v34.py`
