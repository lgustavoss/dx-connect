# Deploy por cliente — um stack Docker na VPS

Cada cliente pagante tem:

- **Subdomínio** próprio (`{slug}.deskrudder.com.br` + `api-{slug}.deskrudder.com.br`)
- **PostgreSQL** dedicado (container no stack do cliente)
- **Um container** da API (`dx-connect-api-{slug}`)
- **Porta loopback** distinta (`127.0.0.1:8002`, `8003`, …) para o Nginx fazer proxy

O **painel admin** DeskRudder (`/saas`) **não** fica em `clients/`. Pasta: [`../admin-center/`](../admin-center/README.md) (`provision-control-plane.sh`). Hosts: `deskrudder.com.br` e `api.deskrudder.com.br`. Não rode `provision-client.sh --slug deskrudder` nem `--slug admin-center`.

Direção de produto: [`docs/DEPLOYMENT_ARCHITECTURE.md`](../../docs/DEPLOYMENT_ARCHITECTURE.md) · Issue **#191** (Fase 1 + Fase 2 single-tenant no código).

## Estrutura

```text
deploy/clients/
  README.md                 # este ficheiro
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
  --slug duplexsoft \
  --base-domain deskrudder.com.br \
  --api-port 8001
```

Isto cria `deploy/clients/duplexsoft/` com `client.env` (senhas geradas), `docker-compose.yml` e ficheiros Nginx/frontend de exemplo.

### 1. Rever `client.env`

Edite `deploy/clients/duplexsoft/client.env`:

- `CORS_ORIGINS` / `ALLOWED_HOSTS` alinhados aos domínios reais (`CORS_ORIGINS` = origem HTTPS da PWA **e** `https://localhost` para o APK Capacitor)
- Par **VAPID** (`WEB_PUSH_VAPID_*`) desta stack — gerar uma vez; vazio = push desligado (`docs/OPERATIONS.md`)
- `DX_CONNECT_MULTI_TENANT=false` (padrão) e `CLIENT_APP_HOST={slug}.connect...`
- `RESEND_API_KEY`, e-mail transaccional, webhooks
- `SEED_ADMIN_EMAIL` / `SEED_ADMIN_PASSWORD` para o primeiro admin

### 2. Subir stack + migrações + seed

```bash
bash deploy/scripts/stack-client.sh migrate duplexsoft
bash deploy/scripts/stack-client.sh up duplexsoft
bash deploy/scripts/stack-client.sh seed duplexsoft
```

Confirme:

```bash
bash deploy/scripts/stack-client.sh health duplexsoft
```

### 3. Frontend

```bash
# Ajuste VITE_API_URL e VITE_CLIENT_APP_HOST em deploy/clients/duplexsoft/frontend.env.production.example
# ou copie para frontend/.env.production antes do build
cd frontend && npm ci && npm run build
sudo mkdir -p /var/www/dx-connect/clients/duplexsoft/dist
sudo rsync -a dist/ /var/www/dx-connect/clients/duplexsoft/dist/
```

### 4. Nginx + DNS

1. Copie `deploy/clients/duplexsoft/nginx.site.conf` para `/etc/nginx/sites-available/`.
2. Ajuste `FRONTEND_DIST` se necessário.
3. Aponte DNS `duplexsoft.connect...` e `api-duplexsoft.connect...` para a VPS.
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

Registe numa folha interna qual `CLIENT_API_PORT` cada slug usa (8001, 8002, …). O Nginx faz proxy para `127.0.0.1:PORTA`.

## Atualizar código de um cliente

No VPS, no clone do repositório:

```bash
git pull
export DX_CONNECT_GIT_SHA=$(git rev-parse --short HEAD)
bash deploy/scripts/stack-client.sh migrate duplexsoft
bash deploy/scripts/stack-client.sh up duplexsoft
```

### Volume `/app/data` (anexos e mídia)

O template monta `backend_data` → `/app/data`. Sem esse volume, cada rebuild apaga anexos de ticket, mídia WhatsApp/chat interno, KB e logos — o metadado fica na BD e o download devolve **404**.

Clientes já provisionados **antes** deste volume: copie o bloco `volumes` do `_template/docker-compose.stack.yml` para o `docker-compose.yml` do cliente e faça `up` de novo. Ficheiros já perdidos não voltam; é preciso reenviar anexos.

## Backup da base do cliente

```bash
docker exec dx-connect-db-duplexsoft pg_dump -U dxconnect dxconnect_duplexsoft > backup-duplexsoft-$(date +%F).sql
```

(ajuste user/db conforme `client.env`)

## Relacionado

- Deploy CI legado (um ambiente staging): [`deploy/github-actions.md`](../github-actions.md)
- `docker-compose.prod.yml` — API só, Postgres no host (modelo antigo single-tenant na mesma máquina)
