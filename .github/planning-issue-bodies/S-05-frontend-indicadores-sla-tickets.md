# SLA — badges e filtros em tickets (frontend)

## Contexto

Épico: **SLA**.

Parte de: **S-F2**

## Proposta

- Badge na listagem: verde/amarelo/vermelho (dentro/risco/violado)
- Filtro «SLA violado» / «Em risco»
- Detalhe ticket: card com countdown ou «Violado há X»
- Tooltip explicando meta aplicada

## Critérios de aceite

- [ ] Consome campos S-02 ou endpoint `/sla`
- [ ] Performance listagem (não N+1)

## Dependências

- Requer: S-02

## Labels

`frontend`, `sla`, `fase-interna`, `tickets`
