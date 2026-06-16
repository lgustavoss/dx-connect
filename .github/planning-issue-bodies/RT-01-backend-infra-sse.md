# Tempo real — infraestrutura SSE e autenticação (backend)

## Contexto

Épico: **Tempo real (SSE)**.

Parte de: **RT-F1**

## Proposta

- `GET /v1/events/stream` — `text/event-stream`
- Auth: JWT query param **ou** cookie HttpOnly (preferir header se EventSource permitir proxy)
- Heartbeat 30s
- Canal por atendente: `atendente:{id}`
- Pub/sub in-process (asyncio Queue) v1; Redis opcional v2 multi-worker

Event envelope:

```json
{ "type": "ping|ticket.mensagem|chat.mensagem|notificacao", "payload": {} }
```

## Critérios de aceite

- [ ] Conexão autenticada; 401 sem token
- [ ] Desconexão limpa
- [ ] Teste integração com cliente SSE
- [ ] Documentar limite conexões Gunicorn

## Dependências

- Bloqueia: RT-02, RT-03, RT-04

## Labels

`backend`, `tempo-real`, `fase-interna`
