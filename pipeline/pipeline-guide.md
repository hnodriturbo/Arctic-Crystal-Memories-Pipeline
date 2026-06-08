# K9 Crystal Pipeline — User Guide

## Overview

Three independent operations. Run any in any order, any number of times.
Use the web interface at `http://localhost:3000` or call scripts directly from CLI.

---

## Operations

### Upscale
Scales the long edge to target resolution (default 1800px) using AI upscaling.
Images already at or above the target are skipped automatically.

```bash
python code/upscale.py --file portrait.png
python code/upscale.py --file portrait.png --engine realesrgan_face --target 2400
python code/upscale.py --file portrait.png --engine lanczos   # no AI, instant
```

### Remove Background
Removes the background and outputs a transparent RGBA PNG.

```bash
python code/remove_bg.py --file portrait.png
python code/remove_bg.py --file portrait.png --engine rembg --model birefnet-portrait
python code/remove_bg.py --file portrait.png --engine carvekit
```

### Enhance
AI face restoration or basic color/sharpness adjustment.

```bash
python code/enhance.py --file portrait.png
python code/enhance.py --file portrait.png --engine codeformer --fidelity 0.7
python code/enhance.py --file portrait.png --engine pillow --sharpness 1.4
```

---

## Output folders

| Folder               | Contains                         |
|----------------------|----------------------------------|
| `output/upscaled/`   | `<stem>_upscaled.png`            |
| `output/enhanced/`   | `<stem>_enhanced.png`            |
| `output/bg_removed/` | `<stem>_bg_removed.png` (RGBA)   |

---

## Web Interface

Start the Next.js app:
```bash
cd web
npm run dev
```

Then open `http://localhost:3000`. Sign in with your admin credentials.

- Click an image thumbnail to select it
- Double-click (or click a selected image again) to open the full preview modal
- Press **Process** to go to the processing page
- Choose upscale / enhance / remove bg — configure options — click Run
- Watch live terminal output
- Approve or deny the result; denied outputs are deleted automatically
