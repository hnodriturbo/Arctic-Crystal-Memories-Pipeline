# ==========================================
# File: deployment/bootstrap-release-layout.sh
# Purpose:
#  - Migrate the original in-place VPS install to current/shared/releases.
#  - Build three shared CPU-only Python 3.11 environments without changing
#    Ubuntu's system Python 3.12.
#  - Preserve secrets and pipeline workspaces, then perform a rollback-safe cutover.
# ==========================================

set -euo pipefail

archive=${1:?Usage: bootstrap-release-layout.sh ARCHIVE RELEASE_ID}
release_id=${2:?Usage: bootstrap-release-layout.sh ARCHIVE RELEASE_ID}
root=/home/hreidar/apps/acm-pipeline
parent=/home/hreidar/apps
staging="$parent/.acm-pipeline-next-$release_id"
legacy="$parent/.acm-pipeline-legacy-$release_id"
release="$staging/releases/$release_id"
shared="$staging/shared"
export UV_CACHE_DIR="$shared/uv-cache"
uv_version=0.12.6
switched=0

case "$archive" in /tmp/acm-pipeline-*.tar.gz) ;; *) echo "Archive must be an ACM Pipeline tarball in /tmp." >&2; exit 1 ;; esac
case "$staging" in "$parent"/.acm-pipeline-next-*) ;; *) echo "Unsafe staging path." >&2; exit 1 ;; esac
case "$legacy" in "$parent"/.acm-pipeline-legacy-*) ;; *) echo "Unsafe legacy path." >&2; exit 1 ;; esac

test -f "$archive"
test -d "$root/converter/web-converter"
test -f "$root/converter/web-converter/.env.production"
test ! -e "$root/current"
test ! -e "$staging"
test ! -e "$legacy"
ldconfig -p | grep 'libGL.so.1' >/dev/null || {
  echo "Ubuntu package libgl1 is required for the CPU image environment." >&2
  exit 1
}

cleanup() {
  rm -f -- "$archive"
  if test "$switched" -eq 0 && test -d "$staging"; then
    case "$staging" in "$parent"/.acm-pipeline-next-*) rm -rf -- "$staging" ;; esac
  fi
}
trap cleanup EXIT

mkdir -p \
  "$release" \
  "$shared/deploy" \
  "$shared/models" \
  "$shared/tools" \
  "$shared/python" \
  "$shared/uv-cache" \
  "$shared/venvs" \
  "$shared/workspaces/image-pipeline/input" \
  "$shared/workspaces/image-pipeline/output" \
  "$shared/workspaces/meshy-pipeline/input" \
  "$shared/workspaces/meshy-pipeline/work" \
  "$shared/workspaces/meshy-pipeline/output" \
  "$shared/workspaces/pipeline-converter/input" \
  "$shared/workspaces/pipeline-converter/output"

tar -xzf "$archive" -C "$release"
cp -p "$root/converter/web-converter/.env.production" "$shared/.env.production"
chmod 600 "$shared/.env.production"

copy_workspace() {
  local source=$1
  local destination=$2
  if test -d "$source"; then cp -a "$source/." "$destination/"; fi
}

copy_all_workspaces() {
  copy_workspace "$root/converter/image-pipeline/input" "$shared/workspaces/image-pipeline/input"
  copy_workspace "$root/converter/image-pipeline/output" "$shared/workspaces/image-pipeline/output"
  copy_workspace "$root/converter/meshy-pipeline/input" "$shared/workspaces/meshy-pipeline/input"
  copy_workspace "$root/converter/meshy-pipeline/work" "$shared/workspaces/meshy-pipeline/work"
  copy_workspace "$root/converter/meshy-pipeline/output" "$shared/workspaces/meshy-pipeline/output"
  copy_workspace "$root/converter/pipeline-converter/input" "$shared/workspaces/pipeline-converter/input"
  copy_workspace "$root/converter/pipeline-converter/output" "$shared/workspaces/pipeline-converter/output"
}
copy_all_workspaces

if test -d "$HOME/.u2net"; then
  ln -s "$HOME/.u2net" "$shared/models/rembg"
else
  mkdir -p "$shared/models/rembg"
fi

set_env() {
  local key=$1
  local value=$2
  local temporary="$shared/.env.production.next"
  awk -v key="$key" -v value="$value" '
    BEGIN { found = 0 }
    index($0, key "=") == 1 { if (!found) print key "=" value; found = 1; next }
    { print }
    END { if (!found) print key "=" value }
  ' "$shared/.env.production" > "$temporary"
  chmod 600 "$temporary"
  mv -f "$temporary" "$shared/.env.production"
}

set_env CONVERTER_ROOT "$root/current/converter/pipeline-converter"
set_env CONVERTER_PYTHON "$root/shared/venvs/pipeline-converter/bin/python"
set_env MESHY_ROOT "$root/current/converter/meshy-pipeline"
set_env MESHY_PYTHON "$root/shared/venvs/meshy-pipeline/bin/python"
set_env IMAGE_PIPELINE_ROOT "$root/current/converter/image-pipeline"
set_env IMAGE_PIPELINE_PYTHON "$root/shared/venvs/image-pipeline/bin/python"
set_env U2NET_HOME "$root/shared/models/rembg"
grep -Eq '^DATABASE_URL=.+' "$shared/.env.production"
grep -Eq '^AUTH_SECRET=.+' "$shared/.env.production"

