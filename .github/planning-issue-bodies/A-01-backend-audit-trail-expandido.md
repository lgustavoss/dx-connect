# Auditoria — trail expandido (backend)

## Contexto

Épico: **Auditoria estruturada**.

Parte de: **A-F1**

## Proposta

Estender `AuditLog`:

- `payload_json` (diff resumido ou snapshot)
- `ip_address`, `user_agent` (opcional)
- `request_id` correlacionável
- Novas entidades: `ticket`, `ticket_mensagem`, `whatsapp_chat`, `whatsapp_mensagem`, `settings`, `export_relatorio`
- Novas actions: `assign`, `transfer`, `close`, `reopen`, `send_email`, `view_credential`

Helper `registrar_audit_v2(...)` mantendo compat com chamadas antigas.

## Critérios de aceite

- [ ] Migração nullable para logs antigos
- [ ] Tickets: log assume, transfer, status change
- [ ] PDV reveal_credential enriquecido
- [ ] Não logar senhas/tokens em payload

## Dependências

- Bloqueia: A-02, A-03

## Labels

`backend`, `auditoria`, `fase-interna`
