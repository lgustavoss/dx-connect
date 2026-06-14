# Tempo real — eventos notificações (backend)

## Contexto

Épico: **Tempo real (SSE)**.

Parte de: **RT-F3**

## Proposta

- `notificacao.contagem` — payload `{ tickets_fila, chats_fila, ... }`
- Emitir quando fila notificação/atualização contadores muda
- Integrar após assume chat, nova msg, ticket atribuído

## Critérios de aceite

- [ ] Navbar pode substituir polling por SSE + fallback 60s
- [ ] Payload compatível com API atual notificações

## Dependências

- Requer: RT-01
- Paralelo: RT-02

## Labels

`backend`, `tempo-real`, `fase-interna`, `notificacoes`
