# Operação e observabilidade (#119)

Guia para quem opera o DX Connect em staging/produção: healthchecks, filas de e-mail e o que monitorizar.

## Healthchecks

| Endpoint | Uso | Falha HTTP |
|----------|-----|------------|
| `GET /health` | **Liveness** — processo de pé | Só se o app não responder |
| `GET /health/ready` | **Readiness** — pronto para tráfego (inclui PostgreSQL) | **503** se o banco estiver inacessível |

### Campos úteis

```json
{
  "status": "ok",
  "git_sha": "3aaff44",
  "environment": "production",
  "capabilities": { "settings_email": true, ... },
  "integrations": {
    "email_outbound": "configured",
    "email_inbound": "configured",
    "evolution_whatsapp": "missing",
    "ticket_closed_webhook": "missing"
  }
}
```

- **`git_sha`**: definir `DX_CONNECT_GIT_SHA` no deploy (commit em execução).
- **`integrations`**: indica **configuração** (env/BD), não testa conectividade com Resend/Evolution.
- **`/health/ready`**: inclui `"checks": { "database": { "status": "ok" } }`. Se `status` for `unavailable`, o orchestrator/load balancer não deve enviar tráfego.

### Monitorização mínima

1. Uptime em `GET /health` (intervalo 1–5 min).
2. Alerta se `GET /health/ready` retorna **503** por > 2 min.
3. Logs com `"event": "notificacao_email_send_failed_permanent"`, `"ticket_email_send_failed_permanent"` ou `"webhook_outbox_send_failed_permanent"`.

## Workers em background

| Worker | Intervalo (env) | Função |
|--------|-----------------|--------|
| `notificacao-email-outbox` | `NOTIFICACAO_EMAIL_WORKER_INTERVAL_SECONDS` (10s) | E-mails de notificação a atendentes |
| `ticket-mensagem-email-outbox` | `TICKET_MENSAGEM_EMAIL_WORKER_INTERVAL_SECONDS` (5s) | Respostas públicas ao cliente por e-mail |
| `webhook-outbox` | `WEBHOOK_OUTBOX_WORKER_INTERVAL_SECONDS` (15s) | POST HTTP ao fechar ticket (#119) |

Todos fazem **commit** após cada ciclo (mesmo com 0 envios), para persistir tentativas e retries.

## Webhook de saída — ticket fechado

Variáveis (`.env`):

- `TICKET_CLOSED_WEBHOOK_URL` — destino do POST (vazio = desligado)
- `TICKET_CLOSED_WEBHOOK_SECRET` — HMAC SHA-256 no header `X-DX-Webhook-Signature: sha256=...`

Payload mínimo:

```json
{
  "event": "ticket.closed",
  "ticket_id": 206,
  "protocolo": "#T202605-0206",
  "empresa_id": 1,
  "setor_id": 2,
  "atendente_id": 3,
  "assunto": "...",
  "fechado_em": "2026-06-12T21:00:00+00:00"
}
```

Fila: tabela `webhook_outbox` (mesma política de 5 tentativas que e-mail).

## Retry Evolution API (WhatsApp)

Envio de texto/mídia via Evolution usa retry **síncrono** em falhas transitórias (rede, HTTP 429/502/503/504):

- `EVOLUTION_HTTP_MAX_ATTEMPTS` (padrão **3**)
- Backoff curto: 2s → 4s → 8s (máx. 30s)

Logs: `evolution_http_retry`, `evolution_http_failed_permanent`.

## Política de retry (e-mail e webhooks)

- **Máximo:** 5 tentativas (`MAX_EMAIL_SEND_ATTEMPTS`).
- **Backoff:** 60s → 120s → 240s → … (máx. 15 min entre tentativas).
- **Notificações atendentes:** tabela `notificacao_email_outbox` — `status`: `pendente` | `enviada` | `falha`.
- **Mensagem ao cliente:** colunas `email_status`, `email_send_attempts`, `email_last_error` em `ticket_mensagens` — `falha_envio` após esgotar tentativas.

### Dev sem Resend

Com `ENVIRONMENT=development` e envio não configurado, notificações a atendentes são **simuladas** (`status=enviada` + log estruturado `notificacao_email_send_simulated_dev`).

## Logs estruturados

Eventos relevantes (JSON em uma linha):

| event | Significado |
|-------|-------------|
| `notificacao_email_send_ok` | Notificação enviada |
| `notificacao_email_send_retry` | Falha transitória; nova tentativa agendada |
| `notificacao_email_send_failed_permanent` | 5 falhas — investigar Resend/SMTP |
| `ticket_email_send_ok` | Resposta ao cliente enviada |
| `ticket_email_send_retry` | Retry da mensagem pública |
| `ticket_email_send_failed_permanent` | Mensagem presa em `falha_envio` |
| `webhook_outbox_send_ok` | Webhook entregue |
| `webhook_outbox_send_retry` | Retry do webhook |
| `webhook_outbox_send_failed_permanent` | Webhook esgotou tentativas |
| `evolution_http_retry` | Retry HTTP Evolution |
| `evolution_http_failed_permanent` | Evolution falhou após tentativas |

Filtrar no agregador de logs: `grep '"event":"notificacao_email_send_failed_permanent"'`.

## Consultas úteis (PostgreSQL)

```sql
-- Fila de notificações com falha permanente
SELECT id, tipo, ticket_id, atendente_id, tentativas, last_error, created_at
FROM notificacao_email_outbox
WHERE status = 'falha'
ORDER BY id DESC
LIMIT 20;

-- Mensagens ao cliente que falharam
SELECT id, ticket_id, email_send_attempts, email_last_error, updated_at
FROM ticket_mensagens
WHERE email_status = 'falha_envio'
ORDER BY id DESC
LIMIT 20;

-- Webhooks com falha permanente
SELECT id, event_type, target_url, tentativas, last_error, created_at
FROM webhook_outbox
WHERE status = 'falha'
ORDER BY id DESC
LIMIT 20;
```

## Relacionado

- Checklist de deploy: [`PRE_DEPLOY_CHECKLIST.md`](PRE_DEPLOY_CHECKLIST.md)
- Deploy CI/CD (GitHub Actions, SSH timeout): [`deploy/github-actions.md`](../deploy/github-actions.md)
- Arquitetura multi-cliente: [`DEPLOYMENT_ARCHITECTURE.md`](DEPLOYMENT_ARCHITECTURE.md)
- Runbook e-mail inbound: issue **#167** (SPF/DKIM)
