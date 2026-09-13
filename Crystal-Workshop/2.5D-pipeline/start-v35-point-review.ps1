<#
Purpose:
 - Open the preserved v3.5 point/mesh review on loopback without external services.
 - Start a hidden local server only when the expected review is not already running.
#>
param([int]$Port = 8427)
$ErrorActionPreference = 'Stop'
$reviewRoot = Join-Path $PSScriptRoot 'output/research/2026-09-05-v35-point-review'
$reviewPython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
$reviewUrl = "http://127.0.0.1:$Port/"
if (-not (Test-Path -LiteralPath (Join-Path $reviewRoot 'catalog.json'))) { throw 'Review artifacts are missing.' }
$reviewResponding = $false
try {
    $reviewCatalog = Invoke-RestMethod -Uri ($reviewUrl + 'catalog.json') -TimeoutSec 2
    $reviewResponding = @($reviewCatalog | Where-Object id -eq 'pabbi-e2').Count -eq 1
    if (-not $reviewResponding) { throw 'The port contains a different application.' }
} catch {
    if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) { throw "Port $Port is occupied by another application. Choose a different -Port." }
}
if (-not $reviewResponding) {
    $reviewArguments = @('-m','http.server',"$Port",'--bind','127.0.0.1','--directory',('"' + $reviewRoot + '"'))
    $reviewProcess = Start-Process -FilePath $reviewPython -ArgumentList $reviewArguments -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $reviewRoot 'server.log') -RedirectStandardError (Join-Path $reviewRoot 'server-error.log')
    $reviewProcess.Id | Set-Content -LiteralPath (Join-Path $reviewRoot 'server.pid')
    for ($reviewAttempt = 0; $reviewAttempt -lt 20; $reviewAttempt++) {
        try { Invoke-RestMethod -Uri ($reviewUrl + 'catalog.json') -TimeoutSec 1 | Out-Null; $reviewResponding = $true; break } catch { Start-Sleep -Milliseconds 200 }
    }
    if (-not $reviewResponding) { throw 'The local review server did not become ready; see server-error.log.' }
}
Start-Process $reviewUrl
