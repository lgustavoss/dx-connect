## DX Connect

Ferramenta interna de controle de tickets voltada para redes de postos/empresas, com visão separada por **rede**, **empresa** e **funcionários da rede**, preparada para integração futura com API de WhatsApp.

### Tecnologias

- **Backend**: FastAPI (Python), SQLAlchemy, JWT
- **Banco de dados**: PostgreSQL (via Docker Compose)
- **Frontend**: React + Vite + TypeScript + Tailwind CSS
- **Infra de desenvolvimento**:
  - Backend e banco sobem em containers Docker
  - Frontend roda em modo dev (Vite) consumindo o backend via proxy (`/api`)

### Principais funcionalidades

- **Autenticação e autorização**
  - Login de atendentes com JWT
  - Perfis: **admin** e **atendente**
  - Primeiro usuário admin criado pelo seed **em desenvolvimento** (`admin@email.com` / `admin123`). Em produção use `SEED_ADMIN_PASSWORD` no `.env` (mín. 8 caracteres) no `python -m app.seed`; a conta exige troca de senha no primeiro acesso.
  - **Atenção:** essas credenciais são **apenas para ambiente local**. Não use em produção. Se o repositório for público ou for copiado (fork), trate-as como públicas — qualquer pessoa pode lê-las no README.

- **Clientes**
  - **Redes**: cadastro de redes com visão detalhada
  - **Empresas**: vinculadas a uma rede
  - **Funcionários da rede**:
    - **Sócio**: vinculado à rede
    - **Supervisor**: vinculado a várias empresas
    - **Colaborador**: vinculado a uma empresa

- **Configurações**
  - **Setores**: ex.: suporte, financeiro etc.
  - **Atendentes**: usuários internos, com relacionamento N:N com setores
  - **Status de ticket**: totalmente configuráveis e com seed inicial (Aberto, Em atendimento, etc.)

- **Tickets**
  - Abertura de ticket vinculando empresa, setor, status e atendente
  - Histórico de alterações de status
  - Dashboard com:
    - Total de tickets
    - Tickets abertos hoje
    - Quantidade por status
    - Últimos tickets

### Estrutura do projeto

```text
dx-connect/
  backend/
    app/
      api/           # Rotas FastAPI
      models/        # Models SQLAlchemy
      schemas/       # Schemas Pydantic
      core/          # Auth, segurança, config
      seed.py        # Seed inicial (status + usuário admin)
  frontend/
    src/
      pages/         # Telas (Dashboard, Tickets, Redes, etc.)
      components/    # Layout, Sidebar, componentes de UI
      api/           # Cliente HTTP tipado
  docker-compose.yml # PostgreSQL + backend
```

### Como rodar em desenvolvimento

Pré‑requisitos:

- Docker e Docker Compose
- Node 18+ e npm

1. **Subir backend + banco**:

```bash
cd backend/..
docker compose up -d
```

O backend ficará acessível em `http://localhost:8000`.

2. **Rodar o frontend em modo dev**:

```bash
cd frontend
npm install
npm run dev
```

O frontend ficará acessível em `http://localhost:5173`.

3. **Login inicial** (só desenvolvimento; ver nota de segurança acima)

- Acesse `http://localhost:5173/login`
- Use:
  - E-mail: `admin@email.com`
  - Senha: `admin123`

### Scripts úteis

No **backend** (com API já a subir via Docker, na raiz do repositório):

- Rodar testes (pytest na imagem; não precisa de Python local): `docker compose run --rm --no-deps backend pytest -q` na raiz do repo — ver [`backend/tests/README.md`](backend/tests/README.md).

- Aplicar seed manualmente (com `docker compose up -d` em curso):

```bash
docker compose exec backend python -m app.seed
```

No **frontend** (a partir da pasta `frontend`):

- Rodar em desenvolvimento:

```bash
npm run dev
```

- Build de produção:

```bash
npm run build
```

### CI e rotina de segurança

- Com repositório no **GitHub**: workflow [`.github/workflows/ci.yml`](.github/workflows/ci.yml) (`pip-audit`, `npm audit`, `compileall`, build do frontend) e [Dependabot](.github/dependabot.yml) para `pip`/`npm`/Docker/actions.
- Localmente (antes de releases): `pip install pip-audit` e `pip-audit -r requirements.txt` na pasta `backend`; `npm audit` na pasta `frontend`.
- Guia curto: [`docs/SECURITY_MAINTENANCE.md`](docs/SECURITY_MAINTENANCE.md).

### Licença

Este projeto está licenciado sob os termos da licença **MIT**. Veja o arquivo `LICENSE` para mais detalhes.

