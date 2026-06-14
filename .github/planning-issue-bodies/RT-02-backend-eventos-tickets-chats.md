# Tempo real — eventos tickets e chats (backend)

## Contexto

Épico: **Tempo real (SSE)**.

Parte de: **RT-F2**

## Proposta

Emitir eventos após commit DB:

| Evento | Quando | Destinatários |
|--------|--------|---------------|
| `chat.mensagem` | Nova msg inbound/outbound | Atendentes com acesso ao chat |
| `chat.fila` | Chat entra/sai fila | Setor/admins |
| `ticket.mensagem` | Nova mensagem ticket | Responsável + setor |
| `ticket.fila` | Ticket sem responsável | Setor |

Hook em services existentes (`evolution_inbound`, `tickets.py` mensagens).

## Critérios de aceite

- [ ] Evento só após commit
- [ ] RBAC: atendente não recebe chat de outro setor
- [ ] Testes emit mock

## Dependências

- Requer: RT-01
- Bloqueia: RT-05, RT-06

## Labels

`backend`, `tempo-real`, `fase-interna`, `whatsapp`, `tickets`
