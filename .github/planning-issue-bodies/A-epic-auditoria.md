# [Épico] Auditoria estruturada e rastreável

## Contexto

Auditoria atual (`registrar_audit`) grava apenas `entity_type`, `entity_id`, `action`, `atendente_id` — sem payload, IP, ou cobertura de tickets/chats/mensagens sensíveis.

## Objetivo

- Trail completo para compliance e suporte interno
- UI consultável com filtros
- Export para análise
- Registro de ações sensíveis (credenciais PDV, export relatórios)

## Fases

| Fase | Issues |
|------|--------|
| A-F1 | A-01 — Trail expandido |
| A-F2 | A-02 — Consulta/export |
| A-F3 | A-03 — UI |

## Labels

`epic`, `auditoria`, `fase-interna`
