<!--
File: .Markdown/models/Sapiens/README.md
Purpose:
 - Record the Sapiens experiment, downloaded assets, and runtime incompatibility.
-->

# Sapiens

## Fyrirhugað hlutverk

Sapiens normal og foreground/background segmentation voru skoðuð sem möguleg uppfærsla á normals og mask quality.

## Staða í ECON-baseline

Sapiens var **ekki notað** í árangursríku baseline-keyrslunni. Local checkpoints voru sótt, en núverandi TorchScript skrár kalla á `aten::scaled_dot_product_attention`, sem er ekki í einangraða Torch 1.12.1 + CUDA 11.6 ECON-runtime-inu.

## Varðveitt assets

- Sapiens 0.3b normal checkpoint: um 1.265 GiB.
- Sapiens 1b foreground/background segmentation checkpoint: um 4.392 GiB.
- Assets eru geymd á D-drifinu; launcher vísar í local cache.

## Næsta skref

Prófa í aðskildu Torch 2.x runtime-i. Ekki uppfæra ECON-baseline runtime in-place, því þá glatast endurgeranleg staða PyTorch3D/CuPy/d-BiNI keyrslunnar.
