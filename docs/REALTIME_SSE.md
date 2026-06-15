# Tempo real (SSE) — RT-F1

Infraestrutura de eventos servidor→cliente para substituir polling no painel interno.

## Endpoint

- `GET /v1/events/stream` — `text/event-stream`
- Autenticação: header `Authorization: Bearer <access_token>` (preferido) ou query `?token=<access_token>`
- Heartbeat: evento `ping` a cada **30 s** sem outro evento
- Envelope: `{ "type": "<tipo>", "payload": { ... } }`
- Canal por atendente: `atendente:{id}`

Evento inicial ao conectar:

```json
{ "type": "connected", "payload": { "atendente_id": 1, "canal": "atendente:1" } }
```

## Eventos (RT-F2+)

| Tipo | Quando | Payload principal |
|------|--------|-------------------|
| `chat.mensagem` | Nova mensagem WhatsApp | `{ chat_id, mensagem }` |
| `chat.fila` | Chat entra/sai da fila ou muda estado | `{ chat_id, estado, chat? }` |
| `ticket.mensagem` | Nova mensagem em ticket | `{ ticket_id, mensagem }` |
| `ticket.fila` | Ticket aberto sem responsável | `{ ticket_id, setor_id, protocolo }` |
| `notificacao.contagem` | RT-F3 — contadores navbar | `NotificacaoResumo` (compatível com `/notificacoes/resumo`) |

Destinatários filtrados por RBAC (setor homônimo + admin).

## Frontend

- Cliente fetch-based (suporta Bearer; `EventSource` nativo não envia header)
- Hook `useEventStream()` + `EventStreamProvider` no `Layout`
- Reconexão com backoff exponencial; após **3 falhas** consecutivas, `useFallback === true` (consumidores RT-F2 mantêm polling)

## Gunicorn e multi-worker

O hub v1 é **in-process** (`asyncio.Queue` por conexão). Implicações:

| Config | Comportamento |
|--------|----------------|
| `--workers 1` | Pub/sub e SSE no mesmo processo — adequado para v1 interno |
| `--workers N>1` | Cada worker tem filas isoladas; um evento publicado no worker A **não** chega a SSE conectada no worker B |

**Recomendação v1 (uso interno):** `--workers 1` ou sticky sessions no Nginx (`ip_hash` / `hash $cookie_...`) se precisar de N>1 por CPU.

**v2 (futuro):** Redis Pub/Sub ou similar para fan-out entre workers.

### Limites práticos

- Cada atendente autenticado = **1 conexão HTTP longa** por aba do painel
- Gunicorn `worker_connections` (gevent/eventlet) ou limite de file descriptors do SO aplicam-se
- Nginx: desativar buffering (`X-Accel-Buffering: no` já enviado pela API); `proxy_read_timeout` ≥ 3600 s para SSE

## Issues

- Épico: [#256](https://github.com/lgustavoss/dx-connect/issues/256)
- RT-F1 backend: [#264](https://github.com/lgustavoss/dx-connect/issues/264)
- RT-F1 frontend: [#267](https://github.com/lgustavoss/dx-connect/issues/267)
