# Distribuição tickets — config por setor (backend)

## Contexto

Épico: **Distribuição automática de tickets**.

Parte de: **T-F1**

## Proposta

Campos em `setores` ou tabela `setor_distribuicao_config`:

- `modo`: `manual` | `auto_apos_timeout` | `auto_imediato`
- `timeout_minutos`: int (só auto_apos_timeout)
- `estrategia`: `round_robin` | `menor_carga_abertos`
- `atendentes_elegiveis`: null = todos do setor (+ homônimos #38)

API admin: `PUT /v1/setores/{id}/distribuicao`

## Critérios de aceite

- [ ] Default `manual` preserva comportamento atual
- [ ] Validação timeout >= 1 quando modo timeout
- [ ] Audit log alteração config

## Dependências

- Bloqueia: T-02, T-03

## Labels

`backend`, `tickets`, `fase-interna`, `distribuicao`
