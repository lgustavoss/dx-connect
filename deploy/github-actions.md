# Deploy com GitHub Actions (SSH + Docker Compose)

Documentação relacionada: checklist geral [`docs/PRE_DEPLOY_CHECKLIST.md`](../docs/PRE_DEPLOY_CHECKLIST.md), índice [`docs/README.md`](../docs/README.md), Nginx [`deploy/nginx/README.md`](./nginx/README.md).

O workflow [`.github/workflows/deploy.yml`](../.github/workflows/deploy.yml) faz:

1. **Build do frontend** no runner (usa o secret `VITE_API_URL` — mesma ideia que `frontend/.env.production`).
2. **`rsync`** da pasta `frontend/dist/` para o caminho no VPS (`DEPLOY_FRONTEND_DIST`).
3. **SSH** no servidor: `git fetch` / `checkout` / `pull` na ref configurada, **`docker compose -f docker-compose.prod.yml run --rm backend alembic upgrade head`** (salvo opção “skip migrations”), depois **`docker compose -f docker-compose.prod.yml up -d --build`**.

**Disparo automático:** **push** para a branch **`staging`** quando mudam `backend/`, `frontend/`, `docker-compose.prod.yml` ou o próprio workflow (ver `on.push` no YAML). Para usar **`main`** (ou outra), altere `branches` em `.github/workflows/deploy.yml`.

**Execução manual:** **Actions → Deploy → Run workflow** (em qualquer branch do repositório no GitHub; no servidor, o `git pull` usa `DEPLOY_GIT_REF`, por defeito **`main`**).

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
| `DEPLOY_GIT_REF` | Branch no **servidor** após o SSH (`git checkout` + `git pull`). Padrão **`main`** se omitido. *Não* altera o branch que dispara o workflow no GitHub (hoje: **`staging`** no `push`). |

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

2. **`backend/.env` de produção** no servidor (não vai para o Git): copie de `backend/.env.example` e preencha. Antes do primeiro `up`, aplique migrações (`alembic upgrade head`) — o arranque em produção **exige** `alembic_version` (ver comentários em `.env.example` e [`docs/PRE_DEPLOY_CHECKLIST.md`](../docs/PRE_DEPLOY_CHECKLIST.md)).

3. **Docker**: usuário do deploy no grupo `docker` (`sudo usermod -aG docker "$USER"`) ou use `sudo` no workflow (não recomendado).

4. **Pasta do frontend** (exemplo):

   ```bash
   sudo mkdir -p /var/www/dx-connect
   sudo chown deploy:www-data /var/www/dx-connect
   ```

   Ajuste o `root` do Nginx para esse diretório e use o mesmo caminho em `DEPLOY_FRONTEND_DIST`.

5. **Primeira subida da API** (migrations e container):

   ```bash
   cd /home/deploy/dx-connect
   docker compose -f docker-compose.prod.yml run --rm backend alembic upgrade head
   docker compose -f docker-compose.prod.yml up -d --build
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

Em cada deploy o workflow executa `docker compose -f docker-compose.prod.yml run --rm backend alembic upgrade head` **no servidor** antes do `up --build`, alinhado ao [`docs/PRE_DEPLOY_CHECKLIST.md`](../docs/PRE_DEPLOY_CHECKLIST.md) (produção sem `create_all`).

Na execução manual (**Run workflow**), pode marcar **skip migrations** (booleano) só em situações excepcionais; em **push** o valor é sempre falso (migrations correm).

## Troubleshooting

- **`Permission denied (publickey)`**: confira `DEPLOY_SSH_KEY`, usuário e `authorized_keys` no VPS.
- **`rsync` falha**: permissões em `DEPLOY_FRONTEND_DIST` e caminho absoluto correto.
- **`docker: permission denied`**: usuário no grupo `docker` ou reiniciar sessão SSH após `usermod`.
- **Build do frontend errado**: `VITE_API_URL` nos secrets deve ser a URL **pública** que o browser usa para chamar a API.
