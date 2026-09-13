<#
File: code/research/run_icon_windows.ps1
Purpose:
 - Run the official ICON source in the isolated Windows Python 3.8 / CUDA 11.6 stack.
 - Layer ICON-only packages ahead of the frozen ECON environment without modifying it.
#>

[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$IconArguments
)

$ErrorActionPreference = "Stop"

# Resolve all model and runtime locations from the local pipeline root.
$pipelineRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$iconRoot = Join-Path $pipelineRoot "Models\research\ICON\source\ICON-official"
$runtimeRoot = Join-Path $pipelineRoot "Models\runtimes\econ-py38-cu116"
$overlayRoot = Join-Path $pipelineRoot "Models\runtimes\icon-py38-cu116-overlay\site-packages"
$cudaRoot = Join-Path $pipelineRoot "Models\runtimes\cuda-11.6.2"
$pythonExecutable = Join-Path $runtimeRoot "Scripts\python.exe"
$torchLibraryPath = Join-Path $runtimeRoot "Lib\site-packages\torch\lib"
$pytorch3dSource = Join-Path $pipelineRoot "Models\research\PyTorch3D\source\pytorch3d-3388d3f0aa6bc44fe704fca78d11743a0fcac38c"
$huggingFaceHome = Join-Path $pipelineRoot "Models\cache\huggingface"

foreach ($requiredPath in @(
    $iconRoot,
    (Join-Path $iconRoot "data"),
    $pythonExecutable,
    $overlayRoot,
    $cudaRoot,
    $torchLibraryPath,
    $pytorch3dSource
)) {
    if (-not (Test-Path -LiteralPath $requiredPath)) {
        throw "Required ICON runtime path is missing: $requiredPath"
    }
}

# Keep every runtime override local to this launcher process and ICON itself.
$env:CUDA_HOME = $cudaRoot
$env:CUDA_PATH = $cudaRoot
$env:HF_HOME = $huggingFaceHome
$env:PYTHONPATH = "$overlayRoot;$pytorch3dSource;$iconRoot"
$env:PATH = "$(Join-Path $cudaRoot 'bin');$torchLibraryPath;$(Join-Path $runtimeRoot 'Scripts');$env:PATH"

Push-Location $iconRoot
try {
    & $pythonExecutable -m apps.infer @IconArguments
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
