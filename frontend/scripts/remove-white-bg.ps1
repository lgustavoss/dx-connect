# Regenera monograma v2 com fundo transparente (fonte: deskrudder-logo-ref-v2-black.png)
# Requer: npm install sharp to-ico --no-save
# Uso: node scripts/build-mark-alpha.mjs
param()
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root
node scripts/build-mark-alpha.mjs