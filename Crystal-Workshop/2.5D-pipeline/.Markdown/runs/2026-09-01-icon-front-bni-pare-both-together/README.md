<!--
File: .Markdown/runs/2026-09-01-icon-front-bni-pare-both-together/README.md
Purpose:
 - Freeze the controlled PARE versus PIXIE front-only ICON/d-BiNI comparison.
-->

# Run: ICON + PARE raw normals → front-only d-BiNI

## Niðurstaða

PARE var keyrt á nákvæmlega sömu `man.png` og `woman.png` person-canvases og
frysta [PIXIE-runnið](../2026-09-01-icon-front-bni-pixie-both-together/README.md).
Allar downstream d-BiNI og adaptive-fillet stillingar voru óbreyttar.

Fyrir þessa sitjandi, partially-occluded mynd er **PARE betri structural
body/posture baseline**:

- fitting-loss lækkaði úr um `0,233` í `0,229` hjá manninum;
- fitting-loss lækkaði úr um `0,247` í `0,237` hjá konunni;
- front-flöturinn er samfelldari við munn, bol og skarandi handleggi;
- PIXIE heldur meiri staðbundinni depth-amplitude og virðist skarpara á sumum detail-svæðum.

Þetta er því ekki niðurstaðan „henda PIXIE“. Vinningsstefnan er PARE fyrir
occlusion-aware líkamsgrunn, síðan source/detail refinement með ICON normals,
PIXIE/SMPL-X upplýsingum og síðar HRN face patch þar sem mælingar styðja það.

## Model stack

1. Official PARE `pare_w_3dpw_checkpoint.ckpt` sem HPS estimator.
2. Official ICON `normal.ckpt`.
3. SMPL body model og 100 ICON fitting iterations.
4. Lossless `float32` front/back normal, depth og mask export.
5. ECON d-BiNI front-only integration.
6. Adaptive fillet með `radius_fraction=0,006` og `gradient_quantile=98,5`.

Ekki notað: ICON implicit reconstruction/closure, HRN, MoGe-2, scene fusion,
Composer eða crystal scaling.

## Controlled A/B

| Mæling | PIXIE | PARE | Mat |
|---|---:|---:|---|
| Maður final fitting-loss | ~0,233 | ~0,229 | PARE lægra |
| Kona final fitting-loss | ~0,247 | ~0,237 | PARE lægra |
| Maður Z-extent | 0,556642 | 0,523745 | PARE grynnra/sléttara |
| Kona Z-extent | 0,451482 | 0,424535 | PARE grynnra/sléttara |
| Samtals triangles | 249.250 | 249.250 | Sama source-mask/topology budget |

Source-maskarnir voru bit-identical milli HPS-priora (`mask_xor_pixels=0`).
Munurinn kemur því frá fitted prior, predicted normals og depth; ekki frá annarri
silhouette crop. Mean absolute munur innan sameiginlegs masks:

- maður: `normal_F=0,124056`, `depth_F=5,263504`;
- kona: `normal_F=0,070394`, `depth_F=3,255236`.

## Geometry

- maður: 65.832 vertices / 130.096 triangles / 1 component;
- kona: 60.280 vertices / 119.154 triangles / 1 component;
- samtals: 126.112 vertices / 249.250 triangles;
- báðir eru opnir source-facing 2.5D fletir, ekki watertight 360° líkön.

## Samþykkt og óleyst

Samþykkt:

- PARE sem structural HPS-vinningsgrunnur fyrir þetta occlusion-tilvik;
- sama adaptive-fillet d-BiNI recipe;
- output nálægt 250k triangle rannsóknarmarkinu;
- varðveitt exact raw tensors, GLB/OBJ, Blender QA og kóðasnapshot.

Óleyst:

- pair-view er enn diagnostic side-by-side, ekki original source-camera fusion;
- 30° sýn sýnir enn útlínustrekkingu undir höku og við hendur;
- PARE-flöturinn er aðeins mýkri/grynnri en PIXIE;
- sófi, general scene-depth, texture registration og formal backfill vantar;
- face identity, hár og gleraugu þurfa sérhæft refinement.

## Næsta skref

1. Nota PARE sem body/depth grunn fyrir þessa mynd.
2. Varpa báðum person-flötum aftur í original source camera áður en frekari smoothing er gert.
3. Bæta við source-aware seam/backfill mask sem greinir raunveruleg occlusion-bil frá göllum.
4. Prófa general scene-depth fyrir sófann sem aðskilið lag.
5. Meta PIXIE/HRN detail patches eftir region, ekki blanda allri geometry blindandi.

## Skrár

- [Artifact skrá](ARTIFACTS.md)
- [Checksums](CHECKSUMS.sha256)
- [Read-only code snapshot](code-snapshot/README.md)
