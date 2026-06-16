# Distribuição tickets — indicadores tempo na fila (frontend)

## Contexto

Épico: **Distribuição automática de tickets**.

Parte de: **T-F2**

## Proposta

Na listagem tickets (filtro sem responsável):

- Coluna «Na fila há» (tempo relativo)
- Badge «Auto em X min» se setor `auto_apos_timeout`
- Destaque visual tickets próximos do timeout

## Critérios de aceite

- [ ] Cálculo client-side from `created_at` + config setor (endpoint ticket inclui `distribuicao_preview` opcional)
- [ ] Ordenação por tempo na fila

## Dependências

- Requer: T-01
- Ideal com: T-02

## Labels

`frontend`, `tickets`, `fase-interna`, `distribuicao`
