# Auditoria — filtros avançados e export (backend)

## Contexto

Épico: **Auditoria estruturada**.

Parte de: **A-F2**

## Proposta

Evoluir `GET /v1/audit`:

- Filtros: período, atendente, entity_type, action, entity_id, busca texto payload
- Paginação cursor-based
- `GET /v1/audit/export?format=csv` admin-only
- Retenção: config `AUDIT_RETENTION_DAYS` (job purge opcional v1)

## Critérios de aceite

- [ ] Performance índice `(created_at, entity_type)`
- [ ] Export auditado (meta-audit)
- [ ] Testes filtros

## Dependências

- Requer: A-01
- Bloqueia: A-03

## Labels

`backend`, `auditoria`, `fase-interna`
