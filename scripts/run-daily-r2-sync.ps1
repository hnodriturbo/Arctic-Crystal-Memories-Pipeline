<#
File: scripts/run-daily-r2-sync.ps1
Purpose:
 - Run the existing Expenses backup and Cockpit3D backup independently each day.
 - Preserve both logs and return failure if either backup fails.
#>
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$workspaceRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$workshop = Join-Path $workspaceRoot 'ACM-Pipeline\Crystal-Workshop\ACM-Web-Pipeline'
$expenseScript = Join-Path $workspaceRoot 'ACM-Web-Bookkeeping\scripts\run-local-expense-sync.ps1'
$logRoot = Join-Path $workspaceRoot 'ACM-Pipeline\deployment\artifacts\r2-sync-logs'
[IO.Directory]::CreateDirectory($logRoot) | Out-Null
$stamp = [DateTime]::Now.ToString('yyyyMMdd-HHmmss')
$failed = $false

# Separate processes prevent an exit in one runner from cancelling the other backup.
function Invoke-Backup {
  param([string]$Name, [string]$Executable, [string[]]$Arguments, [string]$Directory)
  $output = Join-Path $logRoot "$stamp-$Name.log"
  $errors = Join-Path $logRoot "$stamp-$Name.err.log"
  try {
    $process = Start-Process -FilePath $Executable -ArgumentList $Arguments -WorkingDirectory $Directory -WindowStyle Hidden -Wait -PassThru -RedirectStandardOutput $output -RedirectStandardError $errors
    Write-Output "$Name exit=$($process.ExitCode) log=$output"
    return ($process.ExitCode -eq 0)
  } catch {
    Write-Output "$Name failed to start."
    return $false
  }
}
$expenseResult = @(Invoke-Backup 'expenses' "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe" @('-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', "`"$expenseScript`"") $workspaceRoot)
$sceneResult = @(Invoke-Backup 'cockpit3d' (Get-Command node).Source @('--env-file=.env.local', 'scripts/sync-scene-files.mjs') $workshop)
$expenseResult | Where-Object { $_ -is [string] } | Write-Output
$sceneResult | Where-Object { $_ -is [string] } | Write-Output
if ($expenseResult[-1] -ne $true -or $sceneResult[-1] -ne $true) { exit 1 }
Write-Output 'DAILY_R2_BACKUP_OK'
exit 0
