<!--
File: Learning/Markdown/3D-Model-Repair-Course/README.md
Purpose:
 - Provide a beginner-friendly course for manually repairing ACM 2.5D models.
-->

# Námskeið: lagfæring og hreinsun 3D/2.5D módela

## Markmið

Eftir námskeiðið átt þú að geta opnað ECON/ACM-módel í Blender, greint raunverulegt geometry-vandamál frá eðlilegri myndbyggingu, gert afmarkaðar breytingar og exportað staðfesta útgáfu án þess að skemma baseline.

Þú lærir sérstaklega að:

- rata í Blender og skilja Object, Edit og Sculpt Mode;
- varðveita source camera, scale og orientation;
- velja, fela, einangra og eyða geometry;
- laga smágöt og óæskilegar seam-línur;
- varðveita eðlileg occlusion-bil milli handar, handleggs og bols;
- smooth-a staðbundið án þess að eyða nefi, hrukkum, hári eða fatatexture;
- laga andlit, eyru, hendur og silhouette með litlum breytingum;
- búa til eða betrumbæta **útlínustrekkingu** aftur í dýpt;
- exporta OBJ/GLB og sannreyna output í nýrri senu.

## Námsröð

1. [Öryggi, afrit og útgáfur](modules/00-safety-and-versioning.md)
2. [Blender-viðmót og navigation](modules/01-blender-navigation.md)
3. [Import, orientation og source comparison](modules/02-import-and-source-alignment.md)
4. [Greining á mesh og topology](modules/03-mesh-diagnosis.md)
5. [Val, eyðing, göt og seams](modules/04-select-delete-and-repair.md)
6. [Smooth, Sculpt og varðveisla smáatriða](modules/05-smoothing-and-sculpting.md)
7. [Occlusion og útlínustrekking](modules/06-occlusion-and-strekking.md)
8. [Andlit, hár, eyru og hendur](modules/07-face-hair-ears-hands.md)
9. [Export og gæðastaðfesting](modules/08-export-and-validation.md)

## Fyrsta verklega æfingin

[ECON `both_together` lagfæringaræfing](exercises/ECON-both-together.md) notar nákvæmlega baseline-senuna sem gaf góða niðurstöðu 31. ágúst 2026.

## Golden rule

Ef breyting sést ekki greinilega sem framför bæði beint framan frá og í skásýn er hún ekki sett í samþykkta útgáfu. Geometry má ekki líta vel út aðeins vegna texture eða lýsingar.
