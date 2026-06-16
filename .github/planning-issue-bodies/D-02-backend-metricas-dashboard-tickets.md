# Dashboard tickets — endpoints de métricas (backend)

## Contexto

Épico: **Dashboards e relatórios**. Visão analítica do canal ticket.

Parte de: **D-F2**

## Proposta

`GET /v1/dashboard/tickets?de=&ate=&rede_id=&setor_id=`:

| Métrica | Descrição |
|---------|-----------|
| Volume por dia | Série temporal aberturas/fechamentos |
| Por status | Snapshot atual |
| Por prioridade | Distribuição |
| Por natureza/motivo | Top 10 |
| Por rede/empresa | Top redes |
| MTTR | Média tempo abertura → encerramento (tickets fechados no período) |
| Fila | Tempo médio aguardando primeiro responsável |
| CSAT | Média e distribuição 1–5 (tickets com avaliação) |
| Canal origem | Manual, e-mail, filho massa, etc. |

## Critérios de aceite

- [ ] Filtro de período obrigatório (default 30 dias)
- [ ] Escopo setor para atendentes
- [ ] Documentação OpenAPI
- [ ] Testes unitários das agregações

## Dependências

- Paralelo: D-06

## Labels

`backend`, `dashboard`, `fase-interna`, `tickets`
