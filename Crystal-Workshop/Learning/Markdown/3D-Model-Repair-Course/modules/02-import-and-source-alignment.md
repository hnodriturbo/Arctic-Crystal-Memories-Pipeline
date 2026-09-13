<!--
File: Learning/Markdown/3D-Model-Repair-Course/modules/02-import-and-source-alignment.md
Purpose:
 - Explain safe import and how to compare geometry to the source photograph.
-->

# 02 — Import, orientation og source comparison

## Rétt leið til að opna skrár

- `.blend`: `File > Open`.
- `.obj`: `File > Import > Wavefront (.obj)`.
- `.glb`: `File > Import > glTF 2.0`.

GLB er ekki Blender-document og opnast því ekki með `File > Open`.

## Axes í ECON QA-senunni

ECON OBJ er Y-up. QA-import breytir því í Blender Z-up. Í varðveittu `both_together` QA-senunni horfir front-camera almennt eftir Y-ásnum; „aftur í dýpt“ er því almennt í átt að `+Y`. Staðfestu þetta alltaf í side view áður en þú extrude-ar—ekki gera ráð fyrir sama ás í öðrum skrám.

## Source image sem stöðugt viðmið

Best er að hafa source ljósmynd sem camera background/reference image:

1. Farðu í front orthographic view.
2. Bættu source við sem Image/Reference eða camera background.
3. Stilltu opacity þannig bæði mynd og mesh sjáist.
4. Ekki deform-a mesh til að passa perspective úr handahófi. Fyrst þarf camera/scale alignment.

## Multi-person varúð

ECON normalizes-ar hvert detected person crop sér. Í fyrstu QA-senunni voru einstaklingarnir settir gróflega í `x=-0.48` og `x=+0.48` aðeins til sjónmats. Þetta er ekki full source-camera registration.

Þegar source alignment verður gert formlega þarf að geyma fyrir hvern einstakling:

- crop rectangle í original pixels;
- camera scale/translation frá HPS;
- source landmarks;
- transform úr crop-space í sameiginlegt image/camera-space.

Manual lagfæring á anatomy á að bíða ef vandamálið er í raun rangt camera placement.

## Ekki þjappa dýptinni of snemma

Haltu geometry í stærra vinnudýptarrými meðan reconstruction og refinement fer fram. Það þarf pláss fyrir framan nef, enni og hendur og fyrir aftan líkama/sófa/strekkingu. Lokafit í crystal-template kemur eftir að þessi geometry er samþykkt. Sjá [vinnudýptarregluna](../../../../converter/2.5D-pipeline/.Markdown/methodology/DEPTH-SPACE-AND-CRYSTAL-SCALING.md).
