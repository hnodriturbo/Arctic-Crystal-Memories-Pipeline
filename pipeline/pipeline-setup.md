# Image Enhancement Pipeline — Setup

## Requirements

- **Python 3.11** (required — see note below)
- CUDA-capable GPU recommended (RTX 3060 or better)
- ~2GB free disk space for models

> **Why Python 3.11 and not 3.12/3.13?**
> `basicsr` (required by realesrgan and gfpgan) was built against the old `distutils` module, which was **removed in Python 3.12**. Attempting to install basicsr on 3.12+ produces a build error. Until basicsr releases an updated build system, 3.11 is required for this stack. PyTorch itself supports 3.12/3.13 fine — it's purely a basicsr/realesrgan/gfpgan constraint.

---

## 1. Create Virtual Environment

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

---

## 2. Install PyTorch with CUDA First

Always install PyTorch before requirements.txt — order matters.

```powershell
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu130
```

Verify:
```powershell
python -c "import torch; print(torch.cuda.is_available())"
# Should print: True
```

---

## 3. Install Requirements

```powershell
pip install -r requirements.txt
```

---

## 4. Apply basicsr Patch (required for realesrgan)

basicsr has a known incompatibility with newer torchvision. After installing, apply this one-line patch:

```powershell
# Find the file
$file = ".venv\Lib\site-packages\basicsr\data\degradations.py"

# Apply the fix
(Get-Content $file) -replace 'from torchvision.transforms.functional_tensor import rgb_to_grayscale', 'from torchvision.transforms.functional import rgb_to_grayscale' | Set-Content $file

# Verify
python -c "import basicsr; print('basicsr ok')"
```

---

## 5. Optional: Install carvekit (heavier, best edge quality)

carvekit is not in requirements.txt by default — it pulls in heavy dependencies.

```powershell
pip install carvekit
```

---

## 6. Optional: Install CodeFormer

CodeFormer requires a separate install step:

```powershell
pip install codeformer-pytorch
```

---

## 7. Create Folder Structure

```powershell
New-Item -ItemType Directory -Force input, output\upscaled, output\bg_removed, output\enhanced, models\realesrgan, models\gfpgan, models\codeformer
```

---

## 8. Model Downloads

Models are auto-downloaded on first use. To pre-download manually:

| Model                      | Size   | Script                              |
| -------------------------- | ------ | ----------------------------------- |
| RealESRGAN_x4plus.pth      | ~64MB  | upscale.py                          |
| RealESRGAN_x4plus_netD.pth | ~64MB  | upscale.py --engine realesrgan_face |
| GFPGANv1.4.pth             | ~332MB | enhance.py --engine gfpgan          |
| codeformer.pth             | ~375MB | enhance.py --engine codeformer      |

All models download to their respective `models/` subfolder automatically.

---

## Verify Installation

```powershell
python -c "from realesrgan import RealESRGANer; print('realesrgan ok')"
python -c "import rembg; print('rembg ok')"
python -c "import gfpgan; print('gfpgan ok')"
```
