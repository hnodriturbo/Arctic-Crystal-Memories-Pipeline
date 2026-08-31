<#
File: code/research/run_econ_windows.ps1
Purpose:
 - Run ECON inside the isolated Windows Python 3.8 / CUDA 11.6 environment.
 - Add the local CUDA, Torch, and compiled-extension directories without changing system PATH.
#>

[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$EconArguments
)

$ErrorActionPreference = "Stop"

# Resolve every runtime path from this repository so the launcher remains local-first.
$pipelineRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$econRoot = Join-Path $pipelineRoot "Models\research\ECON"
$runtimeRoot = Join-Path $pipelineRoot "Models\runtimes\econ-py38-cu116"
$cudaRoot = Join-Path $pipelineRoot "Models\runtimes\cuda-11.6.2"
$pythonExecutable = Join-Path $runtimeRoot "Scripts\python.exe"
$torchLibraryPath = Join-Path $runtimeRoot "Lib\site-packages\torch\lib"
$pytorch3dSource = Join-Path $pipelineRoot "Models\research\PyTorch3D\source\pytorch3d-3388d3f0aa6bc44fe704fca78d11743a0fcac38c"
$huggingFaceHome = Join-Path $pipelineRoot "Models\cache\huggingface"
$sapiensAssets = Join-Path $pipelineRoot "Models\research\ECON\data\sapiens\assets"

foreach ($requiredPath in @($econRoot, $pythonExecutable, $cudaRoot, $torchLibraryPath, $pytorch3dSource)) {
    if (-not (Test-Path -LiteralPath $requiredPath)) {
        throw "Required ECON runtime path is missing: $requiredPath"
    }
}

# Keep all runtime overrides in this process and its child Python process only.
$env:CUDA_HOME = $cudaRoot
$env:CUDA_PATH = $cudaRoot
$env:NVCC_PREPEND_FLAGS = "-allow-unsupported-compiler -D_ALLOW_COMPILER_AND_STL_VERSION_MISMATCH"
$env:CUPY_ACCELERATORS = ""
$env:HF_HOME = $huggingFaceHome
$env:ECON_SAPIENS_ASSETS_DIR = $sapiensAssets
$env:PYTHONPATH = "$pytorch3dSource;$econRoot"
$env:PATH = "$(Join-Path $cudaRoot 'bin');$torchLibraryPath;$(Join-Path $runtimeRoot 'Scripts');$env:PATH"

Push-Location $econRoot
try {
    & $pythonExecutable -m apps.infer @EconArguments
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
