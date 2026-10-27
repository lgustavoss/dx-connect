#Requires -Version 5.1
<#
.SYNOPSIS
  Publica DeskRudder-Setup.exe no Release GitHub `desktop-windows` (link /app/download).

.EXAMPLE
  cd desktop
  npm run dist
  .\scripts\publicar-setup-release.ps1
#>
[CmdletBinding()]
param(
  [string]$Repo = "lgustavoss/dx-connect",
  [string]$Tag = "desktop-windows",
  [string]$SetupPath = ""
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
if (-not $SetupPath) {
  $ver = (Get-Content (Join-Path $root "package.json") -Raw | ConvertFrom-Json).version
  $SetupPath = Join-Path $root "release\DeskRudder-Setup-$ver.exe"
}
if (-not (Test-Path -LiteralPath $SetupPath)) {
  Write-Error "Setup nao encontrado: $SetupPath (rode npm run dist antes)."
}

$stableDir = Join-Path $env:TEMP "deskrudder-desktop-release"
New-Item -ItemType Directory -Force -Path $stableDir | Out-Null
$stable = Join-Path $stableDir "DeskRudder-Setup.exe"
Copy-Item -LiteralPath $SetupPath -Destination $stable -Force

if (-not $ver) {
  $ver = (Get-Content (Join-Path $root "package.json") -Raw | ConvertFrom-Json).version
}
$downloadUrl = "https://github.com/$Repo/releases/download/$Tag/DeskRudder-Setup.exe"
$versionJson = Join-Path $stableDir "version.json"
$json = (@{
  version = $ver
  download_url = $downloadUrl
} | ConvertTo-Json) + "`n"
[System.IO.File]::WriteAllText($versionJson, $json)

$notes = @"
DeskRudder Setup para Windows (atendente) **$ver**.

Link amigavel na instancia: ``https://{slug}.deskrudder.com.br/app/download``
"@

if (gh release view $Tag --repo $Repo 2>$null) {
  gh release upload $Tag $stable $versionJson --repo $Repo --clobber
  gh release edit $Tag --repo $Repo --title "DeskRudder App Atendente $ver (Windows)" --notes $notes
} else {
  gh release create $Tag $stable $versionJson --repo $Repo --title "DeskRudder App Atendente $ver (Windows)" --notes $notes --latest=false
}

Write-Host "Publicado: https://github.com/$Repo/releases/download/$Tag/DeskRudder-Setup.exe"
