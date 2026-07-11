# Chat interno — notificações in-app e SSE (backend)

## Contexto

Épico: **Chat interno entre atendentes e comunicados por setor**.

Parte de: **IC-F2**

Depende de: **IC-02**, infra SSE (#264–#269)

## Proposta

### Contadores (`/v1/notificacoes`)

- Incluir mensagens internas **não lidas** no resumo (`nao_lidas_count` ou campo dedicado `chat_interno_nao_lidas_count`).
- Item na listagem `/notificacoes/itens` com link para a conversa (tipo `chat_interno`).

### SSE

- Novo evento: `chat.interno.mensagem` (ou `interno.mensagem`) no envelope existente.
- Payload mínimo: `conversa_id`, `tipo` (`direta`|`setor`), `setor_id?`, `remetente_id`, preview do corpo.
- Emitir para:
  - **Direta:** o outro participante.
  - **Canal setor:** todos os atendentes vinculados ao setor (exceto remetente, ou incluir para sync — definir na implementação).

### Leitura

- Recalcular contadores após `POST .../visto` e emitir `notificacao.contagem` (padrão #269).

## Critérios de aceite

- [ ] Testes de integração com hub SSE (`test_events_stream` / `test_realtime_emit`)
- [ ] Contador no navbar reflete mensagens internas não lidas
- [ ] Publicação em canal setor notifica todos os membros elegíveis

## Dependências

- Depende de: IC-02, RT-F1 (#264)

## Labels

`backend`, `chat-interno`, `tempo-real`, `fase-interna`
