<#
File: converter/2.5D-pipeline/start-local-workbench.ps1
Purpose:
 - Start the loopback pipeline API and local Vinext workbench together.
#>

$pipelineRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$apiPython = Join-Path $pipelineRoot '.venv\Scripts\python.exe'
$siteRoot = Join-Path $pipelineRoot 'local-workbench'
$uiPort = if (Get-NetTCPConnection -LocalPort 3000 -State Listen -ErrorAction SilentlyContinue) { 3001 } else { 3000 }

if (Get-NetTCPConnection -LocalPort $uiPort -State Listen -ErrorAction SilentlyContinue) {
    throw "Local workbench port $uiPort is already in use. Stop the earlier workbench process first."
}

if (-not (Test-Path -LiteralPath $apiPython)) {
    throw "2.5D Python environment was not found: $apiPython"
}

$apiProcess = Start-Process -FilePath $apiPython `
    -ArgumentList @((Join-Path $pipelineRoot 'code\local_workbench_server.py')) `
    -WorkingDirectory $pipelineRoot `
    -WindowStyle Hidden `
    -PassThru

try {
    Write-Host "2.5D local workbench: http://localhost:$uiPort"
    Write-Host 'Press Ctrl+C to stop both services.'
    Push-Location $siteRoot
    npm run dev -- $uiPort
}
finally {
    Pop-Location
    if (-not $apiProcess.HasExited) {
        Stop-Process -Id $apiProcess.Id
    }
}
