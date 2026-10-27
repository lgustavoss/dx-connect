#Requires -Version 5.1
<#
.SYNOPSIS
  Baixa o DeskRemote Atendente v2 e grava como DeskRudder-AcessoRemoto-Controle.exe (nome que o Setup espera).
#>
[CmdletBinding()]
param(
  [string]$Repo = "lgustavoss/dx-connect",
  [string]$Tag = "acesso-remoto-controle-flutter-windows",
  [string]$Asset = "DeskRudder-AcessoRemoto-Controle-Flutter.exe"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$destDir = Join-Path $root "vendor\remoto-controle"
$dest = Join-Path $destDir "DeskRudder-AcessoRemoto-Controle.exe"
New-Item -ItemType Directory -Force -Path $destDir | Out-Null

$url = "https://github.com/$Repo/releases/download/$Tag/$Asset"
Write-Host "Baixando $url ..."
Invoke-WebRequest -Uri $url -OutFile $dest -UseBasicParsing
Write-Host "Salvo em $dest ($((Get-Item $dest).Length) bytes)"
