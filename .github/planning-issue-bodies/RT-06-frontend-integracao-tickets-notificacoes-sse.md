# Tempo real — tickets e NavbarNotificacoes (frontend)

## Contexto

Épico: **Tempo real (SSE)**.

Parte de: **RT-F3**

## Proposta

- `TicketDetalhe`: subscrever `ticket.mensagem`
- `NavbarNotificacoes`: subscrever `notificacao.contagem`
- Opcional: badge fila tickets lista on `ticket.fila`

## Critérios de aceite

- [ ] Contadores atualizam sem refresh página
- [ ] Detalhe ticket mostra msg sem F5

## Dependências

- Requer: RT-04, RT-02, RT-03

## Labels

`frontend`, `tempo-real`, `fase-interna`, `tickets`, `notificacoes`
