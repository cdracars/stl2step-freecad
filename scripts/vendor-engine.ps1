[CmdletBinding()]
param(
    [string] $Config,
    [string] $Destination
)

$ErrorActionPreference = 'Stop'
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $Config) { $Config = Join-Path $scriptRoot '..\Stl2StepFreeCAD\stl2step_freecad\engine-release.json' }
if (-not $Destination) { $Destination = Join-Path $scriptRoot '..\Stl2StepFreeCAD\bin\windows-x86_64' }
$configPath = (Resolve-Path -LiteralPath $Config).Path
$releaseSpec = Get-Content -Raw -LiteralPath $configPath | ConvertFrom-Json
$repository = $releaseSpec.upstreamRepository
$pinnedAsset = $releaseSpec.assets.'windows-x64'
if (-not $pinnedAsset) { throw "Engine pin has no windows-x64 asset" }
$release = gh api "repos/$repository/releases/tags/$($releaseSpec.tag)" | ConvertFrom-Json

if ($release.tag_name -ne $releaseSpec.tag) {
    throw "Upstream release tag mismatch: expected $($releaseSpec.tag), got $($release.tag_name)"
}
$asset = $release.assets | Where-Object { $_.name -eq $pinnedAsset.name } | Select-Object -First 1
if (-not $asset) { throw "Release $($releaseSpec.tag) does not contain $($pinnedAsset.name)" }
if ([int64]$asset.size -ne [int64]$pinnedAsset.size) {
    throw "Asset size mismatch: expected $($pinnedAsset.size), got $($asset.size)"
}

$tempRoot = Join-Path ([IO.Path]::GetTempPath()) "stl2step-freecad-$([Guid]::NewGuid())"
$download = Join-Path $tempRoot $pinnedAsset.name
$manifestPath = Join-Path $tempRoot 'engine-manifest.json'
$extract = Join-Path $tempRoot 'extract'
New-Item -ItemType Directory -Force -Path $tempRoot, $extract | Out-Null
try {
    gh release download $releaseSpec.tag --repo $repository --pattern $pinnedAsset.name --pattern 'engine-manifest.json' --dir $tempRoot --clobber
    $manifest = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
    $manifestAsset = $manifest.assets.'windows-x64'
    if (-not $manifestAsset) { throw "Upstream manifest has no windows-x64 entry" }
    if ($manifest.tag -ne $releaseSpec.tag -or $manifest.engineVersion -ne $releaseSpec.engineVersion -or
        $manifestAsset.name -ne $pinnedAsset.name -or $manifestAsset.sha256 -ne $pinnedAsset.sha256 -or
        [int64]$manifestAsset.size -ne [int64]$pinnedAsset.size) {
        throw "Pinned engine config does not match upstream engine-manifest.json"
    }
    $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $download).Hash.ToLowerInvariant()
    if ($hash -ne $pinnedAsset.sha256.ToLowerInvariant()) {
        throw "Asset SHA-256 mismatch: expected $($pinnedAsset.sha256), got $hash"
    }

    Expand-Archive -LiteralPath $download -DestinationPath $extract -Force
    $target = if ([IO.Path]::IsPathRooted($Destination)) {
        [IO.Path]::GetFullPath($Destination)
    } else {
        [IO.Path]::GetFullPath((Join-Path (Get-Location) $Destination))
    }
    New-Item -ItemType Directory -Force -Path $target | Out-Null
    Get-ChildItem -LiteralPath $target -Force | Remove-Item -Recurse -Force
    Get-ChildItem -LiteralPath $extract -Force | Copy-Item -Destination $target -Recurse -Force

    $exe = Join-Path $target 'stl2step.exe'
    if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) {
        throw "Verified archive did not contain stl2step.exe"
    }
    $version = (& $exe --version | Out-String).Trim()
    if ($LASTEXITCODE -ne 0 -or $version -ne "stl2step $($releaseSpec.engineVersion)") {
        throw "Engine version validation failed (exit $LASTEXITCODE): $version"
    }
    Write-Host "Verified and vendored $version from $repository/$($releaseSpec.tag)"
}
finally {
    if (Test-Path -LiteralPath $tempRoot) { Remove-Item -LiteralPath $tempRoot -Recurse -Force }
}
