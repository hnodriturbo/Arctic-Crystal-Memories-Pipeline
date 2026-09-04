<#
File: code/research/extract_cockpit_ci_mesh.ps1
Purpose:
 - Read a local Cockpit CIBF/CRUN `.ci` geometry file with the installed
   Cockpit 3D reader and copy its decoded vertex/index buffer to a neutral
   raw file for interoperability research.

Important context:
 - This script is read-only with respect to the input file.
 - Cockpit's reader creates OpenGL buffers, so a hidden 1x1 OpenTK context is
   required even though the script does not render anything.
 - Run this script through 32-bit Windows PowerShell because CICockpit.exe is
   a 32-bit .NET assembly.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$InputCi,

    [Parameter(Mandatory = $true)]
    [string]$OutputRaw,

    [Parameter(Mandatory = $true)]
    [string]$MetadataPath,

    [string]$CockpitInstall = "C:\Program Files (x86)\Cockpit 3D",

    [switch]$Force
)

$ErrorActionPreference = "Stop"

function Resolve-ExistingFile {
    param([string]$Path, [string]$Label)

    $resolved = Resolve-Path -LiteralPath $Path -ErrorAction Stop
    if (-not (Test-Path -LiteralPath $resolved.Path -PathType Leaf)) {
        throw "$Label is not a file: $Path"
    }
    return $resolved.Path
}

function Resolve-OutputFile {
    param([string]$Path)

    $fullPath = [IO.Path]::GetFullPath($Path)
    $parent = Split-Path -Parent $fullPath
    if (-not (Test-Path -LiteralPath $parent -PathType Container)) {
        New-Item -ItemType Directory -Path $parent | Out-Null
    }
    if ((Test-Path -LiteralPath $fullPath) -and -not $Force) {
        throw "Output already exists; pass -Force to replace it: $fullPath"
    }
    return $fullPath
}

function Get-Sha256Hex {
    param([string]$Path)

    $sha256 = [Security.Cryptography.SHA256]::Create()
    $stream = [IO.File]::OpenRead($Path)
    try {
        $hash = $sha256.ComputeHash($stream)
        return -join ($hash | ForEach-Object { $_.ToString("x2") })
    }
    finally {
        $stream.Dispose()
        $sha256.Dispose()
    }
}

$inputPath = Resolve-ExistingFile -Path $InputCi -Label "Input CI"
$cockpitExe = Resolve-ExistingFile -Path (Join-Path $CockpitInstall "CICockpit.exe") -Label "Cockpit executable"
$openTkDll = Resolve-ExistingFile -Path (Join-Path $CockpitInstall "OpenTK.dll") -Label "OpenTK assembly"
$rawPath = Resolve-OutputFile -Path $OutputRaw
$jsonPath = Resolve-OutputFile -Path $MetadataPath

# Create the graphics context required by Cockpit's geometry constructor.
$openTkAssembly = [Reflection.Assembly]::LoadFrom($openTkDll)
$gameWindowType = $openTkAssembly.GetType("OpenTK.GameWindow", $true)
$window = [Activator]::CreateInstance($gameWindowType, @([int]1, [int]1))
$window.Visible = $false
$window.MakeCurrent()

$geometry = $null
try {
    # Decode the CI with the same local reader that opens it in Cockpit 3D.
    $cockpitAssembly = [Reflection.Assembly]::LoadFrom($cockpitExe)
    $ciType = $cockpitAssembly.GetType("E.U", $true)
    $staticFlags = [Reflection.BindingFlags]"Public,NonPublic,Static"
    $instanceFlags = [Reflection.BindingFlags]"Public,NonPublic,Instance"
    $declaredInstanceFlags = [Reflection.BindingFlags]"Public,NonPublic,Instance,DeclaredOnly"

    $loader = $ciType.GetMethods($staticFlags) |
        Where-Object {
            $_.Name -eq "a" -and
            $_.IsStatic -and
            $_.GetParameters().Count -eq 1 -and
            $_.GetParameters()[0].ParameterType -eq [string]
        } |
        Select-Object -First 1

    if ($null -eq $loader) {
        throw "The installed Cockpit CI reader entry point was not found."
    }

    $geometry = $loader.Invoke($null, @($inputPath))
    if ($null -eq $geometry) {
        throw "Cockpit returned no decoded geometry."
    }

    # C.Z is the geometry base type. Its retained stream contains all float32
    # vertex records followed by all int32 triangle indices.
    $geometryBase = $geometry.GetType()
    while ($null -ne $geometryBase -and $geometryBase.FullName -ne "C.Z") {
        $geometryBase = $geometryBase.BaseType
    }
    if ($null -eq $geometryBase) {
        throw "Cockpit geometry base type was not found."
    }

    $vertexCountMethod = $geometryBase.GetMethod("F", $instanceFlags)
    $strideMethod = $geometryBase.GetMethod("G", $instanceFlags)
    $streamField = $geometryBase.GetFields($declaredInstanceFlags) |
        Where-Object { $_.FieldType -eq [IO.Stream] } |
        Select-Object -First 1

    if ($null -eq $vertexCountMethod -or $null -eq $strideMethod -or $null -eq $streamField) {
        throw "The decoded Cockpit vertex/index buffer could not be located."
    }

    $vertexCount = [int]$vertexCountMethod.Invoke($geometry, @())
    $floatsPerVertex = [int]$strideMethod.Invoke($geometry, @())
    $decodedStream = [IO.Stream]$streamField.GetValue($geometry)
    $vertexBytes = [int64]$vertexCount * $floatsPerVertex * 4
    $remainingBytes = $decodedStream.Length - $vertexBytes

    if ($vertexCount -le 0 -or $floatsPerVertex -lt 3) {
        throw "Decoded geometry dimensions are invalid."
    }
    if ($remainingBytes -le 0 -or ($remainingBytes % 4) -ne 0) {
        throw "Decoded index buffer length is invalid."
    }

    $indexCount = [int64]($remainingBytes / 4)
    if (($indexCount % 3) -ne 0) {
        throw "Decoded index count is not divisible by three."
    }

    # Copy the neutral CPU buffer before disposing Cockpit's temporary object.
    $decodedStream.Position = 0
    $outputStream = [IO.File]::Create($rawPath)
    try {
        $decodedStream.CopyTo($outputStream)
        $outputStream.Flush()
    }
    finally {
        $outputStream.Dispose()
    }

    $metadata = [ordered]@{
        format = "acm-cockpit-ci-decoded-buffer"
        version = 1
        sourceCi = $inputPath
        rawBuffer = $rawPath
        vertexCount = $vertexCount
        floatsPerVertex = $floatsPerVertex
        indexCount = $indexCount
        triangleCount = [int64]($indexCount / 3)
        vertexLayout = @("POSITION_X", "POSITION_Y", "POSITION_Z", "TEXCOORD_U", "TEXCOORD_V", "NORMAL_X", "NORMAL_Y", "NORMAL_Z")
        inputSha256 = Get-Sha256Hex -Path $inputPath
        rawSha256 = Get-Sha256Hex -Path $rawPath
    }
    $metadata | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $jsonPath -Encoding UTF8

    Write-Output ("Decoded {0:N0} vertices and {1:N0} triangles." -f $vertexCount, ($indexCount / 3))
    Write-Output "Raw buffer: $rawPath"
    Write-Output "Metadata: $jsonPath"
}
finally {
    if ($null -ne $geometry -and $geometry -is [IDisposable]) {
        $geometry.Dispose()
    }
    $window.Close()
    $window.Dispose()
}
