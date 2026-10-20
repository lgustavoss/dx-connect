# Vendor — Acesso Remoto (controle)

O Setup do atendente (`npm run dist` ou o workflow **Desktop DeskRudder Windows**) embute:

`remoto-controle/DeskRudder-AcessoRemoto-Controle.exe`

## Como obter

1. Actions → **Acesso Remoto Atendente (Windows)** (quando o remoto mudar)  
2. Actions → **App Atendente Setup (Windows)** (a cada update do painel — rápido)

Dev local: `npm run baixar-remoto` se o Release controle já existir.

Sem esse arquivo, o NSIS ainda gera o Setup do painel, mas avisa na instalação que o remoto não veio no pacote.
