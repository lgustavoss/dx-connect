## Contexto

Administradores precisam saber **quem está online no painel** e **desde quando**, para coordenar quem pode atender chats (WhatsApp/portal) e tickets.

Hoje o painel já abre SSE (`GET /v1/events/stream`) por atendente autenticado (`RealtimeHub`), mas **não há** tracking de presença nem tela para o admin consultar.

Meta-issue: #16

## Objetivo

Expor presença em tempo quase real: lista de atendentes **online** (painel aberto com SSE ativo) com horário de início da sessão atual, consultável só por **admin**.

## Definição de «online» (v1)

| Critério | Decisão |
|----------|---------|
| Sinal | Conexão SSE ativa no hub (`atendente:{id}`) |
| Multi-aba | Online enquanto houver ≥1 conexão; «desde» = início da sessão contínua (primeira conexão atual) |
| Offline | Última conexão SSE fechou (aba fechada, logout, rede) |
| Reinício do backend | Presença zera (memória do processo) — aceitável na v1 |
| Multi-worker Gunicorn | Limitação conhecida do hub v1 (`docs/REALTIME_SSE.md`): presença confiável com `--workers 1` ou sticky session; Redis fora de escopo |

**Não** confundir com `ativo` no cadastro (conta habilitada). Online = sessão ao vivo no painel.

## Issues filhas

| Fase | Issue | Entrega |
|------|-------|---------|
| **PR-F1** | [#546](https://github.com/lgustavoss/dx-connect/issues/546) | Backend: tracking no hub + API admin |
| **PR-F2** | [#547](https://github.com/lgustavoss/dx-connect/issues/547) | Frontend: tela admin + refresh |

## Fora de escopo (v1)

- Histórico / relatório de horas online
- Status manual «ausente» / «em pausa»
- Indicador de presença no chat interno entre pares
- Redis Pub/Sub para multi-worker
- Contagem de carga (qtd. chats/tickets abertos) — follow-up possível

## Critérios do épico

- [ ] Admin vê quem está online e desde quando
- [ ] Atendente não acessa a API/tela de presença
- [ ] Documentar limite multi-worker se necessário
