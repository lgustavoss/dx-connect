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
# Guarde a senha do ops impressa. Edite client.env (Resend, etc.).
bash deploy/scripts/stack-client.sh migrate admin-center
bash deploy/scripts/stack-client.sh up admin-center
bash deploy/scripts/stack-client.sh seed admin-center
bash deploy/scripts/stack-client.sh health admin-center
```

Health esperado: `"saas_control_plane": true`.

DNS: `api.deskrudder.com.br` → IP da VPS. Nginx: copie `nginx.site.conf.example` e peça TLS (Certbot).

SPA comercial (dist **separado** do cliente):

```bash
cp deploy/admin-center/frontend.env.production.example frontend/.env.production
cd frontend && npm ci && npm run build
sudo mkdir -p /var/www/dx-connect/admin-center/dist
sudo rsync -a dist/ /var/www/dx-connect/admin-center/dist/
```

Até o cutover (#878), a DuplexSoft pode continuar com `SAAS_CONTROL_PLANE=true` no compose legado. Não desligue essa flag antes de migrar a fila.

## O que este diretório versiona

Exemplos e o compose-template. `client.env` e `docker-compose.yml` gerados **não** vão no git.

## Issues

- #876 Postgres + container API
- #877 Nginx/TLS + SPA
- #878 migrar dados e desligar a flag na DuplexSoft
- #880 deploy GHA em dois stacks
- #879 docs/MCP após o cutover
