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

2026-09-02 var Official ModelScope HRN Head v0.1 (BFM+FLAME) keyrt á close portrait og sameinað MoGe-2 exact-source depth. HRN/source SIFT-RANSAC skráningin náði 1,148 px miðgildisvillu. Þetta fjarlægði hallucinated PARE-hendur úr nærmyndinni og varð nýtt portrait-baseline. Sjá [HRN + MoGe-2 v3.1 runnið](../../runs/2026-09-02-portrait-hrn-moge-v31/README.md).

Endurkeyranlegt refinement notar `run_portrait_hrn_moge_refinement.ps1`. HRN texture/depth er renderað native, varpað í upprunalega myndavél og feathered inn í MoGe-grunninn með vertical fade yfir háls/jakka.

## Varúð

- Fullt bakhöfuð, eyru og háls eru að hluta completion frá head prior.
- HRN native front/profile render má ekki líma beint á ECON. Projection, scale, pose og seam weights verða að koma frá source camera og landmarks.
- Meta skal neutral-material geometry áður en texture er sett á.
