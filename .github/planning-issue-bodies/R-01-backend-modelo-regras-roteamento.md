# Roteamento — modelo e CRUD de regras (backend)

## Contexto

Épico: **Roteamento automático**.

Parte de: **R-F1**

## Proposta

### Tabela `routing_rules`

- `nome`, `ativo`, `ordem` (precedência)
- `condicoes` JSON: `{ "campo": "email_from"|"email_to"|"assunto"|"canal", "operador": "contains"|"equals"|"regex", "valor": "..." }`
- `acoes` JSON: `{ "setor_id", "prioridade", "natureza_id", "motivo_id" }`
- `escopo`: global ou `rede_id`

### API admin

- `GET/POST/PUT/DELETE /v1/routing/rules`
- Reordenar: `PUT /v1/routing/rules/reorder`

## Critérios de aceite

- [ ] Validação JSON schema condições/ações
- [ ] Audit log create/update
- [ ] Testes CRUD

## Dependências

- Bloqueia: R-02, R-03

## Labels

`backend`, `roteamento`, `fase-interna`
