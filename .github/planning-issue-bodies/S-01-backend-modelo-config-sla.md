# SLA — modelo de metas e calendário comercial (backend)

## Contexto

Épico: **SLA**. Fundação de dados.

Parte de: **S-F1**

## Proposta

### Tabelas

- `sla_policies`: setor_id, prioridade (nullable = default setor), meta_primeira_resposta_min, meta_resolucao_min, ativo
- Reutilizar `whatsapp_business_hours` / feriados ou extrair `business_calendars` compartilhado

### Campos em `tickets`

- `sla_primeira_resposta_vence_em` (nullable, calculado)
- `sla_resolucao_vence_em`
- `sla_primeira_resposta_em` (timestamp cumprido)
- `sla_violado` (bool ou enum)

## Critérios de aceite

- [ ] CRUD admin `POST/GET/PUT /v1/sla/policies`
- [ ] Migração Alembic
- [ ] Ao criar ticket: snapshot das metas aplicáveis
- [ ] Testes criação policy

## Dependências

- Bloqueia: S-02, S-04

## Labels

`backend`, `sla`, `fase-interna`
