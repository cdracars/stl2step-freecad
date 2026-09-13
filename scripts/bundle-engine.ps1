[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string] $EngineDirectory,

    [string] $Destination = (Join-Path $PSScriptRoot '..\Stl2StepFreeCAD\bin\windows-x86_64')
)

$ErrorActionPreference = 'Stop'
$source = (Resolve-Path -LiteralPath $EngineDirectory).Path
$target = if ([System.IO.Path]::IsPathRooted($Destination)) {
    [System.IO.Path]::GetFullPath($Destination)
} else {
    [System.IO.Path]::GetFullPath((Join-Path (Get-Location) $Destination))
}
$executable = Join-Path $source 'stl2step.exe'

if (-not (Test-Path -LiteralPath $executable -PathType Leaf)) {
    throw "Engine directory does not contain stl2step.exe: $source"
}

Write-Warning "This copies a local build for development. Published releases use vendor-engine.ps1 and the canonical upstream checksum manifest."

New-Item -ItemType Directory -Force -Path $target | Out-Null
Get-ChildItem -LiteralPath $target -File | Remove-Item -Force
Get-ChildItem -LiteralPath $source -File | Copy-Item -Destination $target -Force

$versionOutput = & $executable --version
$engineExitCode = $LASTEXITCODE
$version = ($versionOutput | Select-Object -First 1).Trim()
if ($engineExitCode -ne 0 -or $version -notmatch '^stl2step \d+\.\d+\.\d+$') {
    throw "Engine validation failed (exit $engineExitCode): $version"
}

Write-Host "Bundled $version and $((Get-ChildItem -LiteralPath $target -File).Count) runtime files in $target"
