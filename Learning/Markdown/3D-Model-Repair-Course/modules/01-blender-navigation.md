<!--
File: Learning/Markdown/3D-Model-Repair-Course/modules/01-blender-navigation.md
Purpose:
 - Teach the minimum Blender controls needed to inspect and repair a mesh.
-->

# 01 — Blender-viðmót og navigation

## Þrjú vinnuhamstig

- **Object Mode:** færa, nefna, afrita og skipuleggja heil objects.
- **Edit Mode:** breyta vertices, edges og faces í einu mesh.
- **Sculpt Mode:** ýta, draga og smooth-a yfirborð með brush.

`Tab` skiptir milli Object og Edit Mode. Veldu mode úr efra vinstra horni þegar þú vilt Sculpt Mode.

## Sjónarhorn

| Aðgerð | Stýring |
|---|---|
| Snúa sýn | miðmús og draga |
| Pan | `Shift` + miðmús |
| Zoom | músarhjól |
| Front | Numpad `1` |
| Right side | Numpad `3` |
| Top | Numpad `7` |
| Perspective/orthographic | Numpad `5` |
| Frame selected | Numpad `.` |
| Frame all | `Home` |

Á lyklaborði án numpad má nota `View` valmyndina eða virkja `Emulate Numpad` í Preferences.

## Sýna geometry skýrt

Notaðu `Z` pie menu:

- **Solid:** besta almenna geometry-sýnin.
- **Wireframe:** sjá triangles og geometry fyrir aftan.
- **Material Preview:** athuga texture/material, en ekki nota það eitt til geometry-mats.

Kveiktu á `Overlays > Wireframe` þegar þú þarft bæði solid shading og topology. Notaðu `X-Ray` aðeins tímabundið; annars velurðu óvart vertices á bakhlið.

## Fyrsta æfing

Án þess að breyta mesh:

1. Veldu manninn í Outliner.
2. Skoðaðu front, báðar hliðar, top og 45°.
3. Skiptu milli Solid og Wireframe.
4. Finndu nef, eyra, hönd og ystu silhouette í öllum sjónarhornum.
5. Vistaðu ekki breytingar ef þú færðir object óvart.
