<!--
File: .Markdown/models/HRN/README.md
Purpose:
 - Record HRN's intended face-refinement role and current research boundary.
-->

# HRN

## Hlutverk hjá ACM

HRN er fyrir nákvæmari sýnilegt andlit og head prior: kinn, enni, nef, eyru og höfuðform. Það á að keyra per detected face og sameinast source-facing ECON-fletinum í upprunalegri camera/pose.

## Staða

HRN head-only QA hefur verið prófað sérstaklega. Það sýnir gagnlegt identity/face geometry, en var **ekki notað** í ECON-baseline 2026-08-31. Því má rekja allan þann árangur beint til ECON + PIXIE/SMPL-X + d-BiNI.

## Varúð

- Fullt bakhöfuð, eyru og háls eru að hluta completion frá head prior.
- HRN native front/profile render má ekki líma beint á ECON. Projection, scale, pose og seam weights verða að koma frá source camera og landmarks.
- Meta skal neutral-material geometry áður en texture er sett á.
