#Requires -Version 5.1
<#
.SYNOPSIS
  Baixa DeskRudder-AcessoRemoto-Controle.exe do Release GitHub para embutir no Setup.
#>
[CmdletBinding()]
param(
  [string]$Repo = "lgustavoss/dx-connect",
  [string]$Tag = "acesso-remoto-controle-windows",
  [string]$Asset = "DeskRudder-AcessoRemoto-Controle.exe"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$destDir = Join-Path $root "vendor\remoto-controle"
$dest = Join-Path $destDir $Asset
New-Item -ItemType Directory -Force -Path $destDir | Out-Null

$url = "https://github.com/$Repo/releases/download/$Tag/$Asset"
Write-Host "Baixando $url ..."
Invoke-WebRequest -Uri $url -OutFile $dest -UseBasicParsing
Write-Host "Salvo em $dest ($((Get-Item $dest).Length) bytes)"
