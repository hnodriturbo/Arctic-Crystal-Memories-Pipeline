<!--
File: .Markdown/runs/2026-08-31-econ-front-only-both-together/ARTIFACTS.md
Purpose:
 - Map frozen documentation to the large ignored runtime artifacts.
-->

# Artifacts

Stór model/output artifacts eru áfram í ignored `Models/` og `output/` trjánum. Þessi skrá heldur nákvæmri vísun án þess að tvöfalda multi-gigabyte gögn í Git.

## Output root

```text
output/research/econ-front-only/both-together-ai-enhanced/
```

## Input copy

```text
input/both_together.png
```

Þetta er byte-identical afrit af source input; bæði hafa SHA-256 `A39599AF402AAB74726C9276BAC593A44039408050E00EDE934E267AA8F0F2F1`.

## Hrá ECON gögn

```text
result/econ-front-rtx3060-6gb/BNI/both_together_0.npy
result/econ-front-rtx3060-6gb/BNI/both_together_1.npy
result/econ-front-rtx3060-6gb/obj/both_together_0_F.obj
result/econ-front-rtx3060-6gb/obj/both_together_1_F.obj
result/econ-front-rtx3060-6gb/obj/both_together_smpl_00.npy
result/econ-front-rtx3060-6gb/obj/both_together_smpl_00.obj
result/econ-front-rtx3060-6gb/obj/both_together_smpl_01.npy
result/econ-front-rtx3060-6gb/obj/both_together_smpl_01.obj
```

`*_F.obj` eru mikilvægustu baseline-artifactarnir. `*_smpl_*` er cache/body prior, ekki final detailed surface.

## QA artifacts

```text
qa/both_together_econ_front.png
qa/both_together_econ_45deg.png
qa/both_together_econ_front.glb
qa/both_together_econ_front_qa.blend
```

GLB notar hlutlaust QA-material. OBJ geymir source-derived vertex colors. `.blend` geymir camera, light og approximate side-by-side placement.

## Opnun

- `.blend`: opna beint í Blender.
- `.glb`: Blender `File > Import > glTF 2.0`, eða MeshLab. GLB er ekki Blender-document og á því ekki að opnast með `File > Open`.
- `.obj`: Blender `File > Import > Wavefront (.obj)` eða MeshLab.

## Rekjanleiki

Hashes á helstu artifacts og frozen snapshot eru í [CHECKSUMS.sha256](CHECKSUMS.sha256). Allar framtíðar dýptar/refinement keyrslur vísa í þessi hash sem parent-baseline.
