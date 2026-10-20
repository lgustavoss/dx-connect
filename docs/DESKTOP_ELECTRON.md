# App desktop Windows (Electron) — atendente

O app desktop é uma janela Electron que carrega o **painel web da instância** (`https://{slug}.deskrudder.com.br`). Não há build do frontend dentro do app: cada release do painel chega ao desktop sozinho, como no navegador.

**Caminho oficial no PC do atendente:** o Setup `DeskRudder-Setup-*.exe` (não o prompt PWA do Chrome/Edge). No celular o PWA continua disponível.

## Dois produtos Windows

| Produto | Quem usa | Conteúdo |
|---------|----------|----------|
| **DeskRudder Setup** (este doc) | Atendente | Painel Electron + cliente **controle** do Acesso Remoto |
| **DeskRudder Acesso Remoto** (só-recebe) | Posto / PDV | Ver [`RUSTDESK_CLIENT_WINDOWS.md`](RUSTDESK_CLIENT_WINDOWS.md) |

## Diferenças em relação ao PWA (navegador)

| Recurso | PWA | Desktop |
|---------|-----|---------|
| Ícone na bandeja | Não | Sim; fechar a janela só esconde (se marcado no Setup) |
| Iniciar com o Windows | Só pelo Edge (`edge://apps`) | Pergunta **no Setup** + opção no menu da bandeja |
| Alerta da fila com a janela fechada | Para ao fechar | Continua se a opção de bandeja foi aceita no Setup (sem throttling e autoplay liberado) |
| Contador de pendências | Título da aba | Tooltip da bandeja + piscar na barra de tarefas |
| Uma instância | — | Segundo clique no atalho reabre a janela |
| Acesso remoto na frota | `rustdesk://` (precisa cliente instalado) | Prefere `DeskRudder.exe` em `Program Files (x86)\DeskRudder\Acesso Remoto` |
| Cache após deploy | Depende do navegador / SW | Limpa cache + desregistra SW ao abrir; menu **Recarregar painel** |

## Código

- `desktop/src/main.cjs` — janela, bandeja, conta (slug), cache do painel, lançar remoto
- `desktop/src/preload.cjs` — `deskrudder` (conta) + `deskrudderDesktop` (remoto / recarregar)
- `desktop/src/conta.html` + `conta.js` — primeiro acesso / trocar empresa
- `desktop/build/` — ícones e laterais do NSIS; `installer-remoto.nsh` (prefs, atalho do painel, instala o cliente controle)
- `desktop/scripts/gerar_icon_ico.py` — regenera `icon.ico` multi-tamanho a partir de `icon.png` (barra de tarefas)
- `desktop/vendor/remoto-controle/` — colocar `DeskRudder-AcessoRemoto-Controle.exe` antes do `dist` (ver `vendor/README.md`)

Configuração do usuário fica em `%APPDATA%\DeskRudder\config.json` (`slug`, `autostartPerguntado`, `avisoBandejaMostrado`, `alertasNaBandeja`, …). O Setup grava `installer-prefs.json` em `DeskRudder\Painel\` (lido na 1ª abertura). Sessão e `localStorage` do painel ficam em AppData.

## Desenvolvimento

```bash
cd desktop
npm ci
npm start
```

Se o npm bloquear o script de instalação do Electron (`allow-scripts`), baixe o binário manualmente:

```bash
node node_modules/electron/install.js
```

No modo dev, «Iniciar com o Windows» fica desativado e não há `installer-prefs.json` (vale o diálogo de 1ª execução se aplicável). F12 abre o DevTools só no dev; F5 / Ctrl+R limpa cache e recarrega.

## Gerar instalador (atendente)

### Caminho oficial (GitHub Actions)

Três workflows no Actions (nomes na UI):

| Actions (nome) | Quando rodar | Arquivo / Release |
|----------------|--------------|-------------------|
| **Acesso Remoto Cliente (Windows)** | Atualizar remoto do **posto** | `DeskRudder-AcessoRemoto.exe` |
| **Acesso Remoto Atendente (Windows)** | Atualizar remoto do **atendente** (~40–90 min) | `…-Controle.exe` |
| **App Atendente Setup (Windows)** | Atualizar **painel** + embutir o remoto já publicado (rápido) | `DeskRudder-Setup.exe` |

Fluxo típico do atendente:

1. (Só se o remoto mudou ou é a 1.ª vez) **Acesso Remoto Atendente (Windows)**  
2. **App Atendente Setup (Windows)** → Release `desktop-windows` / `/app/download`

Workflows: [desktop](../.github/workflows/desktop-deskrudder-windows.yml) · [remoto atendente](../.github/workflows/acesso-remoto-atendente-windows.yml)

### Local (opcional)

```bash
cd desktop
npm run baixar-remoto   # precisa do Release controle
npm run dist
npm run publicar-setup  # sobe no mesmo Release desktop-windows
```

Saída local: `desktop/release/DeskRudder-Setup-{versão}.exe` (NSIS **por máquina**, pede UAC). Na instalação (pastas irmãs):

1. Painel Electron → `C:\Program Files (x86)\DeskRudder\Painel\`
2. Acesso Remoto (controle) embutido → `C:\Program Files (x86)\DeskRudder\Acesso Remoto\`

O assistente pergunta: **iniciar com o Windows** e **manter na bandeja / alertar com o painel fechado** (defaults Sim). Garante atalho **DeskRudder** na área de trabalho (além do atalho do Acesso Remoto) e abre o painel ao concluir.

Versão do shell em `desktop/package.json`. O cliente remoto tem versão própria (`deploy/rustdesk-client/CLIENT_VERSION`) e banner de update no Release `acesso-remoto-controle-windows`.

### Link no painel (`/app/download`)

Depois do workflow Desktop (ou `publicar-setup`):

`https://{slug}.deskrudder.com.br/app/download`