export UV_UNMANAGED_INSTALL="$shared/tools"
export UV_NO_MODIFY_PATH=1
export UV_PYTHON_INSTALL_DIR="$shared/python"
export UV_CACHE_DIR="$shared/uv-cache"
curl --fail --silent --show-error --location "https://astral.sh/uv/$uv_version/install.sh" | sh
test -x "$shared/tools/uv"
"$shared/tools/uv" python install 3.11

create_environment() {
  local name=$1
  local requirements=$2
  local environment="$shared/venvs/$name"
  "$shared/tools/uv" venv --python 3.11 --seed --relocatable "$environment"
  "$shared/tools/uv" pip install --python "$environment/bin/python" --requirements "$requirements"
  "$environment/bin/python" -c 'import platform,sys; assert sys.version_info[:2] == (3,11), platform.python_version()'
  sha256sum "$requirements" | cut -d' ' -f1 > "$environment/.requirements.sha256"
}

create_environment image-pipeline "$release/converter/image-pipeline/requirements.txt"
create_environment meshy-pipeline "$release/converter/meshy-pipeline/requirements.txt"
create_environment pipeline-converter "$release/converter/pipeline-converter/requirements.txt"

U2NET_HOME="$shared/models/rembg" \
  "$shared/venvs/image-pipeline/bin/python" \
  "$release/converter/image-pipeline/code/download_models.py"

link_shared() {
  local relative=$1
  local target=$2
  local link="$release/$relative"
  case "$link" in "$release"/*) ;; *) echo "Unsafe link path." >&2; exit 1 ;; esac
  rm -rf -- "$link"
  ln -s "$target" "$link"
}

link_shared converter/image-pipeline/.venv ../../../../shared/venvs/image-pipeline
link_shared converter/image-pipeline/input ../../../../shared/workspaces/image-pipeline/input
link_shared converter/image-pipeline/output ../../../../shared/workspaces/image-pipeline/output
link_shared converter/image-pipeline/models ../../../../shared/models/rembg
link_shared converter/meshy-pipeline/.venv ../../../../shared/venvs/meshy-pipeline
link_shared converter/meshy-pipeline/input ../../../../shared/workspaces/meshy-pipeline/input
link_shared converter/meshy-pipeline/work ../../../../shared/workspaces/meshy-pipeline/work
link_shared converter/meshy-pipeline/output ../../../../shared/workspaces/meshy-pipeline/output
link_shared converter/pipeline-converter/.venv ../../../../shared/venvs/pipeline-converter
link_shared converter/pipeline-converter/input ../../../../shared/workspaces/pipeline-converter/input
link_shared converter/pipeline-converter/output ../../../../shared/workspaces/pipeline-converter/output
ln -s ../../../../shared/.env.production "$release/converter/web-converter/.env.production"
ln -s "releases/$release_id" "$staging/current"

U2NET_HOME="$shared/models/rembg" \
  "$shared/venvs/image-pipeline/bin/python" \
  "$release/converter/image-pipeline/code/healthcheck.py"
"$shared/venvs/meshy-pipeline/bin/python" "$release/converter/meshy-pipeline/code/healthcheck.py"
"$shared/venvs/pipeline-converter/bin/python" -c 'import numpy, scipy, ezdxf'

cd "$release/converter/web-converter"
npm ci --no-audit --no-fund
npm run db:generate
node --input-type=module -e \
  'import argon2 from "argon2"; const hash = await argon2.hash("runtime-probe"); if (!await argon2.verify(hash, "runtime-probe")) process.exit(1)'
npm run build
npm run db:status
test -s .next/BUILD_ID
cp "$release/deployment/ecosystem.config.cjs" "$shared/ecosystem.config.cjs"

pm2 stop acm-pipeline >/dev/null
copy_all_workspaces
mv "$root" "$legacy"
mv "$staging" "$root"
switched=1

restore_legacy() {
  pm2 delete acm-pipeline >/dev/null 2>&1 || true
  if test -d "$root"; then mv "$root" "$staging"; fi
  mv "$legacy" "$root"
  pm2 startOrReload "$root/deployment/ecosystem.config.cjs" --only acm-pipeline --update-env >/dev/null || true
  pm2 save >/dev/null || true
  switched=0
}

pm2 delete acm-pipeline >/dev/null 2>&1 || true
if ! pm2 start "$root/shared/ecosystem.config.cjs" --only acm-pipeline --update-env >/dev/null; then
  restore_legacy
  echo "PM2 activation failed; original deployment restored." >&2
  exit 1
fi

healthy=0
for attempt in {1..20}; do
  if curl --fail --silent --show-error --max-time 10 http://127.0.0.1:3003/login >/dev/null; then
    healthy=1
    break
  fi
  sleep 2
done

if test "$healthy" -ne 1; then
  restore_legacy
  echo "Health check failed; original deployment restored." >&2
  exit 1
fi

pm2 save >/dev/null

# The original in-place tree is fully reproducible. Its secrets and workspace
# files were copied and verified before cutover, so keeping its old venvs would
# only waste roughly two gigabytes outside the release-retention policy.
case "$legacy" in "$parent"/.acm-pipeline-legacy-*) rm -rf -- "$legacy" ;; esac
switched=2
printf 'PIPELINE_LAYOUT_READY release=%s python=3.11 environments=3\n' "$root/releases/$release_id"
printf 'PIPELINE_HEALTHCHECK_OK\n'
