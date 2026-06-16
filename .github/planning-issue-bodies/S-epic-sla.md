# [Épico] SLA configurável por setor e prioridade

## Contexto

Tickets têm **prioridade** (#107/#108) mas não há metas de tempo nem alertas. Chats WhatsApp têm urgência operacional via alerta sonoro — SLA formal aplica-se principalmente a **tickets** (e-mail e assíncronos).

## Objetivo

- Definir metas por setor + prioridade (e opcionalmente por natureza)
- Calcular prazos em **horário comercial** (reutilizar lógica WhatsApp business hours)
- Alertar atendente/supervisor ao aproximar ou violar SLA
- Exibir status visual na UI

## Métricas sugeridas (v1)

| Meta | Início | Fim |
|------|--------|-----|
| **Primeira resposta** | Criação ticket | Primeira mensagem pública da equipa |
| **Resolução** | Criação ticket | Status terminal (fechado/resolvido) |

## Fases

| Fase | Issues |
|------|--------|
| S-F1 | S-01, S-04 — Config |
| S-F2 | S-02, S-05 — Cálculo e UI |
| S-F3 | S-03 — Notificações |

## Fora de escopo v1

- SLA em chats WhatsApp (permanece alerta contínuo na fila)
- Pausa automática SLA quando «aguardando cliente» (issue futura)

## Labels

`epic`, `sla`, `fase-interna`
