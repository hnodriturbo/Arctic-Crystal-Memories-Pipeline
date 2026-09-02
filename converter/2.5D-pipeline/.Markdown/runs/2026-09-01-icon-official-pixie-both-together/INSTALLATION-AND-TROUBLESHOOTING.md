<!--
File: .Markdown/runs/2026-09-01-icon-official-pixie-both-together/INSTALLATION-AND-TROUBLESHOOTING.md
Purpose:
 - Record the exact Windows compatibility work needed for official ICON inference.
-->

# ICON Windows uppsetning og bilanagreining

## Source

- Official ICON: commit `ba2ee5681284c3d627305b1c919f4414009f753b`.
- Official neural voxelization layer: commit `b3c054e378fcca4daf6a53aceeee7ef39e86318b`.
- ICON `data` í source er directory junction yfir í ignored local asset tree `Models/research/ICON/data`.

## Einangrun frá ECON

Staðfesta ECON Python 3.8/Torch/CUDA environment var ekki breytt. ICON-only pakkar voru settir í:

```text
Models/runtimes/icon-py38-cu116-overlay/site-packages
```

`run_icon_windows.ps1` setur overlay-ið fremst í `PYTHONPATH` aðeins fyrir child process.

## Native dependencies

- Python 3.8.4 runtime.
- Torch 1.12.1+cu116.
- CUDA toolkit 11.6.124.
- Visual Studio 2019 Build Tools, MSVC 14.29.30133.
- Python 3.8 headers/libs úr local uv Python 3.8.20 runtime meðan extension var smíðað.
- NVIDIA Kaolin 0.12.0 official Windows wheel fyrir Torch 1.12.1/CUDA 11.6.

## Leystar villur

### `ModuleNotFoundError: kaolin`

Leyst með official NVIDIA wheel:

```text
https://nvidia-kaolin.s3.us-east-2.amazonaws.com/torch-1.12.1_cu116/
kaolin-0.12.0-cp38-cp38-win_amd64.whl
```

### PyMCubes 0.1.6 reyndi source-build án Python headers

Notað var síðasta fáanlega CPython 3.8 Windows wheel: `PyMCubes==0.1.4`.

### `voxelize_cuda` DLL procedure mismatch

Gamalt local binary passaði ekki current Torch ABI. Extension var endursmíðað úr official commit með VS2019 og CUDA 11.6. Eina source-fixið breytir gölluðu preprocessor `and` í `&&`; sjá `neural-voxelization-cuda-arch.patch`.

### PIXIE leitaði í `data/HPS/*`

Asset zipið var rétt en flatara en official fetch-script layout. Junction aliases voru gerðir án afritunar:

```text
data/HPS/pixie_data -> data/pixie_data
data/HPS/pare_data  -> data/pare_data
data/HPS/pymaf_data -> data/pymaf_data
```

### `Image.ANTIALIAS` vantaði

Official ICON requirements leyfa Pillow 9. `Pillow==9.5.0` var sett í overlay í stað þess að breyta image-kóðanum.

### Windows absolute input path varð að output filename

Upstream notaði `img_path.split("/")`. Ein I/O-lína var lagfærð í `os.path.basename/splitext`; sjá `icon-official-windows-path.patch`. Engin model eða geometry reikniregla breyttist.

## Asset hashes

| Asset | Bytes | SHA-256 |
|---|---:|---|
| `icon-filter.ckpt` | 29.581.085 | `B9FDB5214CDEFA5922037D2B9D67E68AC0E72752CC1DEBA9868433FB6D68E8A1` |
| `normal.ckpt` | 1.459.672.095 | `8FDAB289FF706441A4ECF55D73367B9C3FC8ECAAC7DF872F4F537B0997616F44` |
| `pixie_model.tar` | 773.605.748 | `9DADE173CBE63527209BFD413B9698E8F194AC9BFB9CF11012A823B4C75ED6B9` |
| `SMPLX_NEUTRAL_2020.npz` | 167.264.530 | `BDF06146E27D92022FE5DADAD3B9203373F6879ECA8E4D8235359EE3EC6A5A74` |

Engar innskráningarupplýsingar eða model binaries eru í Git.
