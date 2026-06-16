# [Épico] Dashboards e relatórios operacionais

## Contexto

O dashboard atual (`GET /v1/dashboard`) expõe apenas totais básicos. A operação precisa de **visões separadas** por canal e **relatórios exportáveis** para gestão de redes de postos.

## Objetivo

| Área | Público | Métricas principais |
|------|---------|---------------------|
| **Dashboard geral** | Admin + atendentes | Resumo cross-canal, alertas operacionais |
| **Dashboard tickets** | Admin + atendentes (setor) | Volume, fila, MTTR, CSAT, por motivo/rede |
| **Dashboard chats** | Admin + atendentes | Fila WhatsApp, TMA, avaliações, encerramentos |
| **Relatórios** | Admin | Export CSV, filtros por período/rede/setor |

## Fases

| Fase | Issues |
|------|--------|
| D-F1 | D-01, D-05 — Geral |
| D-F2 | D-02, D-06 — Tickets |
| D-F3 | D-03, D-07 — Chats |
| D-F4 | D-04, D-08 — Relatórios |

## Fora de escopo v1

- BI externo (Power BI)
- Relatórios agendados por e-mail (issue futura)

## Labels

`epic`, `dashboard`, `fase-interna`
