## Contexto

Follow-up do épico SLA (#259) e dashboard (#260 / #282).

O campo `sla_violacoes_abertas` em `GET /v1/dashboard/geral` foi criado em #282 como **nullable** até o SLA existir. Com #277–#278 mergeados, o campo ainda retorna `null` (stub em `dashboard_geral.py`).

## Proposta

- Contar tickets abertos com `sla_violado=true` (escopo RBAC setor, como demais métricas)
- Exibir no dashboard geral (frontend) com link/filtro para listagem de tickets violados
- Testes agregados (sem N+1)

## Critérios de aceite

- [ ] API retorna inteiro ≥ 0 em produção com SLA configurado
- [ ] UI mostra card/alerta operacional
- [ ] Admin global; atendente vê setores vinculados

## Dependências

- Requer: #277, #278 (concluídos)
- Épico pai: #260

## Origem

Identificado ao fechar épico #259 — escopo fora de #277–#281.
