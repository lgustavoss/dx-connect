# Deploy por cliente — um stack Docker na VPS

Cada cliente pagante tem:

- **Subdomínio** próprio (`{slug}.deskrudder.com.br` + `api-{slug}.deskrudder.com.br`)
- **PostgreSQL** dedicado (container no stack do cliente)
- **Um container** da API (`dx-connect-api-{slug}`)
- **Porta loopback** distinta (`127.0.0.1:8002`, `8003`, …) para o Nginx fazer proxy

O **painel admin** DeskRudder (`/saas`) **não** fica em `clients/`. Pasta: [`../admin-center/`](../admin-center/README.md) (`provision-control-plane.sh`). Hosts: `deskrudder.com.br` e `api.deskrudder.com.br`. Porta **8001** reservada. Não rode `provision-client.sh --slug deskrudder` nem `--slug admin-center`.

A **DuplexSoft** em produção ainda usa o compose legado na raiz (`docker-compose.prod.yml`, porta **8000**). Clientes **novos** usam este diretório (`provision-client.sh`, portas **8002+**). Deploy GHA atualiza as duas stacks — ver [`../github-actions.md`](../github-actions.md).

Direção de produto: [`docs/DEPLOYMENT_ARCHITECTURE.md`](../../docs/DEPLOYMENT_ARCHITECTURE.md) · Issue **#191** (Fase 1 + Fase 2 single-tenant no código).

## Estrutura

```text
deploy/clients/
  README.md                 # este arquivo
  _template/                # modelos (versionados no Git)
  .gitignore                # ignora pastas de clientes geradas
  duplexsoft/               # exemplo — gerado no VPS, NÃO commitar
    docker-compose.yml
    client.env              # secrets
    nginx.site.conf
    frontend.env.production.example
```

## Provisionar um cliente novo

Na **raiz do repositório** (Linux/macOS/Git Bash no Windows):

```bash
bash deploy/scripts/provision-client.sh \
  --slug exemplo \
  --base-domain deskrudder.com.br \
  --api-port 8002
```

Isto cria `deploy/clients/exemplo/` com `client.env` (senhas geradas), `docker-compose.yml` e arquivos Nginx/frontend de exemplo. **Não** use porta `8001` (admin-center).

### 1. Rever `client.env`

Edite `deploy/clients/exemplo/client.env`:

- `CORS_ORIGINS` / `ALLOWED_HOSTS` alinhados aos domínios reais (`CORS_ORIGINS` = origem HTTPS da PWA **e** `https://localhost` para o APK Capacitor)
- Par **VAPID** (`WEB_PUSH_VAPID_*`) desta stack — gerar uma vez; vazio = push desligado (`docs/OPERATIONS.md`)
- `DX_CONNECT_MULTI_TENANT=false` (padrão) e `CLIENT_APP_HOST={slug}.deskrudder.com.br`
- `SAAS_CONTROL_PLANE=false` + `SAAS_INSTANCE_SLUG` + ingest (URL/token da comercial) — ver [`docs/SAAS_CONTROL_PLANE.md`](../../docs/SAAS_CONTROL_PLANE.md)
- `RESEND_API_KEY`, e-mail transacional, webhooks
- `SEED_ADMIN_EMAIL` / `SEED_ADMIN_PASSWORD` para o primeiro admin

### 2. Subir stack + migrações + seed

```bash
bash deploy/scripts/stack-client.sh migrate exemplo
bash deploy/scripts/stack-client.sh up exemplo
bash deploy/scripts/stack-client.sh seed exemplo
```

Confirme:

```bash
bash deploy/scripts/stack-client.sh health exemplo
```

### 3. Frontend

```bash
# Ajuste VITE_API_URL e VITE_CLIENT_APP_HOST em deploy/clients/exemplo/frontend.env.production.example
# ou copie para frontend/.env.production antes do build
cd frontend && npm ci && npm run build
sudo mkdir -p /var/www/dx-connect/clients/exemplo/dist
sudo rsync -a dist/ /var/www/dx-connect/clients/exemplo/dist/
```

### 4. Nginx + DNS

1. Copie `deploy/clients/exemplo/nginx.site.conf` para `/etc/nginx/sites-available/`.
2. Ajuste `FRONTEND_DIST` se necessário.
3. Aponte DNS `{slug}.deskrudder.com.br` e `api-{slug}.deskrudder.com.br` para a VPS.
4. `sudo nginx -t && sudo systemctl reload nginx`
5. TLS (Certbot) e atualize `CORS_ORIGINS` / `VITE_API_URL` para `https://`.

## Comandos `stack-client.sh`

| Comando | Descrição |
|---------|-----------|
| `migrate` | `alembic upgrade head` |
| `up` | build + `docker compose up -d` |
| `down` | para o stack |
| `logs` | logs do backend |
| `seed` | `python -m app.seed` (admin inicial) |
| `health` | `curl` no `/health` local |

## Portas API na mesma VPS

| Porta | Uso |
|-------|-----|
| `8000` | DuplexSoft (compose legado) |
| `8001` | admin-center (control-plane) |
| `8002+` | clientes em `deploy/clients/<slug>/` |

Registre numa folha interna qual `CLIENT_API_PORT` cada slug usa. O Nginx faz proxy para `127.0.0.1:PORTA`.

## Atualizar código de um cliente

No VPS, no clone do repositório:

```bash
git pull
export DX_CONNECT_GIT_SHA=$(git rev-parse --short HEAD)
bash deploy/scripts/stack-client.sh migrate exemplo
bash deploy/scripts/stack-client.sh up exemplo
```

### Volume `/app/data` (anexos e mídia)

O template monta `backend_data` → `/app/data`. Sem esse volume, cada rebuild apaga anexos de ticket, mídia WhatsApp/chat interno, KB e logos — o metadado fica na BD e o download devolve **404**.

Clientes já provisionados **antes** deste volume: copie o bloco `volumes` do `_template/docker-compose.stack.yml` para o `docker-compose.yml` do cliente e faça `up` de novo. Arquivos já perdidos não voltam; é preciso reenviar anexos.

## Backup da base do cliente

```bash
docker exec dx-connect-db-exemplo pg_dump -U dxconnect dxconnect_exemplo > backup-exemplo-$(date +%F).sql
```

(ajuste user/db/slug conforme `client.env`)

## Relacionado

- Deploy CI (duas stacks): [`deploy/github-actions.md`](../github-actions.md)
- Control-plane + runbook desativar cliente: [`docs/SAAS_CONTROL_PLANE.md`](../../docs/SAAS_CONTROL_PLANE.md)
- `docker-compose.prod.yml` — API DuplexSoft legado (Postgres no host / stack antiga na mesma máquina)
- Desativar cliente sem derrubar SaaS: âncora `#runbook-desativar-cliente-sem-derrubar-o-saas` no doc do control-plane
