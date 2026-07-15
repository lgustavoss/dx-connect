# DR-08 — Renovações e alertas

## Contexto

Parte do épico SaaS (Fase 4).

## Objetivo

Monitorar `data_renovacao` das licenças; alertar equipe DeskRudder; atualizar status (ex. vencido → suspenso) conforme regras.

## Escopo

### Dentro

- Job periódico (ou check no login admin) para licenças próximas do vencimento
- Notificação in-app e/ou e-mail interno
- UI no painel: destaque «vence em X dias» / vencidas
- Ação manual renovar (estender data) e suspender

### Fora

- Cobrança automática / boleto do *SaaS DeskRudder* (épico futuro de billing control-plane)
- Suspender automaticamente a stack Docker (pode ser follow-up de DR-04)

## Critérios de aceite

- [ ] Lista mostra renovação e alertas
- [ ] Equipe recebe aviso antes do vencimento (janela configurável)
- [ ] Renovação manual atualiza data e status

## Dependências

- Requer: DR-01, DR-02, DR-03

## Labels

`enhancement`, `backend`, `frontend`
