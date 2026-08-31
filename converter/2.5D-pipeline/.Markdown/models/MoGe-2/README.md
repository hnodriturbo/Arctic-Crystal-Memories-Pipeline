<!--
File: .Markdown/models/MoGe-2/README.md
Purpose:
 - Record the intended general-depth role for non-human scene geometry.
-->

# MoGe-2 / almennt scene-depth

## Hlutverk hjá ACM

Almennt depth model á að gefa source-aligned global depth fyrir sófa, bakgrunn og önnur non-human svæði. Það getur einnig verið low-frequency depth anchor undir manneskjum, en má ekki eyða anatomy sem ECON endurgerir betur.

## Staða

MoGe-2 var **ekki notað** í ECON-baseline 2026-08-31. Næsta rannsóknarlota byrjar á því að prófa almenna dýpkun á varðveittu ECON-senunni og bera afbrigði saman án þess að breyta baseline.

## Samrunaregla

- Human mask: ECON er aðal geometry.
- Face confidence area: seinna HRN refinement.
- Non-human mask: general depth er aðal geometry.
- Transition band: confidence-weighted smooth blend í source camera, með mældri seam width.
