<#
File: scripts/deploy-pipeline-vps.ps1
Purpose:
 - Deploy the reviewed ACM Pipeline master commit directly to the VPS.
 - Keep secrets, workspaces, models and three Python 3.11 environments shared.
 - Activate an immutable release atomically and retain current plus two rollbacks.
#>

[CmdletBinding()]
param(
  [string]$SshHost = "acm-vps",
  [string]$RemoteRoot = "/home/hreidar/apps/acm-pipeline"
)

$ErrorActionPreference = "Stop"
$projectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$gitBranch = (& git -C $projectRoot branch --show-current).Trim()
$gitCommit = (& git -C $projectRoot rev-parse --short=8 HEAD).Trim()
$gitStatus = @(& git -C $projectRoot status --porcelain)
$releaseId = "{0}-master-{1}" -f ([DateTime]::UtcNow.ToString("yyyyMMddTHHmmssZ")), $gitCommit
$archivePath = Join-Path ([System.IO.Path]::GetTempPath()) "acm-pipeline-$releaseId.tar.gz"
$remoteUpload = "$RemoteRoot/shared/deploy/$releaseId.tar.gz"

function Invoke-CheckedCommand {
  param([string]$Program, [string[]]$Arguments)
  & $Program @Arguments
  if ($LASTEXITCODE -ne 0) { throw "$Program failed with exit code $LASTEXITCODE." }
}