# DX Connect

Sistema de controle de tickets interno, com suporte a rede de empresas, setores e funcionários (sócio, supervisor, colaborador).

## Estrutura

- **backend/** – API FastAPI (Python)
- **frontend/** – React + Vite + Tailwind (rodar fora do Docker em desenvolvimento)

## Desenvolvimento

### Pré-requisitos

- Docker Desktop (PostgreSQL + API em containers)
- Node.js (frontend local com hot reload)

### 1. Subir banco e API

```bash
docker compose up -d
```

- PostgreSQL: `localhost:5432` (usuário: `dxconnect`, senha: `dxconnect_secret`, DB: `dxconnect`)
- API: http://localhost:8000  
- Docs: http://localhost:8000/docs

No primeiro start, a API cria as tabelas e o seed: status de ticket e usuário admin.

**Login padrão (após seed em desenvolvimento):**
- E-mail: `admin@email.com`
- Senha: `admin123` (não use em produção)

### 2. Frontend (local, com hot reload)

```bash
cd frontend
npm install
npm run dev
```

- App: http://localhost:5173  
- As requisições para `/api/*` são proxy para `http://localhost:8000`.

### 3. Testes do backend (pytest via Docker)

Não é necessário instalar Python localmente: use a imagem do Compose (com dev deps).

```bash
# Na raiz do repositório
docker compose build backend
docker compose run --rm --no-deps backend pytest -q
```

- **`--no-deps`**: os testes usam SQLite em memória (`backend/tests/conftest.py`); o serviço `db` não precisa de estar a correr.
- O volume `./backend:/app` no `docker-compose.yml` sincroniza código e `tests/`; alterações nos arquivos refletem-se de imediato no container (rebuild só após mudanças em `requirements` ou `Dockerfile`).

Detalhes: [`backend/tests/README.md`](backend/tests/README.md). Matriz de rotas e perfis: [`docs/BACKEND_RBAC.md`](docs/BACKEND_RBAC.md). Configurações de e-mail + empresa do sistema: [`docs/EMAIL_SETTINGS.md`](docs/EMAIL_SETTINGS.md).

### 4. Ordem sugerida de uso

1. Fazer login com o admin.
2. Cadastrar **Redes** e **Empresas** (uma empresa pertence a uma rede).
3. Cadastrar **Setores** (ex.: Suporte, Financeiro).
4. Cadastrar **Atendentes** (vincule setores aos atendentes; admin não precisa de setor).
5. Cadastrar **Funcionários da rede** (sócio, supervisor, colaborador), se quiser.
6. Abrir e gerenciar **Tickets** (lista, filtros, detalhe, alterar status e atendente).

## Produção

Checklist alinhado ao deploy (o que já está no código vs o que validar no servidor): [`docs/PRE_DEPLOY_CHECKLIST.md`](docs/PRE_DEPLOY_CHECKLIST.md).  
Exemplos **Nginx** (HTTP, domínio → backend / estático) e checklist de **HSTS/CSP/limit_req**: [`deploy/nginx/README.md`](deploy/nginx/README.md).  
**Deploy automático** (GitHub Actions → SSH → `rsync` do frontend + `git pull` + Alembic + Docker Compose): [`deploy/github-actions.md`](deploy/github-actions.md).

**Backend (Docker, PostgreSQL externo)**  
- Configure `backend/.env` (veja `backend/.env.example`): `DATABASE_URL` com `sslmode=require` (ou equivalente), `SECRET_KEY` (32+ caracteres), `CORS_ORIGINS`, `ALLOWED_HOSTS` (hostnames da API, sem `*`), `ACCESS_TOKEN_EXPIRE_MINUTES` entre **1 e 30** em produção, `ENVIRONMENT=production`. Opcional: `GUNICORN_FORWARDED_ALLOW_IPS` se o reverse proxy não for `127.0.0.1`. Para o primeiro admin após `python -m app.seed`, defina `SEED_ADMIN_PASSWORD` (mín. 8 caracteres); sem isso o seed em produção não cria usuário admin padrão.  
- Subir: `docker compose -f docker-compose.prod.yml up -d --build`  
- Desenvolvimento local continua com `docker compose up` (API com `--reload` e banco `db` no compose).

**Frontend**  
- Crie `frontend/.env.production` com `VITE_API_URL=https://sua-api` (sem barra final) — veja `frontend/.env.example`.  
- Build: `cd frontend && npm run build`  
- Sirva a pasta `dist/` como site estático (painel Hostinger, nginx, etc.) com HTTPS.
