# Tempo real — hook cliente SSE com fallback (frontend)

## Contexto

Épico: **Tempo real (SSE)**.

Parte de: **RT-F1**

## Proposta

- `useEventStream()` hook:
  - Conecta SSE autenticado
  - Reconnect exponential backoff
  - Fallback polling se 3 falhas
  - Dispatch por `type` para listeners registrados
- Provider global no `Layout`

## Critérios de aceite

- [ ] Reconexão transparente
- [ ] Cleanup on unmount/logout
- [ ] Log dev-only erros conexão

## Dependências

- Requer: RT-01
- Bloqueia: RT-05, RT-06

## Labels

`frontend`, `tempo-real`, `fase-interna`
