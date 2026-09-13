<!--
File: .Markdown/methodology/ACMCRYSTAL-PROJECT-FORMAT.md
Purpose:
 - Define an open ACM-owned desktop project container instead of authoring Cockpit3D files.
-->

# `.acmcrystal` verkefnissnið

## Ákvörðun

ACM Crystal Studio skrifar ekki `.cockpit` eða `.ci`. Fyrri read-only rannsókn
staðfesti að `.cockpit` er ZIP með læsilegu scene XML, en `.ci` geometry-payload
er umbreytt og ekki örugglega skrifanlegt. Okkar snið verður viljandi opið,
versionað og byggt á standard GLB/PNG/JSON.

## Container

`.acmcrystal` er ZIP með þessari lágmarksuppbyggingu:

```text
manifest.json
source/original.jpg
source/prepared.png
source/subject-mask.png
geometry/model.glb
previews/front.png
previews/profile.png
logs/run.log
```

Stór intermediate tensors mega vera utan project-skrárinnar í cache og skráð
með relative artifact-reference og checksum.

## Manifest v1

```json
{
  "format": "acmcrystal",
  "version": 1,
  "units": "mm",
  "axes": { "up": "+Y", "front": "+Z" },
  "source": {
    "original": "source/original.jpg",
    "prepared": "source/prepared.png",
    "mask": "source/subject-mask.png"
  },
  "geometry": {
    "glb": "geometry/model.glb",
    "depthMm": 10.8
  },
  "blank": {
    "id": "none-fullsize",
    "widthMm": 138.57,
    "heightMm": 300.0,
    "depthMm": 60.0,
    "showCrystal": false
  },
  "pipeline": {
    "profile": "cuda-quality",
    "runId": "example"
  }
}
```

## Reglur

1. `version` hækkar aðeins þegar reader þarf nýja hegðun.
2. Allar stærðir og transforms eru í millimetrum.
3. GLB er canonical approval geometry; DXF/XYZ eru export, ekki project source.
4. Allar paths innan ZIP eru relative og mega ekki innihalda `..`.
5. Reader staðfestir checksum, path traversal, skráarstærð og leyfð media-snið.
6. Original og generated artifacts eru aldrei skrifuð yfir við migration.

