# Deploy com GitHub Actions (SSH + Docker Compose)

O workflow [`.github/workflows/deploy.yml`](../.github/workflows/deploy.yml) faz:

1. **Build do frontend** no runner (usa `VITE_API_URL` dos secrets).
2. **`rsync`** da pasta `frontend/dist/` para o caminho no VPS (`DEPLOY_FRONTEND_DIST`).
3. **SSH** no servidor: `git pull`, `alembic upgrade head`, `docker compose -f docker-compose.prod.yml up -d --build`.

Disparo automático em **push** para **`main`** quando mudam `backend/`, `frontend/`, `docker-compose.prod.yml` ou o próprio workflow. Após merge de um PR em **`main`**, o deploy roda sozinho (se os paths acima mudaram). Também pode rodar manualmente em **Actions → Deploy → Run workflow**.

### Por que não usar mais a branch `staging` no GitHub?

Antes o fluxo era merge em `main` → PR `main → staging` → push em `staging` → deploy. Cada push em `staging` fazia o GitHub exibir o banner amarelo **“staging had recent pushes — Compare & pull request”** na aba Pull requests. Isso é comportamento nativo do GitHub (sugere abrir PR a partir da branch que recebeu push); **não há como desligar**. O botão apontava para `staging → main`, direção oposta ao release.

Com deploy na **`main`**, esse passo extra e o banner deixam de ser necessários. A branch `staging` no remoto pode ser apagada quando quiser (opcional); no VPS o workflow faz `git checkout main` e `git reset --hard origin/main`.

**Importante:** não defina `DEPLOY_GIT_REF` com uma branch diferente da que disparou o workflow — isso fazia o frontend atualizar e o backend continuar num commit antigo (rotas novas respondiam 404).

## Secrets no GitHub

Em **Settings → Secrets and variables → Actions → New repository secret**:

| Secret | Descrição |
|--------|-----------|
| `DEPLOY_HOST` | Hostname ou IP do VPS (ex.: `api.exemplo.com` ou IP) |
| `DEPLOY_USER` | Usuário SSH com permissão de `git`, `docker` e escrita em `DEPLOY_FRONTEND_DIST` |
| `DEPLOY_SSH_KEY` | Chave **privada** completa (PEM), linha `-----BEGIN ... KEY-----` até o fim |
| `DEPLOY_PATH` | Diretório no servidor onde está o **clone** deste repositório (ex.: `/home/deploy/dx-connect`) |
| `DEPLOY_FRONTEND_DIST` | Pasta servida pelo Nginx como root do SPA (ex.: `/var/www/dx-connect`). Deve existir e o usuário SSH precisa poder escrever (ex.: pertencer ao grupo `www-data` ou `chown` adequado). |
| `VITE_API_URL` | URL pública **HTTPS** da API, **sem barra no final** (igual ao `frontend/.env.production`) |

Opcionais:

| Secret | Descrição |
|--------|-----------|
| `DEPLOY_SSH_PORT` | Porta SSH se não for 22 |
| `DEPLOY_GIT_REF` | Override opcional da branch no VPS (só usado se o workflow não tiver `github.ref_name`; em push para `staging` usa a branch do push) |

### Environment `production` (opcional)

Se quiser **aprovação manual** ou secrets separados, crie um **Environment** chamado `production` no GitHub e descomente no workflow a linha `environment: production`. Configure os secrets no environment em vez dos secrets do repositório.

## Preparação única no VPS

1. **Clone do repositório** (repositório público ou configure acesso Git: SSH deploy key ou `https` com token):

   ```bash
   sudo mkdir -p /home/deploy && sudo chown "$USER:$USER" /home/deploy
   cd /home/deploy
   git clone https://github.com/SEU_USUARIO/dx-connect.git
   cd dx-connect
   ```

2. **`backend/.env` de produção** no servidor (não vai para o Git): copie de `backend/.env.example` e preencha. Veja também `docs/PRE_DEPLOY_CHECKLIST.md`.

3. **Docker**: usuário do deploy no grupo `docker` (`sudo usermod -aG docker "$USER"`) ou use `sudo` no workflow (não recomendado).

4. **Pasta do frontend** (exemplo):

   ```bash
   sudo mkdir -p /var/www/dx-connect
   sudo chown deploy:www-data /var/www/dx-connect
   ```

   Ajuste o `root` do Nginx para esse diretório e use o mesmo caminho em `DEPLOY_FRONTEND_DIST`.

5. **Primeira subida da API** (migrations e containers — inclui Evolution API):

   ```bash
   cd /home/deploy/dx-connect
   # backend/.env: EVOLUTION_GLOBAL_API_KEY, EVOLUTION_POSTGRES_PASSWORD,
   # EVOLUTION_INTERNAL_BASE_URL=http://127.0.0.1:8080, DX_CONNECT_WEBHOOK_BASE_URL=https://...
   docker compose --env-file backend/.env -f docker-compose.prod.yml run --rm -T backend alembic upgrade head < /dev/null
   docker compose --env-file backend/.env -f docker-compose.prod.yml up -d --build
   ```

6. **Chave SSH para o GitHub**: no seu PC ou no VPS, gere um par só para deploy:

   ```bash
   ssh-keygen -t ed25519 -f github-deploy -C "github-actions-dx-connect" -N ""
   ```

   Coloque o conteúdo de `github-deploy` (privada) no secret `DEPLOY_SSH_KEY`. No servidor, em `~/.ssh/authorized_keys` do `DEPLOY_USER`, adicione uma linha com o conteúdo de `github-deploy.pub`.

## Repositório privado

O servidor precisa conseguir `git pull`. Opções:

- **Deploy key** (somente leitura): Settings → Deploy keys → adicionar a chave **pública** do servidor; ou
- **PAT** em URL remota: `git remote set-url origin https://TOKEN@github.com/...` (menos ideal).

## Migrações

Em cada deploy o workflow executa `alembic upgrade head` antes do `up --build`. No **Run workflow** manual pode marcar **skip migrations** só em situações excepcionais.

## Troubleshooting

- **`Permission denied (publickey)`**: confira `DEPLOY_SSH_KEY`, usuário e `authorized_keys` no VPS.
- **`rsync` falha**: permissões em `DEPLOY_FRONTEND_DIST` e caminho absoluto correto.
- **`docker: permission denied`**: usuário no grupo `docker` ou reiniciar sessão SSH após `usermod`.
- **Build do frontend errado**: `VITE_API_URL` nos secrets deve ser a URL **pública** que o browser usa para chamar a API.
- **404 em `/v1/settings/*` ou `/v1/tenant/*` com frontend novo**: o SPA foi atualizado mas o **container da API** ainda está num commit antigo. Remova qualquer secret `DEPLOY_GIT_REF` que aponte para outra branch. No VPS: `bash deploy/scripts/redeploy-staging-backend.sh` (aceita branch como 2º argumento, padrão `staging`; use `main` se o clone já seguir `main`). Confirme: `curl -s https://SUA-API/health` deve incluir `"capabilities":{"settings_empresa_sistema":true,...}`.
- **Deploy SSH “passa” mas `/health` continua com `git_sha` antigo**: o `docker compose run` no script remoto (`bash -s` + heredoc) pode **consumir o stdin** e impedir o restart do backend. O workflow usa `run --rm -T ... < /dev/null` para evitar isso.
