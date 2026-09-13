<!--
File: .Markdown/runs/2026-09-02-scene-fusion-and-depth-skirts/ARTIFACTS.md
Purpose:
 - Map scene-fusion, rejected gap-fill, and silhouette depth-skirt artifacts.
-->

# Scene fusion artifacts

## Human + scene v1

```text
output/research/scene-fusion/pare-icon-econ-moge2-both-together-v1/
```

Contains separate source-camera human OBJ, MoGe scene OBJ/GLB, combined OBJ/GLB,
layer overlay, stats, Blender QA and full gallery.

## Rejected gap fill

```text
output/research/icon-front-bni/both-together-ai-enhanced-pare/front-surface-adaptive-fillet-repaired-v1/
output/research/source-camera-fusion/both-together-ai-enhanced-pare-repaired-v2/
```

Preserved as negative evidence only. It is not a parent for future runs.

## Depth-skirt v3

```text
output/research/scene-fusion/pare-icon-econ-moge2-clearance0-v3/
output/research/scene-fusion/pare-icon-econ-moge2-clearance0-depth-skirts-v3/
```

Contains separate man/woman skirt OBJ/GLB, human/scene layers, combined OBJ/GLB,
`silhouette_depth_skirt_stats.json`, Blender QA and full gallery.

The accepted black-and-white viewer artifact is:

```text
output/research/scene-fusion/pare-icon-econ-moge2-clearance0-depth-skirts-v3/both_people_scene_with_depth_skirts-crystal-tone.glb
```

Its sidecar records the geometry-preserving luma conversion:
`both_people_scene_with_depth_skirts-crystal-tone.json`.

## Feathered v4 — rejected

```text
output/research/scene-fusion/pare-icon-econ-moge2-clearance0-feathered-depth-skirts-v4/
```

Contains the outward multi-ring skirt, QA renders and rejected gallery. Kept
only for comparison because the front halo is unacceptable.

## Feathered v5 — candidate

```text
output/research/scene-fusion/pare-icon-econ-moge2-underlap9-v5/
output/research/scene-fusion/pare-icon-econ-moge2-underlap9-feathered-v5/
```

Contains the 9 px scene-underlap layer, inward feathered human meshes,
`feathered_depth_skirt_stats.json`, combined GLB/OBJ, Blender QA and gallery.
The v5 artifact remains experimental until the oblique stair-bands are removed.
