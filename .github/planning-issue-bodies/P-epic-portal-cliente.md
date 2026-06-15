# [Épico] Portal do cliente — visão e fases

## Contexto

Desde o início do DX Connect, a visão inclui um **portal externo** para funcionários da rede (sócio, supervisor, colaborador) abrirem e acompanharem tickets. O modelo de dados já prevê `aberto_por_id` em tickets.

**Decisão atual:** priorizar o **produto interno** (atendentes) até consolidação; o portal é **fase posterior**, mas as issues ficam abertas para planejamento incremental.

## Objetivo do épico

Entregar um portal web autenticado onde o funcionário:

- Veja apenas tickets da sua **rede/empresa** (escopo RBAC distinto do painel interno)
- Abra tickets com empresa e PDV pré-preenchidos quando aplicável
- Acompanhe mensagens **públicas** e responda quando permitido
- Avalie atendimento (CSAT) via fluxo existente

## Fases de entrega

| Fase | Issues | Entrega |
|------|--------|---------|
| **P-F1** | P-01, P-05 | Auth + shell do portal |
| **P-F2** | P-02, P-06, P-07 | Listagem e abertura |
| **P-F3** | P-03, P-08 | Detalhe, mensagens, anexos |
| **P-F4** | P-04 | Notificações por e-mail |
| **P-F5** | P-09 (+ KB-03) | Base de conhecimento no portal |

## Fora de escopo (v1 portal)

- Chat WhatsApp no portal (permanece canal separado)
- Gestão de cadastros (redes/empresas) pelo cliente
- App mobile (equipe separada)

## Issues filhas

- Backend: P-01 → P-04
- Frontend: P-05 → P-09

## Relacionado

- Modelo: `backend/app/models/ticket.py` (`aberto_por_id`)
- CSAT público: `public_csat.py` (reutilizar padrão)
- Épico KB: KB-03, KB-07, P-09

## Labels

`epic`, `fase-portal`, `portal-cliente`
