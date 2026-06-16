# Roteamento — UI admin de regras (frontend)

## Contexto

Épico: **Roteamento automático**.

Parte de: **R-F1**

## Proposta

**Configurações → Atendimento → Roteamento**:

- Lista regras drag-and-drop ordem
- Form builder condição: campo + operador + valor
- Form ação: selects setor, prioridade, natureza/motivo
- Toggle ativo/inativo
- Teste seco: «Simular com e-mail X / assunto Y» (chama endpoint debug)

## Critérios de aceite

- [ ] CRUD completo
- [ ] Validação client-side
- [ ] Admin-only

## Dependências

- Requer: R-01
- Simulador opcional depende R-02

## Labels

`frontend`, `roteamento`, `fase-interna`