Nas instâncias: incluir no Nginx o `location = /app/download` (veja `deploy/clients/_template/nginx.site.conf.example`). Sem isso, o SPA em `/app/download` ainda redireciona.

No painel: **Sobre** → Baixar app Windows (e no login, em desktop).

O instalador **não é assinado**: SmartScreen → **Mais informações** → **Executar assim mesmo**. Assinatura Authenticode fica para depois.

## Memória

O shell embute Chromium (como o Chrome). Se o consumo ficar inaceitável no uso real, avaliar migração para WebView2/Tauri mantendo o mesmo painel web.

## Checklist de validação

| # | Cenário | Esperado |
|---|---------|----------|
| 1 | 1ª execução | Tela de conta; conta inexistente mostra erro sem sair da tela |
| 2 | Conta válida | Abre o login do painel da instância |
| 3 | Setup (opções) | Checkboxes iniciar com Windows + alertas na bandeja; `installer-prefs.json` em Painel\ |
| 3b | 1ª execução sem prefs (dev / install antigo) | Pergunta «Abrir o DeskRudder ao iniciar o computador?» |
| 4 | Fechar a janela (X) | Com bandeja ligada: some para a bandeja (aviso na 1ª vez). Com bandeja desligada no Setup: encerra o app (sem ícone perto do relógio) |
| 4b | Área de trabalho após Setup | Atalhos **DeskRudder** (painel) e Acesso Remoto; ícone colorido na barra de tarefas |
| 5 | Clique no ícone da bandeja | Reabre a janela |
| 6 | Chat na fila com a janela escondida | Som da fila + notificação do Windows; tooltip mostra o contador |
| 7 | Menu da bandeja → Iniciar com o Windows | Marca/desmarca; reiniciar o PC abre escondido na bandeja |
| 8 | Abrir o atalho com o app já aberto | Reabre a mesma janela (sem 2ª instância) |
| 9 | Link externo no chat | Abre no navegador padrão |
| 10 | Menu da bandeja → Trocar empresa | Volta para a tela de conta |
| 11 | Menu da bandeja → Sair | Encerra o app e para os alertas |
| 12 | Botão direito numa imagem do chat → Copiar | Imagem colável no Paint/WhatsApp; em texto selecionado copia o texto |
| 13 | Deploy novo no servidor | Melhorias aparecem após abrir o app ou **Recarregar painel** (sem reinstalar o Setup) |
| 14 | Frota → Conectar (com remoto instalado) | Abre janela **DeskRudder - Acesso Remoto** com ID/senha (via `rustdesk://` no `.exe` local) |
| 15 | Navegador no PC | Não sugere «Instale o app» (PWA); no celular continua sugerindo |
| 16 | Setup com remoto no vendor | UAC → painel + `--silent-install` do controle (se falhar, assistente normal) |
| 17 | `/app/download` após workflow Desktop (ou `publicar-setup`) + Nginx | Baixa `DeskRudder-Setup.exe` sem mostrar URL do repositório |
