<#
File: scripts/deploy-pipeline-r2-credentials.ps1
Purpose:
 - Update only the ACM Pipeline R2 credentials in the shared VPS environment.
 - Keep credentials out of command arguments and remove transport files.
#>

[CmdletBinding()]
param(
  [string]$SshHost = "acm-vps",
  [string]$RemoteRoot = "/home/hreidar/apps/acm-pipeline"
)

$ErrorActionPreference = "Stop"
$projectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$sourceEnvironment = Join-Path $projectRoot "converter\web-converter\.env.production"
$transferId = [guid]::NewGuid().ToString("N")
$temporaryRoot = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath())
$localCredentials = Join-Path $temporaryRoot "acm-pipeline-r2-$transferId.env"
$localRemoteScript = Join-Path $temporaryRoot "acm-pipeline-r2-$transferId.sh"
$localStandardOutput = Join-Path $temporaryRoot "acm-pipeline-r2-$transferId.stdout"
$localStandardError = Join-Path $temporaryRoot "acm-pipeline-r2-$transferId.stderr"
$remoteCredentials = "$RemoteRoot/shared/.r2-update-$transferId"

if ($SshHost -notmatch "^[A-Za-z0-9._-]+$") { throw "Invalid SSH host alias." }
if ($RemoteRoot -ne "/home/hreidar/apps/acm-pipeline") {
  throw "RemoteRoot must be the isolated ACM Pipeline root."
}
if (-not (Test-Path -LiteralPath $sourceEnvironment)) {
  throw "Production environment file is missing: $sourceEnvironment"
}

function Remove-VerifiedTemporaryFile {
  param([string]$Path, [string]$Pattern)

  if (-not (Test-Path -LiteralPath $Path)) { return }
  $resolved = [System.IO.Path]::GetFullPath($Path)
  if (-not $resolved.StartsWith($temporaryRoot) -or (Split-Path $resolved -Leaf) -notlike $Pattern) {
    throw "Refusing to remove an unexpected temporary path: $resolved"
  }
  Remove-Item -LiteralPath $resolved -Force
}

try {
  $credentialLines = Get-Content -LiteralPath $sourceEnvironment | Where-Object {
    $_ -match "^R2_PIPELINE_(ACCESS_KEY_ID|SECRET_ACCESS_KEY)="
  }

  if ($credentialLines.Count -ne 2) {
    throw "Expected exactly two R2 credential lines in .env.production."
  }

  $accessKey = ($credentialLines | Where-Object { $_ -match "^R2_PIPELINE_ACCESS_KEY_ID=" }) -replace "^[^=]+=", ""
  $secretKey = ($credentialLines | Where-Object { $_ -match "^R2_PIPELINE_SECRET_ACCESS_KEY=" }) -replace "^[^=]+=", ""
  if ($accessKey -notmatch "^[A-Za-z0-9]{32}$" -or $secretKey -notmatch "^[A-Za-z0-9]{64}$") {
    throw "The R2 credentials do not have the expected format."
  }

  [System.IO.File]::WriteAllText(
    $localCredentials,
    (($credentialLines -join "`n") + "`n"),
    [System.Text.UTF8Encoding]::new($false)
  )

  & scp $localCredentials "${SshHost}:$remoteCredentials"
  if ($LASTEXITCODE -ne 0) { throw "R2 credential transfer failed." }

  $remoteScript = @"
set -euo pipefail
root='$RemoteRoot'
credentials='$remoteCredentials'
environment="`$root/shared/.env.production"
replacement="`$root/shared/.env.production.r2-$transferId"

cleanup() {
  rm -f -- "`$credentials" "`$replacement"
}
trap cleanup EXIT

test -f "`$environment"
test -f "`$credentials"
chmod 600 "`$credentials"

access_key=`$(sed -n 's/^R2_PIPELINE_ACCESS_KEY_ID=//p' "`$credentials")
secret_key=`$(sed -n 's/^R2_PIPELINE_SECRET_ACCESS_KEY=//p' "`$credentials")
test "`$(printf '%s' "`$access_key" | wc -c)" -eq 32
test "`$(printf '%s' "`$secret_key" | wc -c)" -eq 64

awk -v access_key="`$access_key" -v secret_key="`$secret_key" '
  BEGIN { access_count = 0; secret_count = 0 }
  /^R2_PIPELINE_ACCESS_KEY_ID=/ {
    print "R2_PIPELINE_ACCESS_KEY_ID=" access_key
    access_count++
    next
  }
  /^R2_PIPELINE_SECRET_ACCESS_KEY=/ {
    print "R2_PIPELINE_SECRET_ACCESS_KEY=" secret_key
    secret_count++
    next
  }
  { print }
  END {
    if (access_count != 1 || secret_count != 1) exit 42
  }
' "`$environment" > "`$replacement"

chmod 600 "`$replacement"
mv -f -- "`$replacement" "`$environment"
pm2 restart acm-pipeline --update-env >/dev/null
pm2 save >/dev/null
printf 'PIPELINE_R2_ENV_UPDATED\n'
"@

  [System.IO.File]::WriteAllText(
    $localRemoteScript,
    $remoteScript,
    [System.Text.UTF8Encoding]::new($false)
  )

  $process = Start-Process -FilePath (Get-Command ssh).Source `
    -ArgumentList @($SshHost, "bash -s") `
    -RedirectStandardInput $localRemoteScript `
    -RedirectStandardOutput $localStandardOutput `
    -RedirectStandardError $localStandardError `
    -WindowStyle Hidden `
    -Wait `
    -PassThru
  $remoteOutput = if (Test-Path -LiteralPath $localStandardOutput) {
    Get-Content -LiteralPath $localStandardOutput -Raw
  } else { "" }
  $remoteError = if (Test-Path -LiteralPath $localStandardError) {
    Get-Content -LiteralPath $localStandardError -Raw
  } else { "" }
  if ($process.ExitCode -ne 0) {
    throw "Remote R2 environment update failed with exit code $($process.ExitCode). $remoteError"
  }
  if ($remoteOutput) { Write-Host $remoteOutput.Trim() }
} finally {
  Remove-VerifiedTemporaryFile -Path $localCredentials -Pattern "acm-pipeline-r2-*.env"
  Remove-VerifiedTemporaryFile -Path $localRemoteScript -Pattern "acm-pipeline-r2-*.sh"
  Remove-VerifiedTemporaryFile -Path $localStandardOutput -Pattern "acm-pipeline-r2-*.stdout"
  Remove-VerifiedTemporaryFile -Path $localStandardError -Pattern "acm-pipeline-r2-*.stderr"
}

Write-Host "ACM Pipeline R2 credentials updated on the VPS."
