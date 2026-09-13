<!--
File: .Markdown/runs/2026-09-01-icon-front-bni-pixie-both-together/README.md
Purpose:
 - Preserve the first ICON-normal to front-only d-BiNI 2.5D experiment and its A/B variants.
-->

# Run: ICON + PIXIE raw normals → front-only d-BiNI

## Niðurstaða

Þetta run bjargar high-precision `normal_F` áður en ICON fer í implicit occupancy/marching-cubes closure. Normal, SMPL-X depth prior og source mask eru síðan samþætt með ECON d-BiNI í opinn, source-facing 2.5D framflöt.

Besti variant þessa runs er **adaptive fillet**:

- maður: 65.832 vertices / 130.096 triangles / 1 component;
- kona: 60.280 vertices / 119.154 triangles / 1 component;
- samtals: 126.112 vertices / 249.250 triangles;
- full-3D closure, IF-Net, Poisson, HRN, MoGe-2 og Composer voru ekki notuð.

Posture, coarse andlit, háls, fatnaður og hendur varðveitast mun betur en í rejected ICON 256³ closed mesh. Hliðarsýn sýnir enn ófullkomna útlínustrekkingu við stór occlusion-stökk, þannig outputið er rannsóknar-baseline en ekki production-ready.

## Model stack

1. Official ICON `normal.ckpt`.
2. PIXIE + SMPL-X 2020 pose/shape/camera prior.
3. 100 SMPL fitting iterations á sömu person canvases og fyrra ICON-baseline.
4. Lossless `float32` export af `normal_F`, `normal_B`, SMPL depth og mask.
5. ECON d-BiNI front integration.
6. Adaptive depth fillet aðeins á efstu 1,5% depth-gradientum.

Ekki notað: ICON implicit reconstruction, PARE, ECON normal checkpoint, back-surface output, HRN, general scene depth eða source-camera pair fusion.

## Raw tensor export

Official ICON inference fékk tvo opt-in flags:

```text
--export_front_data
--front_data_only
```

`front_data_only` stöðvar eftir normal/depth og fitted SMPL export. Það kemur í veg fyrir að rejected 360° closure sé keyrð óvart sem hluti af samþykkta 2.5D runinu.

Fyrsta export-tilraun tók aðeins fyrstu línu 512×512 depth-mapps vegna þess að ICON renderer skilaði 2D tensor án batch-víddar. Það export er varðveitt undir `icon-export/` en hafnað. Rétta `icon-export-v2/` styður bæði 2D og batched depth tensors.

## A/B geometry variants

| Variant | Cut intersections | Remove steep faces | Fillet | Niðurstaða |
|---|---:|---:|---:|---|
| `front-surface-v2` | já | já | nei | Sprungur; 3/2 components. |
| `front-surface-no-cut` | nei | já | nei | Litlar breytingar; sprungur héldust. |
| `front-surface-continuous` | nei | nei | nei | Einn component; góð front-samfella en hráir langir tengitriangles. |
| `front-surface-adaptive-fillet` | nei | nei | já | Besti front-flöturinn; strekking mýkist en þarf áfram seam/backfill refinement. |

Þetta einangraði orsök svörtu sprungnanna: `remove_stretched_faces()` eyddi triangles sem snúa bratt frá myndavélinni. Default ECON-hegðun er áfram óbreytt; nýja stillingin er opt-in.

## Adaptive fillet formúla

Fillet-radius er ekki fast millimetragildi á reconstruction-stigi:

```text
radius_px = round(max(image_width, image_height) × radius_fraction)
          = round(512 × 0,006)
          = 3 px
```

Einungis gradientar við eða yfir 98,5 percentile eru blandaðir. Þannig er reynt að mýkja stór occlusion-/depth-stökk án þess að blura venjulegar peysuhrukkur eða andlitsdetail. Physical millimetra-scaling kemur síðar þegar source-camera fusion og geometry eru samþykkt.

## Samþykkt og takmarkanir

Samþykkt:

- raw ICON float-normal tensor export;
- front-only d-BiNI sem rétt research direction;
- continuous/adaptive-fillet variant sem núverandi besti ICON geometry candidate;
- einn mesh component á mann;
- aggregate mesh budget nálægt 250k triangle lágmarkinu.

Óleyst:

- mennirnir eru enn á aðskildum person canvases;
- diagnostic pair view er ekki original source-camera registration;
- sófi og scene-depth vantar;
- hendur/háls geta fengið breiða stretched bridge frá hlið;
- source texture er í individual GLB en neutral Blender QA metur geometry eingöngu;
- hár, gleraugu og high-frequency identity þurfa seinni refinement.

## Næsta skref

1. Keyra official ICON með `hps_type=pare` á sömu canvases og exporta sömu raw tensors.
2. Nota sama adaptive-fillet d-BiNI config og bera PIXIE/PARE saman án annarra breytinga.
3. Velja prior per posture, silhouette og hand/arm continuity.
4. Varpa vinningsflötum aftur í original 1086×1177 source camera.
5. Bæta síðan general scene-depth og formlegri silhouette backfill/útlínustrekkingu við.

## Skrár

- [Artifact skrá](ARTIFACTS.md)
- [Checksums](CHECKSUMS.sha256)
- `code-snapshot/`: read-only run scripts og modified upstream source files.
