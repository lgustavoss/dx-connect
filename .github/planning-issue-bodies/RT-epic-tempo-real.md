# [Épico] Eventos em tempo real (SSE)

## Contexto

Chat WhatsApp e notificações usam **polling**, causando atraso e carga. **Server-Sent Events (SSE)** é suficiente para push unidirecional servidor→cliente (FastAPI friendly).

**Importante:** tempo real **não** unifica filas tickets/chats — apenas atualiza cada tela mais rápido.

## Objetivo

- Nova mensagem chat aparece sem refresh manual
- Contadores `NavbarNotificacoes` atualizam ao vivo
- Detalhe ticket: nova mensagem/anexo em tempo real
- Fallback automático para polling se SSE cair

## Fases

| Fase | Issues |
|------|--------|
| RT-F1 | RT-01, RT-04 — Infra |
| RT-F2 | RT-02, RT-05 — Chats |
| RT-F3 | RT-03, RT-06 — Tickets + notificações |

## Fora de escopo v1

- WebSocket bidirecional
- Typing indicators WhatsApp

## Labels

`epic`, `tempo-real`, `fase-interna`
