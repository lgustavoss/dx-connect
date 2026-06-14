# [Épico] Motor de roteamento automático

## Contexto

Hoje e-mail inbound usa setor/empresa default via env ou tabela encaminhamento. Tickets manuais exigem escolha manual. **Regras configuráveis** reduzem triagem errada.

## Objetivo

Motor que, dado um contexto (e-mail, ticket manual), define:

- `setor_id`
- `prioridade` (opcional)
- `atendente_id` (opcional, raro v1)
- `natureza_id` / `motivo_id` (sugestão)

## Fases

| Fase | Issues |
|------|--------|
| R-F1 | R-01, R-03 — Modelo + UI |
| R-F2 | R-02 — Aplicação inbound + manual |

## Exemplos de regras

| Condição | Ação |
|----------|------|
| Remetente domínio `@financeiro.` | Setor Financeiro |
| Assunto contém «NF» | Motivo Entrada NF + prioridade normal |
| Destino `financeiro.t1@notify...` | Setor Financeiro |
| Rede X + motivo PDV | Prioridade alta |

## Labels

`epic`, `roteamento`, `fase-interna`
