# Portal do cliente — base de conhecimento (frontend)

## Contexto

Épico: **Portal do cliente** + **Base de conhecimento**. Artigos publicados visíveis ao funcionário antes/durante abertura de ticket.

Parte de: **P-F5**

## Proposta

- Rota `/portal/ajuda` com categorias e busca
- Artigo individual `/portal/ajuda/:slug`
- Widget «Artigos sugeridos» na abertura de ticket (KB-04)
- Feedback «Este artigo ajudou?» (opcional v1)

## Critérios de aceite

- [ ] Consome API pública KB-03
- [ ] Apenas artigos `publicado=true`
- [ ] Mobile-friendly

## Dependências

- Requer: P-05, KB-03
- Relacionado: KB-07 (leitura interna)

## Labels

`frontend`, `fase-portal`, `portal-cliente`, `base-conhecimento`
