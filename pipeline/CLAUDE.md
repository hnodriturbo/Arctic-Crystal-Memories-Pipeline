# K9 Crystal Pipeline — Python Backend

## Purpose

This pipeline provides three independent image processing operations,
each accessible from the Next.js web interface at `../web/`.

| Script         | Operation   | Output folder        | Web trigger                  |
|----------------|-------------|----------------------|------------------------------|
| `remove_bg.py` | Remove BG   | `output/bg_removed/` | POST /api/process remove_bg  |
| `upscale.py`   | AI upscale  | `output/upscaled/`   | POST /api/process upscale    |
| `enhance.py`   | Enhancement | `output/enhanced/`   | POST /api/process enhance    |

Scripts are **independent** — run any in any order, any number of times.

---

## Folder Structure

```
pipeline/
├── input/                  # Drop source images here
├── output/
│   ├── bg_removed/         # RGBA PNGs from remove_bg.py
│   ├── upscaled/           # Upscaled PNGs from upscale.py
│   └── enhanced/           # Enhanced PNGs from enhance.py
├── models/
│   ├── realesrgan/         # Auto-downloaded on first run
│   ├── gfpgan/             # Auto-downloaded on first run
│   └── codeformer/         # Auto-downloaded on first run
├── code/
│   ├── remove_bg.py
│   ├── upscale.py
│   ├── enhance.py
│   ├── codeformer_arch.py  # vendored CodeFormer arch
│   └── vqgan_arch.py       # vendored VQGAN arch
├── CLAUDE.md
├── requirements.txt
└── pipeline-guide.md
```

---

## Web Interface Integration

The web app (`../web/`) spawns scripts via:
```
.venv/Scripts/python.exe code/<script>.py --file <abs_path> [--engine X] [--model X]
```

- Python executable: `.venv/Scripts/python.exe`
- Working directory: `pipeline/`
- Input: absolute path to file in `pipeline/input/`
- Scripts print progress to stdout; errors to stderr
- Web reads SSE stream of stdout/stderr lines live

---

## Key Constraints

- **CUDA required** — RTX 3060 Laptop GPU; do not fall back to CPU silently
- **Python 3.11** (.venv)
- **Alpha channel** — always preserved through all operations
- **Aspect ratio** — never modified in upscale
