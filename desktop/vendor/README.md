# Vendor — Acesso Remoto (controle)

O Setup do atendente (`npm run dist` ou o workflow **Desktop DeskRudder Windows**) embute:

`remoto-controle/DeskRudder-AcessoRemoto-Controle.exe`

## Como obter

**Preferido:** Actions → **Desktop DeskRudder Windows** (baixa o controle sozinho e gera o Setup).

Manual:

1. Actions → **RustDesk DeskRudder Windows** → **profile = controle**
2. Na pasta `desktop/`: `npm run baixar-remoto` (ou o script `scripts/baixar-remoto-controle.ps1`)

Sem esse arquivo, o NSIS ainda gera o Setup do painel, mas avisa na instalação que o remoto não veio no pacote.
