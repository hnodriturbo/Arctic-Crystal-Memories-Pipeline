<!--
File: .Markdown/runs/2026-08-31-econ-front-only-both-together/requirements/RUNTIME-VERSIONS.md
Purpose:
 - Record observed installed versions separately from intended requirement pins.
-->

# Runtime versions observed on 2026-08-31

| Component | Version |
|---|---|
| Windows Python | 3.8.4 |
| Torch | 1.12.1+cu116 |
| torchvision | 0.13.1+cu116 |
| Torch CUDA runtime | 11.6 |
| CUDA toolkit / nvcc | 11.6.124 |
| PyTorch3D | 0.7.2 |
| CuPy | 12.3.0 |
| trimesh | 3.17.1 |
| opencv-python package | 4.7.0.68 |
| opencv-contrib-python package | 4.7.0.68 |
| MediaPipe package | 0.10.11 |
| pytorch-lightning | 1.8.6 |
| rembg | 0+unknown local wheel |
| Blender | 5.1.2 |
| NVIDIA driver | 610.47 |
| GPU | NVIDIA GeForce RTX 3060 Laptop GPU, 6144 MiB |

Athugið: `cv2.__version__` skilaði `5.0.0` þótt uppsettu PyPI pakkarnir væru 4.7.0.68. Þetta bendir til blandaðs namespace/runtime import og er skráð sem frávik; endurgerð á að nota package-listann og smoke-test, ekki treysta eingöngu á `cv2.__version__`.
