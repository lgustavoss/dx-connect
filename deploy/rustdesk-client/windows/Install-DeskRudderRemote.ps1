#Requires -Version 5.1
<#
.SYNOPSIS
  Fase 0 — instala o RustDesk oficial no Windows e aplica a config do servidor Duplex.

.DESCRIPTION
  Não troca o nome/logo do binário (isso exige build a partir do código — ver README).
  Útil para validar o servidor e distribuir a config sem rebuild.

  Uso (PowerShell como Administrador recomendado):
    .\Install-DeskRudderRemote.ps1
    .\Install-DeskRudderRemote.ps1 -InstallerPath C:\Temp\rustdesk-1.x.x-x86_64.exe
#>
[CmdletBinding()]
param(
  [string]$InstallerPath,
  [string]$ConfigString = "9JiI6ISawFmIsISPJpGdINzMtpmRq1kTHtmV0Y3SSl0ZSlVcthVMq52VLJTOUVla3czSZ9WRrJiOikXZrJCLikzNuAjNx4yN54SMzIiOikXYsVmciwiI5cjLwYTMucTOuEzMiojI0N3boJye",
  [string]$DownloadUrl = ""
)

$ErrorActionPreference = "Stop"

function Find-RustDeskExe {
  $candidates = @(
    "${env:ProgramFiles}\RustDesk\rustdesk.exe",
    "${env:ProgramFiles(x86)}\RustDesk\rustdesk.exe",
    "$env:LOCALAPPDATA\RustDesk\rustdesk.exe"
  )
  foreach ($c in $candidates) {
    if (Test-Path -LiteralPath $c) { return $c }
  }
  $cmd = Get-Command rustdesk.exe -ErrorAction SilentlyContinue
  if ($cmd) { return $cmd.Source }
  return $null
}

Write-Host "DeskRudder — acesso remoto (fase 0: RustDesk oficial + config Duplex)" -ForegroundColor Cyan

$exe = Find-RustDeskExe
if (-not $exe) {
  if (-not $InstallerPath) {
    if (-not $DownloadUrl) {
      Write-Error @"
RustDesk não encontrado e nenhum instalador foi indicado.
1) Baixe o .exe Windows em https://github.com/rustdesk/rustdesk/releases
2) Rode: .\Install-DeskRudderRemote.ps1 -InstallerPath C:\caminho\rustdesk-....exe
Ou passe -DownloadUrl com a URL direta do release.
"@
    }
    $tmp = Join-Path $env:TEMP ("rustdesk-setup-{0}.exe" -f [guid]::NewGuid().ToString("N"))
    Write-Host "Baixando instalador oficial..."
    Invoke-WebRequest -Uri $DownloadUrl -OutFile $tmp
    $InstallerPath = $tmp
  }
  if (-not (Test-Path -LiteralPath $InstallerPath)) {
    Write-Error "Instalador não encontrado: $InstallerPath"
  }
  Write-Host "Instalando $InstallerPath ..."
  # Instalador NSIS do RustDesk costuma aceitar /S (silencioso).
  Start-Process -FilePath $InstallerPath -ArgumentList "/S" -Wait
  Start-Sleep -Seconds 2
  $exe = Find-RustDeskExe
  if (-not $exe) {
    Write-Error "Instalação terminou mas rustdesk.exe não foi encontrado."
  }
}

Write-Host "Aplicando configuração do servidor ($exe --config)..."
& $exe --config $ConfigString
if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) {
  Write-Warning "Código de saída $LASTEXITCODE ao aplicar --config. Confira em Configurações → Rede."
}

Write-Host @"

Pronto.
1. Abra o RustDesk e confirme ID Server = 31.97.160.79
2. A chave pública deve estar preenchida
3. O ID deste computador deve aparecer no painel DeskRudder → Acesso remoto

Marca DeskRudder (nome/logo no .exe) vem na fase 1 (build a partir do código).
"@ -ForegroundColor Green
