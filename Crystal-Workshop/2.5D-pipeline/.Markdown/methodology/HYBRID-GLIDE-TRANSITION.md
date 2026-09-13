<!--
File: .Markdown/methodology/HYBRID-GLIDE-TRANSITION.md
Purpose:
 - Define the v3-front plus v5-edge hybrid and the physical meaning of a 0.01 mm glide tolerance.
-->

# Hybrid v6: v3 front + v5 glide-band

## Staðfest staða

Samþykkta depth-skirt v3 notar tvo boundary-ringa: einn á human-framhlið og
einn við sampled MoGe scene-depth. Tvö triangles tengja hvern edge beint aftur.
Það er **ekki** 0,01 mm glide og getur litið út eins og 90° extrusion frá hlið.

V5 varðveitir human-framhliðina óbreytta og bætir við 12 hringja smoothstep-band:

- 6 px underlap inn undir silhouette;
- 3 px scene sample offset út á við;
- 80 boundary-depth smoothing iterations;
- náttúruleg internal gaps haldast opin.

V5 er því rétta upphafið fyrir jaðarinn, en tekur ekki við af v3-framhliðinni.

## Merking 0,01 mm

Við 18% viewer-dýpt á 60 mm blank er sýnd relief-dýpt 10,8 mm. V3 source
Z-span er 0,746234 scene-unit, eða um 14,473 mm á scene-unit. Þá er 0,01 mm um
0,000691 scene-unit.

0,01 mm á ekki að þýða að búa til eitt heilt geometry-ring fyrir hverja 0,01
mm niður í dýpt. Það gæti myndað hundruð ringa og milljónir óþarfa triangles.
Það verður notað sem:

- overlap/clearance epsilon við scene-tenginguna;
- hámarks leyfilegt curve-frávik þegar glide-band er adaptive tessellated;
- QA-tolerance við physical scaling.

## Hybrid v6 regla

```text
fryst v3/ICON-ECON human front
  → mjótt v5 Hermite/smoothstep transition-band
  → 0,01 mm overlap tolerance
  → MoGe scene-depth
```

Front vertices, face detail og source-camera registration mega ekki breytast.
Einungis boundary-band og scene-underlap eru breytileg milli tilrauna.

## Næstu A/B gildi

Prófa 12, 24 og adaptive ring-count við sömu camera/lighting:

1. front-view: enginn halo;
2. 30°/45°: engin sýnileg 90° brún eða regluleg banding;
3. profile: samfelld tangent inn í scene;
4. arm/body gap: enn opið;
5. geometry budget og GLB-stærð skráð.

