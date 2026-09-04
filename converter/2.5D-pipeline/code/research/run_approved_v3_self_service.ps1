<#
File: code/research/run_approved_v3_self_service.ps1
Purpose:
 - Re-run the approved PARE -> ICON -> ECON -> MoGe -> depth-skirt v3 recipe.
 - Keep every user image and intermediate artifact inside one isolated local run directory.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Source,

    [Parameter(Mandatory = $true)]
    [string]$OutputDir
)

$ErrorActionPreference = "Stop"
$pipelineRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$sourcePath = (Resolve-Path $Source).Path
$outputRoot = [System.IO.Path]::GetFullPath($OutputDir)
$basePython = Join-Path $pipelineRoot ".venv\Scripts\python.exe"
$geometryPython = Join-Path $pipelineRoot "Models\runtimes\.venv-geometry\Scripts\python.exe"
$econPython = Join-Path $pipelineRoot "Models\runtimes\econ-py38-cu116\Scripts\python.exe"
$iconLauncher = Join-Path $PSScriptRoot "run_icon_windows.ps1"
$bniLauncher = Join-Path $PSScriptRoot "run_icon_bni_windows.ps1"
$iconConfig = Join-Path $pipelineRoot "Models\research\ICON\source\ICON-official\configs\icon-filter.yaml"

$inputDir = Join-Path $outputRoot "01-person-inputs"
$iconOutput = Join-Path $outputRoot "02-icon-pare"
$rawDir = Join-Path $iconOutput "icon-filter\front-data"
$humanSurfaceDir = Join-Path $outputRoot "03-econ-front-surface"
$sourceCameraDir = Join-Path $outputRoot "04-source-camera"
$sceneDepthDir = Join-Path $outputRoot "05-moge-scene-depth"
$sceneFusionDir = Join-Path $outputRoot "06-scene-fusion"
$skirtDir = Join-Path $outputRoot "07-depth-skirt-v3"
$resultPath = Join-Path $outputRoot "relief-crystal.glb"

foreach ($required in @($basePython, $geometryPython, $econPython, $iconLauncher, $bniLauncher, $iconConfig)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Required approved-v3 dependency is missing: $required"
    }
}
New-Item -ItemType Directory -Force -Path $outputRoot | Out-Null

function Invoke-Checked {
    param([string]$Stage, [scriptblock]$Action)
    Write-Host "[approved-v3] START $Stage"
    & $Action
    if ($LASTEXITCODE -ne 0) {
        throw "$Stage failed with exit code $LASTEXITCODE"
    }
    Write-Host "[approved-v3] DONE  $Stage"
}

Invoke-Checked "person detection and ICON canvases" {
    & $econPython (Join-Path $PSScriptRoot "detect_and_prepare_icon_people.py") `
        --source $sourcePath --output-dir $inputDir --device cuda:0
}

$people = Get-Content -LiteralPath (Join-Path $inputDir "people.json") -Raw | ConvertFrom-Json
$subjects = @($people.subjects | ForEach-Object { $_.name })
if ($subjects.Count -lt 1) {
    throw "No safe person input was prepared"
}

Invoke-Checked "PARE and official ICON front tensors" {
    & $iconLauncher -cfg $iconConfig -gpu 0 -in_dir $inputDir -out_dir $iconOutput `
        -hps_type pare -loop_smpl 100 -loop_cloth 0 -vis_freq 1000 `
        -export_front_data -front_data_only
}

Invoke-Checked "ECON d-BiNI adaptive-fillet front surfaces" {
    & $bniLauncher --input-dir $rawDir --raw-dir $rawDir --output-dir $humanSurfaceDir `
        --device cuda:0 --keep-intersections --keep-stretched-faces `
        --fillet-radius-fraction 0.006 --fillet-gradient-quantile 98.5
}

$subjectArguments = @()
foreach ($subject in $subjects) {
    $subjectArguments += @("--subject", $subject)
}
Invoke-Checked "exact source-camera registration" {
    & $basePython (Join-Path $PSScriptRoot "source_camera_fusion.py") `
        --source $sourcePath --raw-dir $rawDir --mesh-dir $humanSurfaceDir `
        --output-dir $sourceCameraDir @subjectArguments
}

$sceneRaw = Join-Path $sceneDepthDir "depth_raw.npy"
Invoke-Checked "MoGe-2 ViT-L exact-source depth" {
    & $geometryPython (Join-Path $pipelineRoot "code\depth_map.py") `
        --input $sourcePath --output (Join-Path $sceneDepthDir "depth.png") `
        --engine moge-2 --moge-model vitl --moge-resolution-level 9 --device cuda `
        --aux-output (Join-Path $sceneDepthDir "geometry") --raw-output $sceneRaw --mask-from-alpha
}

Invoke-Checked "PARE human and MoGe scene fusion" {
    & $basePython (Join-Path $PSScriptRoot "fuse_scene_depth_layers.py") `
        --source $sourcePath --scene-depth-raw $sceneRaw `
        --human-stats (Join-Path $sourceCameraDir "source_camera_fusion_stats.json") `
        --human-mesh-dir $sourceCameraDir --raw-dir $rawDir --output-dir $sceneFusionDir `
        --stride 3 --scene-depth-span 0.35 --boundary-clearance-px 0
}

Invoke-Checked "accepted silhouette depth-skirt v3" {
    & $basePython (Join-Path $PSScriptRoot "add_silhouette_depth_skirts.py") `
        --fusion-dir $sceneFusionDir --scene-depth-raw $sceneRaw --output-dir $skirtDir `
        --minimum-skirt-depth 0.025
}

$combinedInput = Join-Path $skirtDir "both_people_scene_with_depth_skirts.glb"
Invoke-Checked "crystal-tone GLB" {
    & $basePython (Join-Path $PSScriptRoot "recolor_glb_crystal_tone.py") `
        --input $combinedInput --output $resultPath --contrast 1.28 --gamma 0.92
}

$manifest = [ordered]@{
    recipe = "approved-v3-self-service"
    source = $sourcePath
    subjects = $subjects
    stages = [ordered]@{
        people = $inputDir
        icon_pare = $iconOutput
        econ_front = $humanSurfaceDir
        source_camera = $sourceCameraDir
        moge_scene = $sceneDepthDir
        scene_fusion = $sceneFusionDir
        depth_skirt = $skirtDir
    }
    result = $resultPath
}
$manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $outputRoot "approved-v3-manifest.json") -Encoding utf8
Write-Host "[approved-v3] RESULT $resultPath"
