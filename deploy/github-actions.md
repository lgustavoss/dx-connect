# Deploy com GitHub Actions (SSH + Docker Compose)

O workflow [`.github/workflows/deploy.yml`](../.github/workflows/deploy.yml) faz:

1. Job **prepare**: build do frontend no runner (`VITE_API_URL`) + CalVer; envia artefacto.
2. Job **Deploy VPS**: SSH **IPv4** — `git pull`, `rsync` de `frontend/dist/` para `DEPLOY_FRONTEND_DIST`, Alembic, compose.
3. Se o SSH der `Connection timed out`, job **Deploy VPS (retry noutro runner)** — mesmo artefacto, IP novo. Ver troubleshooting abaixo.

Disparo automático em **push** para **`staging`** quando mudam `backend/`, `frontend/`, `docker-compose.prod.yml` ou o próprio workflow. A branch **`main`** não dispara deploy (último estágio de testes/integração); após validar em `main`, abra PR **`main → staging`**, merge e o deploy roda no VPS. Também pode rodar manualmente em **Actions → Deploy → Run workflow**.

**Importante:** não defina `DEPLOY_GIT_REF=main` nos secrets se o ambiente de produção segue a branch **`staging`** — isso fazia o frontend atualizar e o backend continuar na `main` (rotas novas como `/v1/settings/empresa-sistema` respondiam 404).

### Banner “staging had recent pushes” na aba Pull requests

Depois de mergear um release **`main → staging`**, o GitHub exibe um aviso amarelo sugerindo **Compare & pull request**. Isso é **comportamento nativo** (a branch `staging` acabou de receber push) e **não indica erro**. **Ignore o botão** — ele abriria PR na direção **`staging → main`**, oposta ao fluxo correto. Não há configuração no GitHub para desligar esse aviso enquanto o deploy continuar em push para `staging`.

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

### SSH timeout intermitente (`Connection timed out`)

**Sintoma** no log do job:

```text
ssh: connect to host *** port 22: Connection timed out
```

Costuma aparecer no job **Deploy VPS** (git pull / rsync / Alembic). O job **prepare** (build do frontend) pode ter passado. O log inclui o **IP público IPv4 do runner** (ex. via `api.ipify.org`) para cruzar com o firewall da Hostinger.

**Causa:** o TCP SYN para a porta 22 **não teve resposta** — o `sshd` nem chegou a autenticar. Não é chave SSH errada (`Permission denied (publickey)`). Hipóteses: firewall/proteção a **alguns** IPs do pool Azure do GitHub Actions; IPv6 partido (`DEPLOY_HOST` com AAAA e o runner insiste nesse caminho); rota transitória.

O retry **dentro do mesmo job** (5 tentativas, 15 s) usa o **mesmo** runner/IP e costuma falhar as 5 vezes seguidas. **Re-run all jobs** (ou o job `deploy-retry`) muda de máquina no pool `ubuntu-latest` e costuma ligar à primeira. O passo `ssh-keyscan` **não** engole falha: se não houver host key, o job falha com timeout vs DNS vs recusa.

**O que o workflow faz sozinho (#734):**

1. SSH e rsync forçam **IPv4** (`ssh -4` / `AddressFamily inet`).
2. Retry no mesmo job: [`deploy/scripts/retry.sh`](../deploy/scripts/retry.sh) (5×, 15 s, `ConnectTimeout=20`).
3. Se ainda for `Connection timed out` (exit 75), o job **Deploy VPS (retry noutro runner)** corre noutro `ubuntu-latest`, **sem** rebuild do frontend (reutiliza o artefacto).
4. Esse segundo job **não** corre em falhas que não são de rede (`Permission denied`, git/alembic/compose, health).

**Se o retry automático também falhar:**

1. **Re-run all jobs** no run falhado (não altere secrets).
2. Confira firewall do VPS, `sshd`, `DEPLOY_HOST` / `DEPLOY_SSH_PORT` e se o IP do servidor mudou. O IP do runner está no log.
3. **Actions → Deploy → Run workflow** na branch `staging` (deploy completo novo).

Fora de escopo: whitelist permanente de todos os ranges GitHub (mudam com frequência); self-hosted runner; mudar porta SSH ou credenciais.

### Outros erros comuns

- **`Permission denied (publickey)`**: confira `DEPLOY_SSH_KEY`, usuário e `authorized_keys` no VPS.
- **`rsync` falha**: permissões em `DEPLOY_FRONTEND_DIST` e caminho absoluto correto.
- **`docker: permission denied`**: usuário no grupo `docker` ou reiniciar sessão SSH após `usermod`.
- **Build do frontend errado**: `VITE_API_URL` nos secrets deve ser a URL **pública** que o browser usa para chamar a API.
- **404 em `/v1/settings/*` ou `/v1/tenant/*` com frontend novo**: o SPA foi atualizado mas o **container da API** ainda está na `main` antiga. Remova o secret `DEPLOY_GIT_REF=main` (deixe o workflow usar a branch do push, ex. `staging`). No VPS: `bash deploy/scripts/redeploy-staging-backend.sh`. Confirme: `curl -s https://SUA-API/health` deve incluir `"capabilities":{"settings_empresa_sistema":true,...}`.
- **Deploy SSH “passa” mas `/health` continua com `git_sha` antigo**: o `docker compose run` no script remoto (`bash -s` + heredoc) pode **consumir o stdin** e impedir o restart do backend. O workflow usa `run --rm -T ... < /dev/null` para evitar isso.
