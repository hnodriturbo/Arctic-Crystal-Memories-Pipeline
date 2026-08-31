<!--
File: Learning/Markdown/3D-Model-Repair-Course/modules/08-export-and-validation.md
Purpose:
 - Teach repeatable export and independent verification of repaired models.
-->

# 08 — Export og gæðastaðfesting

## Áður en exportað er

1. Vistaðu nýtt `.blend` version.
2. Staðfestu að aðeins samþykkt `WORKING_` object verði exportað.
3. Athugaðu transform, scale og axes.
4. Reiknaðu normals ef þörf er á.
5. Skráðu vertex/face count.
6. Taktu front og 45° screenshot með hlutlausu efni.

## OBJ

OBJ er einfalt geometry-format sem MeshLab og Blender lesa vel. Staðfestu hvort vertex colors eða texture fylgi þeirri export-leið sem valin er; OBJ-stuðningur við vertex colors er ekki jafn staðlaður og geometry.

## GLB

GLB hentar til preview og geymir geometry/material í einni skrá. Flyttu inn með `File > Import > glTF 2.0`; ekki `File > Open`.

## Óháð re-import próf

1. Opnaðu tóma Blender-senu.
2. Importaðu exportið.
3. Athugaðu front, side og 45°.
4. Berðu vertex/face count saman.
5. Athugaðu scale og orientation.
6. Prófaðu neutral material.
7. Opnaðu einnig í MeshLab ef format interoperability skiptir máli.

## Samþykktarskilyrði

- source identity og pose óbreytt nema breyting hafi verið markmiðið;
- engin ný göt eða self-intersections;
- eðlileg occlusion-bil varðveitt;
- örfín óæskileg seams minnkuð;
- strekking slétt frá 15° til 45°;
- file size og triangle count innan crystal-template budget;
- input, parent-baseline, breytingar og checksum skráð.
