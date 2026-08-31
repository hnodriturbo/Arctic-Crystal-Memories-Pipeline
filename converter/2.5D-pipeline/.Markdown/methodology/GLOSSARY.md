<!--
File: .Markdown/methodology/GLOSSARY.md
Purpose:
 - Define consistent terms used while reviewing source-aligned 2.5D geometry.
-->

# Hugtakasafn

## Útlínustrekking

Stutt vinnuheiti: **strekking**. Enskt tæknilegt heiti: **silhouette depth skirt**; einnig **silhouette backfill**.

Geometry-rönd sem er búin til með því að strekkja eða teygja boundary vertices/triangles aftur í dýpt frá sýnilegri útlínu. Hún fyllir bak við front-facing 2.5D flöt og getur tengt hann við bakflöt án þess að þykjast vera endurgerð 360° anatomy.

Í AC3D-viðmiðinu birtist útlínustrekkingin sem langar rendur/fleygar frá hári, kinn, hálsi og öðrum útlínum. Þegar notandinn segir „strekking“ eða „strekkingu“ merkir það nákvæmlega þessa aðgerð, ekki smoothing eða almenna extrusion á öllum fletinum.

## Occlusion gap

Raunverulegt bil í source-sýn vegna þess að einn líkamspartur liggur fyrir framan annan—til dæmis hönd eða handleggur fyrir framan bol. Slíkt bil á ekki sjálfkrafa að fylla sem villa.

## Seam line / mask gap

Óæskileg örfín lína eða smágat á mörkum maska eða tveggja geometry-svæða. Þetta er það sem á að laga þegar línan samsvarar ekki raunverulegu occlusion-bili í ljósmyndinni.

## Front surface

Sýnilegi source-facing 2.5D flöturinn sem d-BiNI reiknar úr front normals. Hann er baseline okkar fyrir manninn.

## Completion

Ósýnileg geometry sem líkan áætlar út frá prior, til dæmis bakhöfuð eða bakhlið líkamans. Completion er ekki jafn traust og geometry sem styðst beint við source pixels.

## Vinnudýptarrými

Stærra reconstruction-volume með framsvigrúmi og baksvigrúmi. Módelið er unnið þar áður en það er fitted í lokastærð kristalsins. Þetta kemur í veg fyrir að nef eða annar fremsti punktur verði clamped við ramma.

## Framsvigrúm / front headroom

Laust rými fyrir framan núverandi source-facing flöt svo nef, enni, hendur eða önnur svæði geti færst nær áhorfanda.

## Baksvigrúm / back headroom

Laust rými fyrir aftan source-facing flöt fyrir líkamsdýpt, scene-depth og útlínustrekkingu.
