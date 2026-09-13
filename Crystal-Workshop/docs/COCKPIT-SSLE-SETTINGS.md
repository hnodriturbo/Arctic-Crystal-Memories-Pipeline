<!--
Purpose: Preserve owner-supplied Cockpit settings and verified source evidence.
-->

# Cockpit SSLE settings — 2026-09-13

The workflow has two distinct stages: generate a point cloud from the edited
surface and photograph, then write those points as DXF POINT entities.
Rasterizer settings concern point generation, not merely DXF serialization.
Matching their labels does not establish an equivalent Cockpit algorithm.

## Owner screenshots: active 3D Large preset

| Setting | Value |
| --- | --- |
| XY point distance | 0.08 mm |
| Z / layer distance | 0.09 mm |
| Toning | 1.80 |
| Trim point cloud to template | On |
| Layer shift | Off |
| Z jitter | On |
| Mask blur radius | 3.0 |
| Mask falloff exponent | 0.5 |
| Create stabilizing points | On |
| Power delta | 0.0 |
| Import scene settings | Off |
| Optimize on save | Off |

Geometry default rasterizer: Portrait; maximum layers 8; Z factor 5;
Diffuse 2; sample radius 3.0.

Vector defaults: face layers 4; Z factor 2; Diffuse 2; extrusion side fill 4.
Do not interpret factors, radii, or side-fill counts as millimetres without
further evidence. Do not apply vector defaults to a portrait automatically.

## Jón Þór: template and layer are different

Template: rectangle, 3D large, W80 × H100 × D60 mm. Margins XYZ5 mm,
bevel0, offsets XYZ0, article A0009. The owner's separate showroom preference
is a 5 mm display bevel; it must not overwrite the recorded Cockpit bevel0.

Layer: visible, use lightmap, default rasterization, maintain aspect ratio.
Position XYZ = (0, 0, -2.486) mm; dimensions approximately
(68.8820, 90.7073, 46.506) mm. Rotation XYZ = (-15, 0, 0) degrees.
Layer dimensions describe the portrait, not the crystal.

## Verified against actual files

Source: Cockpit3D-Files/75572-jon-thor/75572-jon-thor.cockpit.
Its CockpitScene.xml contains PointCloudBuilderSettings with XY0.08, Z0.09,
Toning1.8, TrimToTemplate=True, CreateStabilizers=True and
OptimizePointClouds=False. PortraitRasterizerSettings stores MaximumLayers8,
SampleRadius3, ZFactor5 and Stagger2. Preserve the raw key Stagger rather than
assuming every internal use is identical to the displayed Diffuse label.
VectorRasterizerSettings stores FaceLayers4, ExtrusionThickness4,
FaceZFactor2 and FaceDiffuse2. Mask and template values match the screenshots.
Layer shift and Z jitter were observed in the screenshots but were not present
as attributes in the inspected scene; do not label them as extracted values.

The paired DXF has 2,609,603 POINT entities. A streaming group-code scan found
no 999 comments, 1000 strings, or 1001 application XDATA carrying these settings.
Therefore retrieve the generating settings from the paired Cockpit file, not
from an assumption that every DXF contains them. DXF supports optional XDATA,
but exporters need not write it.

The production job report for 20260913-173254-7b527533 explicitly records
Eulers [-15,0,0], Position [0,0,-2.486], sample_rate1 and limit0. Thus the
Jón Þór GLB used the saved rotation and all source points. The reconstruction
undoes the scene pose for photograph projection and restores it afterward;
DXF scale is not applied a second time.

## Preservation contract

Keep original Cockpit and DXF files alongside derived assets. Store source
hashes, scene settings, applied pose and reconstruction options with each new
GLB and its JSON report. Distinguish raw extracted attributes, owner-supplied
settings and estimates. Unknown settings must stay unknown.

GLB extras can store application metadata, but an editor may omit it on export.
Keep the report independently. A smoothed or edited surface plus settings does
not reproduce the exact original point coordinates; retain the original DXF.

Sources: [Autodesk DXF XDATA](https://help.autodesk.com/cloudhelp/2018/ENU/AutoCAD-DXF/files/GUID-A2A628B0-3699-4740-A215-C560E7242F63.htm),
[Khronos glTF extras](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html#reference-extras).
