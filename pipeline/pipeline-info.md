# Image Enhancement Pipeline — Info & Q&A

This file is maintained by Claude Code. Each time the user asks an informational question about this pipeline, the answer is logged here under a date header.

---

<!-- New Q&A entries go below this line, newest first -->

---

## 2026-06-06 — Can we use Python 3.12, 3.13, or 3.14 for this pipeline?

**Short answer: No. Python 3.11 is required.**

`basicsr` (a dependency of both `realesrgan` and `gfpgan`) uses Python's `distutils` module in its build system (`setup.py`). `distutils` was **fully removed in Python 3.12**. Attempting to install `basicsr` on Python 3.12+ fails at build time with a `No module named 'distutils'` error.

PyTorch itself supports Python 3.12 and 3.13 fine. The blocker is entirely `basicsr` → `realesrgan` + `gfpgan`. Until those packages migrate to a PEP 517 build (pyproject.toml), Python 3.11 is the ceiling.

**PyTorch CUDA wheels**: Updated from `cu124` to `cu126`. Latest stable (PyTorch 2.12) supports `cu126` (driver 525+) and `cu130` (driver 570+). `cu124` still works but is no longer the recommended choice.
