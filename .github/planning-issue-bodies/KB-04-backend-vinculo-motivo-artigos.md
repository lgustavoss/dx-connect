# KB — sugestão de artigos por natureza/motivo (backend)

## Contexto

Épico: **Base de conhecimento**.

Parte de: **KB-F4**

## Proposta

- Tabela `kb_article_motivo_links`: article_id, motivo_id (nullable natureza_id)
- `GET /v1/kb/suggestions?motivo_id=&natureza_id=` — artigos publicados linked
- Usado na abertura ticket (interno + portal)

## Critérios de aceite

- [ ] Admin vincula artigo a motivo no CRUD
- [ ] Máx 5 sugestões ordenadas

## Dependências

- Requer: KB-01, KB-03

## Labels

`backend`, `base-conhecimento`, `fase-interna`
