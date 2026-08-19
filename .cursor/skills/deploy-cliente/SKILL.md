---
name: deploy-cliente
description: Runbook de deploy multi-cliente do DX Connect — provisionar stack, migrate, health, Nginx e atualização. Use ao deployar cliente novo, atualizar instância em produção, ou quando o usuário mencionar deploy, VPS, stack-client, provision-client ou subdomínio de cliente.
---

# Deploy por cliente — DX Connect

Referências: `docs/DEPLOYMENT_ARCHITECTURE.md`, `deploy/clients/README.md`

## Modelo

- **Um cliente = um subdomínio + Postgres dedicado + container API**
- Produção **single-tenant** (`DX_CONNECT_MULTI_TENANT=false`)
- `tenant_id` legado — não usar como eixo de isolamento entre clientes

## Provisionar cliente novo

Na raiz do repo (Linux/macOS/Git Bash):

```bash
bash deploy/scripts/provision-client.sh \
  --slug NOME_CLIENTE \
  --base-domain connect.seudominio.com.br \
  --api-port 8001
```

Gera `deploy/clients/NOME_CLIENTE/` (não commitar secrets).

### Checklist pós-provision

1. Editar `client.env`: CORS (origem HTTPS da PWA), ALLOWED_HOSTS, RESEND, SEED_ADMIN, **VAPID** (`WEB_PUSH_VAPID_*`)
2. `bash deploy/scripts/stack-client.sh NOME_CLIENTE migrate`
3. `bash deploy/scripts/stack-client.sh NOME_CLIENTE up`
4. `bash deploy/scripts/stack-client.sh NOME_CLIENTE seed`
5. `bash deploy/scripts/stack-client.sh NOME_CLIENTE health`
6. Build frontend com `VITE_API_URL` / `VITE_CLIENT_APP_HOST` corretos
7. Nginx + DNS + TLS (Certbot)

## Comandos stack-client.sh

| Comando | Ação |
|---------|------|
| `migrate` | `alembic upgrade head` na BD do cliente |
| `up` | build + docker compose up -d |
| `down` | para stack |
| `logs` | logs backend |
| `seed` | admin inicial |
| `health` | curl /health local |

## Atualizar código (cliente existente)

No VPS:

```bash
git pull
export DX_CONNECT_GIT_SHA=$(git rev-parse --short HEAD)
bash deploy/scripts/stack-client.sh SLUG migrate
bash deploy/scripts/stack-client.sh SLUG up
```

**Sempre** rodar `migrate` antes de `up` quando houver migrations novas.

## Portas

Registrar internamente: slug → porta loopback (8001, 8002, …). Nginx proxy para `127.0.0.1:PORTA`.

## Backup

```bash
docker exec dx-connect-db-SLUG pg_dump -U dxconnect dxconnect_SLUG > backup-SLUG-$(date +%F).sql
```

(Ajustar user/db conforme `client.env`.)

## Pré-deploy

Consultar `docs/PRE_DEPLOY_CHECKLIST.md` antes de releases.

## Erros comuns

| Problema | Causa provável |
|----------|----------------|
| `alembic upgrade` falha | Múltiplos heads ou chain quebrada — ver skill/rule Alembic |
| SSE não atualiza | Gunicorn com N>1 workers sem sticky session |
| CORS error | `CORS_ORIGINS` desalinhado com domínio HTTPS |
| 502 Nginx | Container down ou porta errada no site config |
