<#
File: code/research/run_portrait_hrn_moge_refinement.ps1
Purpose:
 - Reproduce the rejected v3.1 portrait heightfield for controlled comparison.
 - Keep every derived mesh, QA image, and manifest in a new isolated run directory.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Source,

    [Parameter(Mandatory = $true)]
    [string]$MogeDepth,

    [Parameter(Mandatory = $true)]
    [string]$HrnObj,

    [Parameter(Mandatory = $true)]
    [string]$OutputDir
)

$ErrorActionPreference = "Stop"
Write-Warning "This script reproduces rejected portrait v3.1. Use it only as an A/B baseline; v3.2 direct-HRN work supersedes it."
$pipelineRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$sourcePath = (Resolve-Path $Source).Path
$mogeDepthPath = (Resolve-Path $MogeDepth).Path
$hrnObjPath = (Resolve-Path $HrnObj).Path
$outputRoot = [System.IO.Path]::GetFullPath($OutputDir)
$basePython = Join-Path $pipelineRoot ".venv\Scripts\python.exe"
$blender = "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"

$assetDir = Join-Path $outputRoot "01-hrn-front-assets"
$fusionDir = Join-Path $outputRoot "02-hrn-moge-fusion"
$meshDir = Join-Path $outputRoot "03-portrait-mesh"
$backfillDir = Join-Path $outputRoot "04-bounded-silhouette-backfill"
$qaDir = Join-Path $outputRoot "05-neutral-qa"

foreach ($required in @($basePython, $blender)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Required portrait-refinement dependency is missing: $required"
    }
}
if ((Test-Path -LiteralPath $outputRoot) -and
    (Get-ChildItem -LiteralPath $outputRoot -Force -ErrorAction SilentlyContinue)) {
    throw "OutputDir must be new or empty so an earlier baseline cannot be overwritten: $outputRoot"
}
New-Item -ItemType Directory -Force -Path $outputRoot | Out-Null

function Invoke-Checked {
    param([string]$Stage, [scriptblock]$Action)
    Write-Host "[portrait-2.5d] START $Stage"
    & $Action
    if ($LASTEXITCODE -ne 0) {
        throw "$Stage failed with exit code $LASTEXITCODE"
    }
    Write-Host "[portrait-2.5d] DONE  $Stage"
}

Invoke-Checked "measure visible source regions and record model routing" {
    & $basePython (Join-Path $PSScriptRoot "analyze_single_person_2_5d_route.py") `
        --source $sourcePath --output (Join-Path $outputRoot "model-route.json")
}

Invoke-Checked "render native HRN front texture and depth" {
    & $blender --background --python (Join-Path $PSScriptRoot "render_hrn_fusion_assets.py") -- `
        --input $hrnObjPath --output-dir $assetDir --resolution 1024
}

Invoke-Checked "register HRN and fuse it with exact-source MoGe depth" {
    & $basePython (Join-Path $PSScriptRoot "fuse_hrn_moge_portrait_depth.py") `
        --source $sourcePath --moge-depth $mogeDepthPath `
        --hrn-texture (Join-Path $assetDir "hrn-front-texture.png") `
        --hrn-depth (Join-Path $assetDir "hrn-front-depth.png") `
        --output-dir $fusionDir
}

New-Item -ItemType Directory -Force -Path $meshDir | Out-Null
$baseMesh = Join-Path $meshDir "portrait-hrn-moge.glb"
Invoke-Checked "build dense source-aligned 2.5D mesh" {
    & $basePython (Join-Path $pipelineRoot "code\depth_to_mesh.py") `
        --depth (Join-Path $fusionDir "hrn-moge-fused-depth.png") `
        --photo $sourcePath --mask-image (Join-Path $fusionDir "primary-subject-mask.png") `
        --output $baseMesh --obj (Join-Path $meshDir "portrait-hrn-moge.obj") `
        --template 100x220x40 --border 0.1 --relief-depth 20 --grid 900 `
        --edge-fillet-mm 0.01 --boundary-fillet-mm 0.01 `
        --flow-depth-output (Join-Path $meshDir "flow-depth.png") --vertex-color luma
}

Invoke-Checked "add bounded multi-ring silhouette backfill" {
    & $basePython (Join-Path $PSScriptRoot "add_portrait_silhouette_backfill.py") `
        --input $baseMesh --output-dir $backfillDir `
        --rings 8 --inset 0.65 --minimum-depth 0.35 --maximum-depth 2.5 `
        --smoothing-iterations 32 --smoothing-weight 0.52
}

$resultPath = Join-Path $backfillDir "portrait-with-silhouette-backfill.glb"
Invoke-Checked "render neutral front, 30-degree, and profile QA" {
    & $blender --background --python (Join-Path $PSScriptRoot "render_source_portrait_qa.py") -- `
        --input $resultPath --output-dir $qaDir --label "portrait-hrn-moge-v31"
}

$manifest = [ordered]@{
    recipe = "portrait-hrn-moge-v31"
    terminology = "3D means source-facing 2.5D unless explicitly stated otherwise"
    model_stack = @(
        "Official ModelScope HRN Head v0.1 (BFM+FLAME)",
        "MoGe-2 ViT-L exact-source metric depth"
    )
    source = $sourcePath
    source_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $sourcePath).Hash.ToLowerInvariant()
    inputs = [ordered]@{
        moge_depth = $mogeDepthPath
        hrn_obj = $hrnObjPath
    }
    parameters = [ordered]@{
        fillet_mm = 0.01
        grid_long_edge = 900
        relief_depth_working_units = 20
        backfill_rings = 8
        backfill_depth_range = @(0.35, 2.5)
    }
    result = $resultPath
    result_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $resultPath).Hash.ToLowerInvariant()
    model_route = (Join-Path $outputRoot "model-route.json")
    qa = $qaDir
}
$manifest | ConvertTo-Json -Depth 6 | Set-Content `
    -LiteralPath (Join-Path $outputRoot "portrait-refinement-manifest.json") -Encoding utf8
Write-Host "[portrait-2.5d] RESULT $resultPath"
