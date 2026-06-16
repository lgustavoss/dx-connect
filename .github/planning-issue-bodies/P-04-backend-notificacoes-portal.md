# Portal do cliente — notificações por e-mail ao funcionário (backend)

## Contexto

Épico: **Portal do cliente**. Funcionário deve ser avisado quando há resposta no ticket.

Parte de: **P-F4**

## Proposta

Eventos que disparam e-mail ao `FuncionarioRede.email`:

- Nova mensagem **pública** da equipa no ticket
- Mudança de status relevante (ex.: encerrado, aguardando cliente)
- Link deep link para `/portal/tickets/{id}`

Reutilizar `email_send_sistema.py` / Resend transacional.

Preferências opt-out simples (fase 1: tudo ou nada por funcionário).

## Critérios de aceite

- [ ] E-mail enviado com protocolo e link correto
- [ ] Não envia para mensagens internas
- [ ] Idempotência básica (não spammar reenvios)
- [ ] Teste unitário com mock Resend

## Dependências

- Requer: P-02 (idealmente P-03)
- Paralelo: P-08 frontend

## Labels

`backend`, `fase-portal`, `portal-cliente`, `notificacoes`
