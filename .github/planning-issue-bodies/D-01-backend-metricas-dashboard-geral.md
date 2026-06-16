# Dashboard geral — endpoints de métricas consolidadas (backend)

## Contexto

Épico: **Dashboards e relatórios**. Evoluir além de `dashboard.py` atual.

Parte de: **D-F1**

## Proposta

Novo ou estendido `GET /v1/dashboard/geral`:

- Tickets abertos / sem responsável (escopo setor)
- Chats `aguardando_atendente` / `em_atendimento`
- CSAT médio tickets (7 dias) se existir avaliação
- CSAT médio chats (7 dias)
- Violações SLA abertas (quando épico S existir — campo nullable até lá)
- Última atualização / cache curto (60s)

Respeitar RBAC setor (#38).

## Critérios de aceite

- [ ] Admin vê global; atendente vê setores vinculados
- [ ] Resposta tipada Pydantic `DashboardGeralResponse`
- [ ] Testes com fixtures multi-setor
- [ ] Performance: queries agregadas, sem N+1

## Dependências

- Paralelo: D-05
- Opcional futuro: S-02 (SLA)

## Labels

`backend`, `dashboard`, `fase-interna`
