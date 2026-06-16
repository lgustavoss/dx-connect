# KB — categorias, artigos, versões e publicação (backend)

## Contexto

Épico: **Base de conhecimento**.

Parte de: **KB-F1**

## Proposta

### Tabelas

- `kb_categories`: nome, slug, ordem, parent_id nullable
- `kb_articles`: titulo, slug, category_id, status (`rascunho`|`publicado`|`arquivado`), conteudo_html ou markdown, autor_atendente_id, published_at
- `kb_article_versions` (opcional v1): snapshot em cada save

Slugs únicos globalmente.

## Critérios de aceite

- [ ] Migração Alembic
- [ ] Índice full-text titulo+conteudo (Postgres `tsvector` ou ILIKE v1)
- [ ] Soft delete / arquivar

## Dependências

- Bloqueia: KB-02, KB-03, KB-06

## Labels

`backend`, `base-conhecimento`, `fase-interna`
