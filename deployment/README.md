<!--
File: deployment/README.md
Purpose:
 - Document the production runtime and release policy for pipeline.acm.is.
-->

# `pipeline.acm.is` production runtime

The website is deployed from the reviewed local checkout directly to the ACM
VPS. Git and GitHub are not part of the deployment path.

## Runtime layout

```text
/home/hreidar/apps/acm-pipeline/
├── current -> releases/<active-release>
├── releases/                         immutable application releases (max 3)
└── shared/
    ├── .env.production               production secrets, mode 0600
    ├── ecosystem.config.cjs          stable PM2 configuration
    ├── models/rembg -> ~/.u2net      all ten shared image weights
    ├── python/                       uv-managed CPython 3.11
    ├── tools/blender/                shared Blender 4.5 LTS conversion runtime
    ├── tools/uv                      user-scoped uv binary
    ├── uv-cache/                     shared package/download cache
    ├── venvs/
    │   ├── image-pipeline/           rembg + CPU Torch/ONNX/GFPGAN/Real-ESRGAN
    │   ├── meshy-pipeline/           lightweight API diagnostics
    │   └── pipeline-converter/       numpy/scipy/ezdxf conversion
    └── workspaces/                   uploads, work files and generated output
```

Ubuntu 24.04's system Python 3.12 is deliberately left untouched. The three
pipeline environments use uv-managed Python 3.11 and are shared between
releases because their requirements change much less often than the web app.
No CUDA or `onnxruntime-gpu` package belongs on this VPS. Torch is installed
only from PyTorch's explicit `+cpu` wheels. Install Ubuntu's small OpenCV
runtime prerequisites once before the first image-AI/model-converter deployment:

```bash
sudo apt-get install --no-install-recommends libgl1 libxrender1 libxfixes3 libxi6 libsm6 libice6 x11-common
```

## Deploy from the local source of truth

From PowerShell in the repository root:

```powershell
.\scripts\deploy-pipeline-vps.ps1
```

For an explicitly reviewed local release before the user's manual commit:

```powershell
.\scripts\deploy-pipeline-vps.ps1 -DeployWorkingTree
```

This packages only non-ignored local changes under `converter/` and
`deployment/`; it does not modify Git state or contact GitHub.

The script creates a secret-free archive, rejects `.env`, `node_modules`,
`.next`, `.venv` and customer workspace content, then transfers it over SSH.
The VPS builds an inactive release, validates all three interpreters and the
database schema, atomically switches `current`, recreates only the
`acm-pipeline` PM2 process and checks the login route. Recreating that process
is intentional because PM2 otherwise retains an obsolete absolute script/cwd
after an application-folder rename. A failed health check restores the
previous release. Successful deployments retain the active release and at
most two rollbacks.

## Services and limits

| Component | Production value |
| --- | --- |
| Public URL | `https://pipeline.acm.is` |
| PM2 process | `acm-pipeline` |
| Next.js origin | `127.0.0.1:3003` |
| Nginx site | `/etc/nginx/sites-available/pipeline.acm.is` |
| Shared environment | `/home/hreidar/apps/acm-pipeline/shared/.env.production` |
| Upload limit through Cloudflare | 100 MB |

Nginx disables proxy buffering and uses one-hour read/send timeouts so SSE
progress and long conversions are not cut off. Larger input files should be
copied by SSH/SFTP into the appropriate shared workspace.

## Verification

```bash
readlink -f /home/hreidar/apps/acm-pipeline/current
pm2 status acm-pipeline
curl -fsS http://127.0.0.1:3003/login >/dev/null
sudo nginx -t

for env in image-pipeline meshy-pipeline pipeline-converter; do
  /home/hreidar/apps/acm-pipeline/shared/venvs/$env/bin/python -c \
    'import platform; print(platform.python_version())'
done

/home/hreidar/apps/acm-pipeline/shared/tools/blender/blender --background --version
```

The public root redirects signed-out users to Auth.js login. Meshy's webhook
route stays public but authenticates its payload using the configured webhook
secret or an already-known task identifier.
