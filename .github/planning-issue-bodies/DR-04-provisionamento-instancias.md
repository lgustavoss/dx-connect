# DR-04 — Provisionamento de instâncias a partir do painel

## Contexto

Parte do épico SaaS. Infra manual já existe (#170): `provision-client.sh`, `stack-client.sh`, `deploy/clients/`.

## Objetivo

A partir do painel DR-03, disparar (job/API) o provisionamento de uma nova instância para um `ClienteSaaS` (slug → subdomínio + Postgres + stack), com audit trail.

## Escopo

### Dentro

- Integração com scripts/runbook existentes (ou worker que os invoca com segurança)
- Status do job: pendente / em progresso / sucesso / falha
- Atualizar host/URL no registro SaaS ao concluir
- Documentar pré-requisitos de servidor (SSH, permissões) em `docs/` ou runbook

### Fora

- Redesign completo da infra (#170 continua dono do isolamento)
- Billing
- Path-based multi-tenant na mesma BD

## RBAC

- Só admin control-plane; ação auditable

## Critérios de aceite

- [ ] Ação «Provisionar» cria/atualiza stack para o slug
- [ ] Falhas ficam registradas e visíveis na UI
- [ ] Instância sobe com health ok (checklist alinhado a #170)
- [ ] Não altera o modelo single-tenant (1 Postgres por cliente)

## Dependências

- Requer: DR-01, DR-02, DR-03 (mínimo)
- Relacionado: #170

## Labels

`enhancement`, `backend`, `frontend`
