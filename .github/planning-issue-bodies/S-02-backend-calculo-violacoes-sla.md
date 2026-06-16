# SLA — cálculo de prazos, pausas e violações (backend)

## Contexto

Épico: **SLA**. Motor de cálculo.

Parte de: **S-F2**

## Proposta

1. **Job periódico** (60s) ou trigger em eventos:
   - Nova mensagem pública equipa → marca primeira resposta
   - Mudança status → verifica resolução
2. **Horário comercial:** incrementar relógio SLA só dentro do calendário do setor
3. **Estados:** `dentro`, `em_risco` (ex.: 80% tempo), `violado`
4. Endpoint `GET /v1/tickets/{id}/sla` para detalhe

## Critérios de aceite

- [ ] Ticket criado sexta 18h → relógio pausa até segunda
- [ ] Prioridade alta usa policy correta
- [ ] Testes unitários calendário + edge cases
- [ ] Não recalcular retroativo policies alteradas (snapshot na criação)

## Dependências

- Requer: S-01
- Bloqueia: S-03, S-05, D-01 (campo violações)

## Labels

`backend`, `sla`, `fase-interna`
