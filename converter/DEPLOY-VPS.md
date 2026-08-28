<!--
File: converter/DEPLOY-VPS.md
Purpose:
 - Explain how all three pipelines run together on the Ubuntu 24.04 VPS.
-->

# Deploying ACM Pipeline to `pipeline.acm.is`

The deployable unit is the complete `converter/` tree:

1. `image-pipeline` prepares uploads locally with CPU-safe Python tools.
2. `meshy-pipeline` owns direct Meshy uploads, job work and diagnostics.
3. `pipeline-converter` turns Meshy or uploaded models into OBJ, DXF and the
   point-cloud formats used by the engraving workflow.
4. `web-converter` is the authenticated Next.js operator interface joining the
   three pipelines together.

## Python policy

Production has exactly three isolated Python 3.11 environments under
`shared/venvs`. A user-scoped uv install downloads and manages CPython 3.11;
Ubuntu's system Python 3.12 is never replaced or modified.

| Environment | Packages and purpose |
| --- | --- |
| `image-pipeline` | `rembg[cpu]`, `onnxruntime`, Pillow, NumPy and SciPy |
| `meshy-pipeline` | `requests` and a small API/workspace health check |
| `pipeline-converter` | NumPy, SciPy, ezdxf, rich and tqdm |

Never install `requirements-gpu.txt`, CUDA, Torch or `onnxruntime-gpu` on this
VPS. `upscale.py` and `enhance.py` intentionally fall back to Lanczos and
Pillow. The rembg ONNX model cache is shared instead of copied into each
release.

## Environment paths

Production secrets live only in `shared/.env.production`. These path values
must point through `current` or directly to the shared interpreters:

```dotenv
CONVERTER_ROOT=/home/hreidar/apps/acm-pipeline/current/converter/pipeline-converter
CONVERTER_PYTHON=/home/hreidar/apps/acm-pipeline/shared/venvs/pipeline-converter/bin/python
MESHY_ROOT=/home/hreidar/apps/acm-pipeline/current/converter/meshy-pipeline
MESHY_PYTHON=/home/hreidar/apps/acm-pipeline/shared/venvs/meshy-pipeline/bin/python
IMAGE_PIPELINE_ROOT=/home/hreidar/apps/acm-pipeline/current/converter/image-pipeline
IMAGE_PIPELINE_PYTHON=/home/hreidar/apps/acm-pipeline/shared/venvs/image-pipeline/bin/python
U2NET_HOME=/home/hreidar/apps/acm-pipeline/shared/models/rembg
```

The same file also carries `DATABASE_URL`, Meshy/OpenAI/R2 credentials and the
Auth.js settings. It is never included in a release archive.

## Normal deployment

Run from the local repository root in PowerShell:

```powershell
.\scripts\deploy-pipeline-vps.ps1
```

This is a local-to-VPS transfer, not a Git deployment. It builds before the
atomic switch, automatically rolls back a failed start and keeps no more than
three releases: current plus two rollback candidates.

## Production checks

```bash
cd /home/hreidar/apps/acm-pipeline/current/converter/web-converter
npm run db:status
pm2 status acm-pipeline
curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:3003/login
curl -sS -X POST http://127.0.0.1:3003/webhooks/meshy \
  -H 'Content-Type: application/json' -d '{}'
sudo nginx -t
```

Expected results are an up-to-date migration, PM2 `online`, HTTP 200 for the
login page, and HTTP 400 for the deliberately incomplete webhook probe.