function Invoke-RemoteScript {
  param([string]$HostName, [string]$Script)
  $temporaryScript = Join-Path ([System.IO.Path]::GetTempPath()) "acm-pipeline-release-$([guid]::NewGuid().ToString('N')).sh"
  $temporaryOutput = Join-Path ([System.IO.Path]::GetTempPath()) "acm-pipeline-release-$([guid]::NewGuid().ToString('N')).out"
  $temporaryError = Join-Path ([System.IO.Path]::GetTempPath()) "acm-pipeline-release-$([guid]::NewGuid().ToString('N')).err"
  # Bash receives the script over stdin. Normalize Windows CRLF first so
  # options such as `pipefail` do not acquire a hidden carriage return.
  $normalizedScript = $Script.Replace("`r`n", "`n").Replace("`r", "`n")
  [System.IO.File]::WriteAllText($temporaryScript, $normalizedScript, [System.Text.UTF8Encoding]::new($false))
  try {
    $process = Start-Process -FilePath (Get-Command ssh).Source `
      -ArgumentList @($HostName, "bash -s") `
      -RedirectStandardInput $temporaryScript `
      -RedirectStandardOutput $temporaryOutput `
      -RedirectStandardError $temporaryError `
      -WindowStyle Hidden `
      -Wait `
      -PassThru

    $standardOutput = if (Test-Path -LiteralPath $temporaryOutput) {
      Get-Content -Raw -LiteralPath $temporaryOutput
    } else { "" }
    $standardError = if (Test-Path -LiteralPath $temporaryError) {
      Get-Content -Raw -LiteralPath $temporaryError
    } else { "" }
    if ($standardOutput) { Write-Host $standardOutput.TrimEnd() }
    if ($process.ExitCode -ne 0) {
      $detail = if ($standardError) { $standardError.Trim() } else { "No remote error output was captured." }
      throw "Remote release failed with exit code $($process.ExitCode): $detail"
    }
  } finally {
    $temporaryRoot = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath())
    foreach ($temporaryFile in @($temporaryScript, $temporaryOutput, $temporaryError)) {
      $resolvedTemporary = [System.IO.Path]::GetFullPath($temporaryFile)
      $leaf = Split-Path $resolvedTemporary -Leaf
      if ($resolvedTemporary.StartsWith($temporaryRoot) -and $leaf -like "acm-pipeline-release-*.*" -and (Test-Path -LiteralPath $resolvedTemporary)) {
        Remove-Item -LiteralPath $resolvedTemporary -Force
      }
    }
  }
}

if ($SshHost -notmatch '^[A-Za-z0-9._-]+$') { throw "Invalid SSH host alias." }
if ($RemoteRoot -ne "/home/hreidar/apps/acm-pipeline") { throw "RemoteRoot must be the isolated ACM Pipeline root." }
if ($gitBranch -ne "master") { throw "Production deploys must run from master, not '$gitBranch'." }
if ($gitStatus.Count -gt 0) { throw "Commit or restore local source changes before deploying master." }

foreach ($entry in @("converter", "deployment")) {
  if (-not (Test-Path -LiteralPath (Join-Path $projectRoot $entry))) {
    throw "Required runtime entry is missing: $entry"
  }
}

try {
  Write-Host "Creating release $releaseId from committed master source."
  Invoke-CheckedCommand "git" @("-C", $projectRoot, "archive", "--format=tar.gz", "--output=$archivePath", "HEAD", "converter", "deployment")

  $archiveListing = & tar -tzf $archivePath
  if ($LASTEXITCODE -ne 0) { throw "Could not inspect the deployment archive." }
  $forbidden = $archiveListing | Where-Object {
    $_ -match '(^|/)\.env($|\.(development|local|production)$)' -or
    $_ -match '(^|/)(node_modules|\.next|\.venv)(/|$)'
  }
  if ($forbidden) { throw "Deployment archive contains forbidden runtime or secret paths." }

  Invoke-CheckedCommand "ssh" @($SshHost, "mkdir -p '$RemoteRoot/shared/deploy'")
  Invoke-CheckedCommand "scp" @($archivePath, "${SshHost}:$remoteUpload")

  $remoteScript = @"
set -euo pipefail
root='$RemoteRoot'
release_id='$releaseId'
archive='$remoteUpload'
releases="`$root/releases"
shared="`$root/shared"
export UV_CACHE_DIR="`$shared/uv-cache"
new_release="`$releases/`$release_id"
current_link="`$root/current"
previous_release=`$(readlink -f "`$current_link")
next_link="`$root/.current-`$release_id"
ecosystem="`$shared/ecosystem.config.cjs"
ecosystem_previous="`$shared/.ecosystem-`$release_id.previous"
switched=0

case "`$new_release" in "`$releases"/*) ;; *) echo 'Unsafe release path.' >&2; exit 1 ;; esac
test -L "`$current_link"
test -d "`$previous_release"
test -f "`$shared/.env.production"
test -x "`$shared/tools/uv"
test -f "`$archive"
test ! -e "`$new_release"

cleanup() {
  rm -f -- "`$archive" "`$next_link" "`$ecosystem_previous"
  if test "`$switched" -eq 0 && test -d "`$new_release"; then
    case "`$new_release" in "`$releases/"*) rm -rf -- "`$new_release" ;; esac
  fi
}
trap cleanup EXIT

mkdir -p -- "`$new_release"
tar -xzf "`$archive" -C "`$new_release"

link_shared_directory() {
  local relative="`$1"
  local destination="`$2"
  local target="`$new_release/`$relative"
  case "`$target" in "`$new_release"/*) ;; *) echo 'Unsafe shared-link target.' >&2; exit 1 ;; esac
  rm -rf -- "`$target"
  ln -s "`$destination" "`$target"
}

link_shared_directory converter/image-pipeline/.venv "`$shared/venvs/image-pipeline"
link_shared_directory converter/image-pipeline/input "`$shared/workspaces/image-pipeline/input"
link_shared_directory converter/image-pipeline/output "`$shared/workspaces/image-pipeline/output"
link_shared_directory converter/image-pipeline/models "`$shared/models/rembg"
link_shared_directory converter/meshy-pipeline/.venv "`$shared/venvs/meshy-pipeline"
link_shared_directory converter/meshy-pipeline/input "`$shared/workspaces/meshy-pipeline/input"
link_shared_directory converter/meshy-pipeline/work "`$shared/workspaces/meshy-pipeline/work"
link_shared_directory converter/meshy-pipeline/output "`$shared/workspaces/meshy-pipeline/output"
link_shared_directory converter/pipeline-converter/.venv "`$shared/venvs/pipeline-converter"
link_shared_directory converter/pipeline-converter/input "`$shared/workspaces/pipeline-converter/input"
link_shared_directory converter/pipeline-converter/output "`$shared/workspaces/pipeline-converter/output"
ln -s "`$shared/.env.production" "`$new_release/converter/web-converter/.env.production"

sync_environment() {
  local name="`$1"
  local requirements="`$2"
  local environment="`$shared/venvs/`$name"
  local required_hash
  local installed_hash=''
  required_hash=`$(sha256sum "`$requirements" | cut -d' ' -f1)
  if test -f "`$environment/.requirements.sha256"; then
    installed_hash=`$(cat "`$environment/.requirements.sha256")
  fi
  if test "`$required_hash" != "`$installed_hash"; then
    "`$shared/tools/uv" pip install --python "`$environment/bin/python" --requirements "`$requirements"
    printf '%s\n' "`$required_hash" > "`$environment/.requirements.sha256"
  fi
}
sync_environment image-pipeline "`$new_release/converter/image-pipeline/requirements.txt"
sync_environment meshy-pipeline "`$new_release/converter/meshy-pipeline/requirements.txt"
sync_environment pipeline-converter "`$new_release/converter/pipeline-converter/requirements.txt"

# All image weights live outside releases and venvs. The downloader is
# idempotent and verifies expected file sizes before making a download visible.
U2NET_HOME="`$shared/models/rembg" \
  "`$shared/venvs/image-pipeline/bin/python" \
  "`$new_release/converter/image-pipeline/code/download_models.py"

verify_python() {
  local python="`$1"
  "`$python" -c 'import platform,sys; assert sys.version_info[:2] == (3,11), platform.python_version()'
}
verify_python "`$shared/venvs/image-pipeline/bin/python"
verify_python "`$shared/venvs/meshy-pipeline/bin/python"
verify_python "`$shared/venvs/pipeline-converter/bin/python"
ldconfig -p | grep 'libGL.so.1' >/dev/null
U2NET_HOME="`$shared/models/rembg" \
  "`$shared/venvs/image-pipeline/bin/python" \
  "`$new_release/converter/image-pipeline/code/healthcheck.py"
"`$shared/venvs/meshy-pipeline/bin/python" "`$new_release/converter/meshy-pipeline/code/healthcheck.py"
"`$shared/venvs/pipeline-converter/bin/python" -c 'import numpy, scipy, ezdxf'

cd "`$new_release/converter/web-converter"
npm ci --no-audit --no-fund
npm run db:generate
node --input-type=module -e 'import argon2 from "argon2"; const hash = await argon2.hash("runtime-probe"); if (!await argon2.verify(hash, "runtime-probe")) process.exit(1)'
npm run build
npm run db:status
test -s .next/BUILD_ID

cp -p -- "`$ecosystem" "`$ecosystem_previous"
cp -- "`$new_release/deployment/ecosystem.config.cjs" "`$ecosystem"
ln -s "`$new_release" "`$next_link"
mv -Tf "`$next_link" "`$current_link"
switched=1

reload_service() {
  pm2 startOrReload "`$ecosystem" --only acm-pipeline --update-env >/dev/null
  pm2 save >/dev/null
}

health_check() {
  local attempt
  for attempt in {1..20}; do
    if curl --fail --silent --show-error --max-time 10 http://127.0.0.1:3003/login >/dev/null; then
      return 0
    fi
    sleep 2
  done
  return 1
}

if ! reload_service || ! health_check; then
  ln -s "`$previous_release" "`$next_link"
  mv -Tf "`$next_link" "`$current_link"
  switched=0
  cp -p -- "`$ecosystem_previous" "`$ecosystem"
  reload_service || true
  health_check || true
  echo 'Health verification failed; previous release restored.' >&2
  exit 1
fi

current_release=`$(readlink -f "`$current_link")
rollback_count=0
while IFS= read -r old_release; do
  test "`$old_release" = "`$current_release" && continue
  if test "`$rollback_count" -lt 2; then
    rollback_count=`$((rollback_count + 1))
    continue
  fi
  case "`$old_release" in "`$releases/"*) rm -rf -- "`$old_release" ;; *) exit 1 ;; esac
done < <(find "`$releases" -mindepth 1 -maxdepth 1 -type d -printf '%T@ %p\n' | sort -nr | cut -d' ' -f2-)

printf 'PIPELINE_RELEASE_ACTIVE release=%s previous=%s\n' "`$new_release" "`$previous_release"
printf 'PIPELINE_HEALTHCHECK_OK\n'
"@
  Invoke-RemoteScript -HostName $SshHost -Script $remoteScript
} finally {
  $resolvedArchive = [System.IO.Path]::GetFullPath($archivePath)
  $temporaryRoot = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath())
  if ($resolvedArchive.StartsWith($temporaryRoot) -and (Split-Path $resolvedArchive -Leaf) -like "acm-pipeline-*-master-*.tar.gz" -and (Test-Path -LiteralPath $resolvedArchive)) {
    Remove-Item -LiteralPath $resolvedArchive -Force
  }
}
