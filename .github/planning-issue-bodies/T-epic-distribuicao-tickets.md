# [Épico] Distribuição automática de tickets na fila

## Contexto

Modelo operacional **receptivo**:

- **Chats:** alerta contínuo até atendente **assumir manualmente** — sem fila automática (decisão do time).
- **Tickets:** podem ficar «sem responsável»; após **timeout configurável**, atribuir automaticamente ou permanecer em fila conforme configuração do **setor**.

> **Nota:** Isto **não** é escala de plantão/turnos (sugestão original #9). É **atribuição automática opcional** de tickets órfãos na fila.

## Objetivo

Por setor, configurar:

| Modo | Comportamento |
|------|---------------|
| `manual` | Só assume manualmente (default atual) |
| `auto_apos_timeout` | Após X minutos sem responsável, atribui automaticamente |
| `auto_imediato` | Atribui na criação (round-robin ou menor carga) |

Estratégias: `round_robin`, `menor_carga_abertos`, `menor_carga_setor`.

## Fases

| Fase | Issues |
|------|--------|
| T-F1 | T-01, T-03 — Config |
| T-F2 | T-02, T-04 — Worker + UI fila |

## Fora de escopo

- Distribuição automática de **chats** WhatsApp
- Escalas de horário de atendentes (turnos)

## Labels

`epic`, `tickets`, `fase-interna`, `distribuicao`
