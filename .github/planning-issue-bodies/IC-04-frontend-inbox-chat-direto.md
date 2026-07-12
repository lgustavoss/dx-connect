# Chat interno — inbox e conversa direta (frontend)

## Contexto

Épico: **Chat interno entre atendentes e comunicados por setor**.

Parte de: **IC-F3**

Depende de: **IC-02**, **IC-03** (SSE recomendado)

## Proposta

### UX

- Entrada no menu ou ícone dedicado (além do sino de notificações operacionais).
- **Inbox:** lista conversas com preview, hora, badge não lida; filtro ou abas «Todas» / «Diretas» / «Setores».
- **Nova conversa:** buscar atendente por nome/e-mail; abrir thread 1:1.
- **Thread:** bolhas estilo chat, envio com Enter, scroll automático, indicador de envio.
- Marcar como lida ao abrir (`POST .../visto`).
- Atualização em tempo real via SSE (`chat.interno.mensagem`) quando a thread estiver aberta ou para atualizar inbox.

### Rotas sugeridas

- `/chat-interno` — inbox
- `/chat-interno/:conversaId` — thread

## Critérios de aceite

- [ ] Fluxo completo: iniciar conversa → enviar → receber → badge some ao abrir
- [ ] Responsivo (mobile): inbox utilizável
- [ ] Estados vazios e erro de rede com mensagem clara
- [ ] `tsc` e build sem regressão

## Dependências

- Depende de: IC-02; IC-03 para tempo real no inbox

## Labels

`frontend`, `ux`, `chat-interno`, `fase-interna`
