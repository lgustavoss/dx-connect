# KB — API pública de leitura (backend)

## Contexto

Épico: **Base de conhecimento**. Consumo externo (portal) e interno.

Parte de: **KB-F4**

## Proposta

- `GET /v1/kb/public/categories`
- `GET /v1/kb/public/articles?categoria=&q=`
- `GET /v1/kb/public/articles/{slug}`

Sem auth ou auth portal opcional (artigos podem ser `interno_only=false`).

Rate limit básico.

## Critérios de aceite

- [ ] Só artigos publicados
- [ ] Busca por termo
- [ ] Cache-Control curto

## Dependências

- Requer: KB-01
- Bloqueia: P-09, KB-07

## Labels

`backend`, `base-conhecimento`, `fase-interna`, `fase-portal`
