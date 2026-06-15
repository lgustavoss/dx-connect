# SLA — alertas in-app e e-mail (backend)

## Contexto

Épico: **SLA**. Notificar antes e após violação.

Parte de: **S-F3**

## Proposta

Eventos:

- `sla_em_risco` — ex.: 80% do prazo
- `sla_violado` — prazo estourado

Destinatários:

- Atendente responsável (se houver)
- Admins do setor ou lista configurável

Integrar com notificações existentes (#109) + novo tipo preferência.

## Critérios de aceite

- [ ] Não duplicar alerta (debounce por ticket/meta)
- [ ] Preferência opt-in/out por tipo
- [ ] Testes mock fila e-mail

## Dependências

- Requer: S-02

## Labels

`backend`, `sla`, `fase-interna`, `notificacoes`
