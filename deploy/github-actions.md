# Deploy com GitHub Actions (SSH + Docker Compose) — #734 / #880

O workflow [`.github/workflows/deploy.yml`](../.github/workflows/deploy.yml) faz:

1. **Dois builds** do frontend no runner:
   - **DuplexSoft** → `VITE_API_URL` (API do cliente), **sem** `VITE_SAAS_CONTROL_PLANE`
   - **admin-center** (landing / `/saas`) → `VITE_API_URL_ADMIN` + `VITE_SAAS_CONTROL_PLANE=true`
2. **`rsync`** de cada `dist` para o caminho Nginx correspondente no VPS.
3. **SSH**: `git pull` + `alembic upgrade` + rebuild:
   - Stack **DuplexSoft**: `docker-compose.prod.yml` + `backend/.env` (exige `SAAS_CONTROL_PLANE=false`)
   - Stack **comercial**: `deploy/scripts/stack-client.sh migrate|up admin-center`
4. Health das **duas** APIs com flags distintas (`saas_control_plane` false / true).

Disparo automático em **push** para **`staging`**. A branch **`main`** não dispara deploy. Após validar em `main`, PR **`main → staging`**, merge e o deploy roda no VPS. Também: **Actions → Deploy → Run workflow**.

**Importante:** não defina `DEPLOY_GIT_REF=main` nos secrets se a produção segue **`staging`**.

### Banner “staging had recent pushes”

Aviso nativo do GitHub após merge `main → staging`. **Ignore** o botão Compare & pull request (`staging → main`).

## Secrets no GitHub

Em **Settings → Secrets and variables → Actions → New repository secret**:

| Secret | Descrição |
|--------|-----------|
| `DEPLOY_HOST` | Hostname ou IP do VPS |
| `DEPLOY_USER` | Usuário SSH (`git`, `docker`, escrita nos dists) |
| `DEPLOY_SSH_KEY` | Chave **privada** completa (PEM) |
| `DEPLOY_PATH` | Clone do repo no servidor (ex.: `/opt/dx-connect`) |
| `DEPLOY_FRONTEND_DIST` | Dist do **painel DuplexSoft** (ex.: `/opt/dx-connect/frontend/dist`) |
| `DEPLOY_FRONTEND_DIST_ADMIN` | Dist da **landing/SaaS** (ex.: `/var/www/dx-connect/admin-center/dist`) |
| `VITE_API_URL` | HTTPS da API **DuplexSoft** sem barra final (ex.: `https://api-duplexsoft.deskrudder.com.br`) |
| `VITE_API_URL_ADMIN` | HTTPS da API **comercial** (ex.: `https://api.deskrudder.com.br`) |

Opcionais:

| Secret | Descrição |
|--------|-----------|
| `DEPLOY_SSH_PORT` | Porta SSH se não for 22 |
| `DEPLOY_GIT_REF` | Override da branch no VPS (evitar em produção normal) |

O workflow **recusa** trocar as URLs (comercial em `VITE_API_URL` ou DuplexSoft em `VITE_API_URL_ADMIN`).

### Environment `production` (opcional)

Environment com aprovação manual: descomente `environment: production` no workflow e coloque os secrets lá.

## Preparação única no VPS

1. Clone do repositório + `backend/.env` DuplexSoft (`SAAS_CONTROL_PLANE=false` + ingest após #878).
2. Stack comercial: `bash deploy/scripts/provision-control-plane.sh` + migrate/up/seed (ver [`admin-center/README.md`](admin-center/README.md)).
3. Pastas de dist:

   ```bash
   sudo mkdir -p /var/www/dx-connect/admin-center/dist
   sudo chown deploy:www-data /var/www/dx-connect/admin-center/dist /opt/dx-connect/frontend/dist
   ```

4. Nginx: DuplexSoft → `DEPLOY_FRONTEND_DIST`; `deskrudder.com.br` → `DEPLOY_FRONTEND_DIST_ADMIN`; APIs em `api-duplexsoft…` (:8000) e `api.deskrudder.com.br` (:8001).
5. Chave SSH do Actions em `authorized_keys` do `DEPLOY_USER`.

## Migrações

Cada deploy corre `alembic upgrade head` na BD DuplexSoft **e** na BD `admin-center` (salvo skip manual).

## Troubleshooting

### SSH timeout intermitente (`Connection timed out`)

**Sintoma** no log (job `deploy` ou `deploy-retry`):

```text
ssh: connect to host *** port 22: Connection timed out
```

O job **`build`** pode ter passado; a falha é só na ligação **runner → VPS**.

**O que o workflow faz (#734):** IPv4 forçado; até 5 tentativas; job **`deploy-retry`** noutro runner reutiliza o artefacto.

### Outros erros comuns

- **`Permission denied (publickey)`**: confira `DEPLOY_SSH_KEY` e `authorized_keys`.
- **`rsync` falha**: permissões nos dois caminhos de dist (`chown deploy:www-data` em ambos).
- **`admin-center não provisionado`**: falta `deploy/admin-center/client.env` no VPS.
- **`SAAS_CONTROL_PLANE=true` na DuplexSoft**: o deploy aborta de propósito — corrigir `backend/.env` (cutover #878).
- **Landing fala com API DuplexSoft**: dist admin desatualizado ou `DEPLOY_FRONTEND_DIST_ADMIN` / secret `VITE_API_URL_ADMIN` errados.
- **404 em rotas novas**: `DEPLOY_GIT_REF=main` desalinhado — remova o secret e redeploye a `staging`.
- **Admin-center não sobe no deploy (API antiga)**: `stack-client.sh migrate` sem `-T`/`</dev/null` fazia o `docker compose run` consumir o stdin do SSH e engolir o `up` seguinte. O migrate já fecha o stdin; se voltar a acontecer, confira esse padrão.
- **Health público admin exit 22 no runner**: Cloudflare/rede no IP do GHA; o script valida loopback `127.0.0.1:8001` no VPS como fonte de verdade.