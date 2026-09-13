<#
File: code/research/run_icon_bni_windows.ps1
Purpose:
 - Run ICON front-normal integration with ECON's d-BiNI solver on Windows.
 - Reuse the isolated ECON Python/CUDA environment without modifying it.
#>

[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$IntegrationArguments
)

$ErrorActionPreference = "Stop"

# Resolve all dependencies locally and expose them only to the child process.
$pipelineRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$econRoot = Join-Path $pipelineRoot "Models\research\ECON"
$runtimeRoot = Join-Path $pipelineRoot "Models\runtimes\econ-py38-cu116"
$cudaRoot = Join-Path $pipelineRoot "Models\runtimes\cuda-11.6.2"
$pythonExecutable = Join-Path $runtimeRoot "Scripts\python.exe"
$torchLibraryPath = Join-Path $runtimeRoot "Lib\site-packages\torch\lib"
$pytorch3dSource = Join-Path $pipelineRoot "Models\research\PyTorch3D\source\pytorch3d-3388d3f0aa6bc44fe704fca78d11743a0fcac38c"
$integrationScript = Join-Path $pipelineRoot "code\research\integrate_icon_front_bni.py"

foreach ($requiredPath in @(
    $econRoot,
    $pythonExecutable,
    $cudaRoot,
    $torchLibraryPath,
    $pytorch3dSource,
    $integrationScript
)) {
    if (-not (Test-Path -LiteralPath $requiredPath)) {
        throw "Required ICON d-BiNI path is missing: $requiredPath"
    }
}

$env:CUDA_HOME = $cudaRoot
$env:CUDA_PATH = $cudaRoot
$env:CUPY_ACCELERATORS = ""
$env:PYTHONPATH = "$pytorch3dSource;$econRoot"
$env:PATH = "$(Join-Path $cudaRoot 'bin');$torchLibraryPath;$(Join-Path $runtimeRoot 'Scripts');$env:PATH"

Push-Location $econRoot
try {
    & $pythonExecutable $integrationScript @IntegrationArguments
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
