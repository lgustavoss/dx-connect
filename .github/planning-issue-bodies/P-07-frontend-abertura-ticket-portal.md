# Portal do cliente — abertura de ticket (frontend)

## Contexto

Épico: **Portal do cliente**. Formulário de nova solicitação.

Parte de: **P-F2**

## Proposta

- Empresa pré-selecionada se colaborador (única); select se supervisor/sócio
- PDV opcional (lista PDVs da empresa, se cadastrados)
- Setor: select ou default configurável
- Classificação natureza/motivo (reutilizar componentes adaptados de `TicketClassificacaoFields`)
- Anexos na abertura (opcional v1)

## Critérios de aceite

- [ ] Validação de campos obrigatórios
- [ ] Sucesso redireciona para detalhe com toast
- [ ] Empresa fora do escopo impossível de selecionar

## Dependências

- Requer: P-05, P-02

## Labels

`frontend`, `fase-portal`, `portal-cliente`, `tickets`
