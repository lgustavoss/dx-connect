# Portal do cliente — listagem de tickets (frontend)

## Contexto

Épico: **Portal do cliente**. Tela principal pós-login.

Parte de: **P-F2**

## Proposta

- Tabela/cards: protocolo, assunto, status, última atualização
- Filtros: abertos/fechados, busca por protocolo
- Empty state orientando abrir primeiro ticket
- Paginação ou infinite scroll

## Critérios de aceite

- [ ] Consome `GET /v1/portal/tickets`
- [ ] Estados loading/erro/vazio
- [ ] Clique navega para detalhe

## Dependências

- Requer: P-05, P-02

## Labels

`frontend`, `fase-portal`, `portal-cliente`, `tickets`
