<!--
File: .Markdown/runs/2026-08-31-econ-front-only-both-together/INSTALLATION-AND-TROUBLESHOOTING.md
Purpose:
 - Record the Windows build and runtime work needed to reproduce the ECON baseline.
-->

# Uppsetning og bilanagreining

## Einangrað runtime

- Python 3.8.4
- Torch 1.12.1+cu116
- torchvision 0.13.1+cu116
- CUDA toolkit 11.6.2, `nvcc` 11.6.124
- Visual Studio 2022 C++ build environment
- RTX 3060 Laptop GPU, 6 GiB

Launcherinn breytir aðeins environment fyrir child-process. Hann breytir ekki system PATH. Hann setur `CUDA_HOME`, `CUDA_PATH`, Torch library path, local PyTorch3D source, local Hugging Face cache og local Sapiens asset path.

## Model assets

ICON/ECON assets voru sett í opinbera `data/` uppbyggingu: checkpoints, PIXIE, PARE/PyMAF, SMPL, SMPL-X og fylgigögn. `normal.ckpt` sem baseline notar er 1,591,572,521 bytes með SHA-256:

```text
9E78E491AB97268B76EC4FFABD0DF432A2A3BFCDB1A447FCC6690FF0F2A7051C
```

`SMPLX_NEUTRAL.npz` sem er í local ECON asset tree er 108,752,058 bytes með SHA-256:

```text
376021446DDC86E99ACACD795182BBEF903E61D33B76B9D8B359C2B0865BD992
```

Ekki skrá lykilorð, session cookies eða download tokens í þessa möppu.

## PyTorch3D

- Package version: 0.7.2.
- Local source snapshot-mappa: `pytorch3d-3388d3f0aa6bc44fe704fca78d11743a0fcac38c`.
- Build þurfti official CUDA 11.6.2 development libraries í einangraðan D-drive prefix.
- Windows path var of langt; temporary `subst P:` var notað í build og síðan fjarlægt.
- VS2022 build env notaði `DISTUTILS_USE_SDK=1` og `MSSdk=1`.
- NVCC fékk `-allow-unsupported-compiler -D_ALLOW_COMPILER_AND_STL_VERSION_MISMATCH`.
- 67 C++/CUDA compilation units voru byggðar.
- GPU smoke test á `ball_query` fór í gegn á RTX 3060.

## ECON Cython extensions

Byggt fyrir CPython 3.8 / Windows x64:

```text
lib/common/libmesh/triangle_hash.cp38-win_amd64.pyd
lib/common/libvoxelize/voxelize.cp38-win_amd64.pyd
```

Generated `.cpp`/`.c` skrár og `.pyd` artifacts eru runtime/build artifacts í ignored model tree; reproducible breytingarnar eru í frozen patch og source snapshot.

## CuPy / d-BiNI

CuPy compilation þurfti sama NVCC compiler override. `CUPY_ACCELERATORS` er sett tómt í launcher til að forðast CUB/nvcc ósamhæfni í þessu legacy runtime-i.

## Local ECON breytingar

1. `apps/infer.py`
   - bætti við `--front-only`;
   - hreinsaði Windows-óleyfileg tákn úr sample filename;
   - exportar `F_trimesh` strax eftir d-BiNI og sleppir 360° completion.
2. `lib/common/BNI.py`
   - gerði standalone `F_trimesh`/`B_trimesh` aðgengileg aftur.
3. `apps/sapiens.py`
   - lazy local checkpoint download í stað alls Hugging Face Space;
   - sequential VRAM unloading;
   - leiðrétt `no-bg-removal` mask handling.

Nákvæmt patch er í `code-snapshot/code/research/patches/econ-front-only-windows.patch`. `git apply --reverse --check` fór í gegn gegn patched ECON source við skráningu, sem staðfestir að patchið samsvaraði vinnuskránum.

## Sapiens tilraun sem var ekki notuð

Fyrsta Sapiens tilraunin gat ekki keyrt í Torch 1.12 vegna vöntunar á `aten::scaled_dot_product_attention`. Checkpoints voru varðveitt, en baseline fór aftur í official ECON `normal.ckpt`. Sapiens verður prófað í sér Torch 2.x runtime-i svo ekki þurfi að brjóta endurgeranlega legacy ECON-uppsetningu.

Tilraun til að sækja allt Hugging Face Space sótti um 25 GB í user cache og stöðvaðist á Windows symlink privilege (`WinError 1314`). Cache var ekki eytt; engin destructive cleanup var gerð.
