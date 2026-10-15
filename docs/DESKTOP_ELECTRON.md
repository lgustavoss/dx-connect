# App desktop Windows (Electron) — #1130

O app desktop é uma janela Electron que carrega o **painel web da instância** (`https://{slug}.deskrudder.com.br`). Não há build do frontend dentro do app: cada release do painel chega ao desktop sozinho, como no navegador.

Diferenças em relação ao PWA:

| Recurso | PWA | Desktop |
|---------|-----|---------|
| Ícone na bandeja | Não | Sim; fechar a janela só esconde |
| Iniciar com o Windows | Só pelo Edge (`edge://apps`) | Pergunta na 1ª execução + opção no menu da bandeja (abre escondido na bandeja) |
| Alerta da fila com a janela fechada | Para ao fechar | Continua (sem throttling e autoplay liberado) |
| Contador de pendências | Título da aba | Tooltip da bandeja + piscar na barra de tarefas |
| Uma instância | — | Segundo clique no atalho reabre a janela |
| Botão direito | Menu do navegador | Só «Copiar», em imagem ou texto selecionado (nada nos demais lugares) |

## Código

- `desktop/src/main.cjs` — janela, bandeja, iniciar com o Windows, conta (slug), links externos
- `desktop/src/preload.cjs` — ponte só para a tela local de conta (`file:`)
- `desktop/src/conta.html` + `conta.js` — primeiro acesso / trocar empresa
- `desktop/build/` — ícone (`icon.png`, `icon.ico`) e imagens laterais do instalador (`installerSidebar.bmp`, `uninstallerSidebar.bmp`), gerados de `frontend/public/deskrudder-mark-alpha.png` com `python scripts/gerar-icones.py` (Pillow)

Configuração do usuário fica em `%APPDATA%\DeskRudder\config.json` (`slug`, `autostartPerguntado`, `avisoBandejaMostrado`). Sessão e `localStorage` do painel ficam na mesma pasta (o «Lembrar-me» do login funciona como no navegador).

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

No modo dev, «Iniciar com o Windows» fica desativado (registraria o `electron.exe` genérico) e a pergunta da 1ª execução não aparece. F12 abre o DevTools só no dev; F5 / Ctrl+R recarrega nos dois.

## Gerar instalador

```bash
cd desktop
npm run dist
```

Saída: `desktop/release/DeskRudder-Setup-{versão}.exe` (NSIS, por usuário, sem admin). Versão em `desktop/package.json`.

O instalador **não é assinado**: o Windows SmartScreen mostra «O Windows protegeu o computador» → **Mais informações** → **Executar assim mesmo**. Assinatura de código e auto-update ficam fora da v1.

## Checklist de validação

| # | Cenário | Esperado |
|---|---------|----------|
| 1 | 1ª execução | Tela de conta; conta inexistente mostra erro sem sair da tela |
| 2 | Conta válida | Abre o login do painel da instância |
| 3 | Após o painel carregar | Pergunta «Abrir o DeskRudder ao iniciar o computador?» |
| 4 | Fechar a janela (X) | Some para a bandeja; aviso na 1ª vez |
| 5 | Clique no ícone da bandeja | Reabre a janela |
| 6 | Chat na fila com a janela escondida | Som da fila + notificação do Windows; tooltip mostra o contador |
| 7 | Menu da bandeja → Iniciar com o Windows | Marca/desmarca; reiniciar o PC abre escondido na bandeja |
| 8 | Abrir o atalho com o app já aberto | Reabre a mesma janela (sem 2ª instância) |
| 9 | Link externo no chat | Abre no navegador padrão |
| 10 | Menu da bandeja → Trocar empresa | Volta para a tela de conta |
| 11 | Menu da bandeja → Sair | Encerra o app e para os alertas |
| 12 | Botão direito numa imagem do chat → Copiar | Imagem colável no Paint/WhatsApp; em texto selecionado copia o texto |
