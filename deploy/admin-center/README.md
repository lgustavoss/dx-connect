# Control-plane DeskRudder — Postgres + API próprios (#875)

A instância comercial **não** é a DuplexSoft. Clientes ficam em `deploy/clients/{slug}/`. O painel ops fica em **`deploy/admin-center/`**.

| Peça | Host | Porta loopback |
|------|------|----------------|
| API comercial | `api.deskrudder.com.br` | `127.0.0.1:8001` |
| Landing + `/saas` | `deskrudder.com.br` | SPA em `/var/www/dx-connect/admin-center/dist` |
| Helpdesk DuplexSoft | `duplexsoft.deskrudder.com.br` / `api-duplexsoft…` | `127.0.0.1:8000` (compose legado) |

## No VPS

```bash
cd /opt/dx-connect   # ou o clone de deploy
git pull
bash deploy/scripts/provision-control-plane.sh
# Gera client.env, docker-compose.yml e certs/ (TLS self-signed do Postgres).
# Guarde a senha do ops impressa. Edite client.env (Resend, etc.).
bash deploy/scripts/stack-client.sh migrate admin-center
bash deploy/scripts/stack-client.sh up admin-center
bash deploy/scripts/stack-client.sh seed admin-center
bash deploy/scripts/stack-client.sh health admin-center
```

Health esperado: `"saas_control_plane": true`.

DNS: `api.deskrudder.com.br` → IP da VPS. Nginx: copie `nginx.site.conf.example` e peça TLS (Certbot).

SPA comercial (dist **separado** do cliente — não sobrescreve o `frontend/dist` da DuplexSoft):

```bash
cd /opt/dx-connect/frontend
export VITE_API_URL=https://api.deskrudder.com.br
export VITE_SAAS_CONTROL_PLANE=true
export VITE_MARKETING_SITE_URL=https://deskrudder.com.br
export VITE_CLIENT_APP_HOST=deskrudder.com.br
export VITE_DEFAULT_TENANT_ID=1
npm ci
npx vite build --outDir /tmp/admin-center-spa-dist --emptyOutDir
sudo mkdir -p /var/www/dx-connect/admin-center/dist
sudo rsync -a --delete /tmp/admin-center-spa-dist/ /var/www/dx-connect/admin-center/dist/
```

Nginx da landing (`deskrudder.com.br`): `root /var/www/dx-connect/admin-center/dist;`  
Painel DuplexSoft continua em `/opt/dx-connect/frontend/dist` (API `api-duplexsoft`).

## Cutover (#878) — feito em produção

1. Migrar tabelas SaaS + mídia `solicitacao_media` + `protocol_sequences` (`kind=S`) + contas `saas_ops` para o Postgres do `admin-center`
2. Criar licença `clientes_saas` slug `duplexsoft` e token de ingest
3. Na DuplexSoft (`backend/.env`): `SAAS_CONTROL_PLANE=false`, `SAAS_INSTANCE_SLUG=duplexsoft`, `SAAS_CONTROL_PLANE_INGEST_URL` + `SAAS_INSTANCE_INGEST_TOKEN`
4. Desativar contas `saas_ops` na BD DuplexSoft (ficam só na comercial)
5. Health esperado: `api.deskrudder.com.br` → `saas_control_plane: true`; `api-duplexsoft…` → `false`

## Desativar um cliente

Runbook completo (pré/pós health, MCP, o que **não** parar):  
[`docs/SAAS_CONTROL_PLANE.md`](../../docs/SAAS_CONTROL_PLANE.md#runbook-desativar-cliente-sem-derrubar-o-saas)

Resumo: `stack-client.sh down <slug>` **ou** `docker compose … stop` na DuplexSoft — **nunca** `down admin-center`.

## O que este diretório versiona

Exemplos e o compose-template. `client.env` e `docker-compose.yml` gerados **não** vão no git.

## Issues

- #876 Postgres + container API
- #877 Nginx/TLS + SPA
- #878 migrar dados e desligar a flag na DuplexSoft
- #880 deploy GHA em dois stacks
- #879 docs/MCP após o cutover
