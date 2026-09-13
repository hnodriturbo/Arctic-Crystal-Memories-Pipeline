<!--
File: Learning/Markdown/3D-Model-Repair-Course/modules/06-occlusion-and-strekking.md
Purpose:
 - Teach the distinction between valid occlusion gaps and silhouette depth-skirt geometry.
-->

# 06 — Occlusion og útlínustrekking

## Orðalagið okkar

**Strekking** merkir **útlínustrekkingu**: boundary vertices/triangles við silhouette eru teygð aftur í dýpt. Ensk tæknileg heiti eru `silhouette depth skirt` og `silhouette backfill`.

## Ekki fylla raunveruleg bil

Í ECON-mynd hjónanna eru stóru bilin við hendur/handleggi að mestu eðlileg occlusion-bil. Hendin á konunni er fyrir framan bolinn. Að loka bilinu myndi festa höndina við fötin og gera formið rangt.

Laga á aðeins örfínar línur eða göt sem skera samfelldan source-flöt án ljósmyndafræðilegrar ástæðu.

## Handvirk strekking í þessari QA-senu

Gerðu þetta aðeins á afriti:

1. Farðu í side view og staðfestu back-direction. Í þessari senu er hún almennt `+Y`.
2. Í Edit Mode skaltu velja aðeins viðeigandi ytri silhouette boundary.
3. Extrude-a boundary aftur í dýpt með `E`, síðan réttum axis.
4. Haltu front boundary alveg óhreyfðri; aðeins nýja röðin fer aftur.
5. Notaðu fleiri en eitt depth-step ef þú vilt bogna yfirfærslu í stað 90° veggs.
6. Scale/falloff á hverju skrefi má minnka röndina smám saman.
7. Tengdu aftari röð við back plane eða láttu hana enda þar sem crystal mask sleppir henni.

## Sjálfvirk framtíðaraðferð

Fyrir endurtekna pipeline þarf strekkingin að vera reiknuð, ekki föst millimetratala:

```text
skirt_depth = clamp(subject_depth_span * depth_ratio,
                    crystal_depth * min_ratio,
                    crystal_depth * max_ratio)
```

Boundary er síðan extrude-uð í nokkrum þrepum með smooth easing, til dæmis smoothstep/cosine falloff. Þannig skalast strekkingin með raunverulegri model- og crystal-dýpt.

## Gæðapróf

- Front-view má ekki breytast.
- 15°, 30° og 45° eiga að sýna samfellda strekkingu án rifinna triangles.
- Nef, hár og eyru mega ekki límast við rangan bakflöt.
- Innri occlusion-bil við hendur mega haldast opin ef print mask krefst þess.
