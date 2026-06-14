# Relatórios — consultas paginadas e export CSV (backend)

## Contexto

Épico: **Dashboards e relatórios**. Dados tabulares para gestão.

Parte de: **D-F4**

## Proposta

`GET /v1/relatorios/tickets` e `GET /v1/relatorios/chats`:

- Mesmos filtros dos dashboards + paginação
- `Accept: text/csv` ou `?format=csv` para export
- Colunas configuráveis via query `fields=`
- Limite export: ex. 50k linhas (admin)

Admin-only ou atendente com permissão futura.

## Critérios de aceite

- [ ] CSV UTF-8 com BOM para Excel
- [ ] Rate limit export
- [ ] Audit log ao exportar (#A quando pronto)

## Dependências

- Requer: D-02, D-03 (reutilizar queries)
- Bloqueia: D-08

## Labels

`backend`, `dashboard`, `fase-interna`, `relatorios`
