# Subir local

Suba o DX Connect em **desenvolvimento** (Docker + frontend Vite) e confirme que está acessível.

## Pré-requisitos

- Docker Desktop **rodando**
- Node.js 18+ e npm (frontend local)
- Executar na **raiz do repositório**

## Passo 1 — Diagnóstico

```bash
docker version
docker compose version
node --version
npm --version
```

Se Docker não responder, **pare** e oriente o usuário a abrir o Docker Desktop.

## Passo 2 — Arquivo `backend/.env`

Se `backend/.env` **não existir**:

```bash
cp backend/.env.example backend/.env
```

No Windows (PowerShell):

```powershell
Copy-Item backend\.env.example backend\.env
```

Não commitar `.env`.

## Passo 3 — Subir stack Docker

Na raiz:

```bash
docker compose up -d --build
```

Use `--build` se `Dockerfile`, `requirements*.txt` ou `docker-compose.yml` mudaram; caso contrário `docker compose up -d` basta.

Serviços esperados:

| Serviço | Porta | Uso |
|---------|-------|-----|
| `db` | 5432 | PostgreSQL DX Connect |
| `backend` | 8000 | API FastAPI |
| `evolution-api` | 8080 | WhatsApp (dev) |
| `evolution-db` / `evolution-redis` | interno | Evolution |

Aguarde containers saudáveis:

```bash
docker compose ps
```

## Passo 4 — Migrations (recomendado)

Após `git pull` ou ao trabalhar com branch que alterou `backend/alembic/`:

```bash
docker compose run --rm --no-deps backend alembic heads
docker compose run --rm --no-deps backend alembic upgrade head
```

Em dev a API também roda `create_all` no startup, mas **migrations Alembic** mantêm o schema alinhado ao repo (obrigatório após pull com migrations novas).

## Passo 5 — Seed (se banco vazio ou primeiro uso)

O backend tenta seed automático em dev. Se login falhar:

```bash
docker compose exec backend python -m app.seed
```

Login dev (só local):

- URL: http://localhost:5173/login
- E-mail: `admin@email.com`
- Senha: `admin123`

## Passo 6 — Health check da API

```bash
curl -s http://localhost:8000/health
```

Ou abra http://localhost:8000/docs

Se API não subir, inspecione:

```bash
docker compose logs backend --tail 80
docker compose logs db --tail 30
```

## Passo 7 — Frontend (Vite)

```bash
cd frontend
npm install
npm run dev
```

- App: http://localhost:5173
- Proxy `/api` → http://localhost:8000 (não precisa `frontend/.env` em dev)

Se `node_modules` já existir e `package.json` não mudou, pule `npm install`.

### Rodar frontend em background (opcional)

Se o agente precisar manter o terminal livre:

**PowerShell:**

```powershell
cd frontend; Start-Process npm -ArgumentList "run","dev" -NoNewWindow
```

**bash:**

```bash
cd frontend && npm run dev
```

(rodar em terminal em background / segunda aba)

## Passo 8 — Entrega

Reporte:

| Item | Status |
|------|--------|
| Docker (`docker compose ps`) | ... |
| Migrations (`alembic heads`) | ... |
| API http://localhost:8000/health | ... |
| Frontend http://localhost:5173 | ... |
| Login admin | ok / precisa seed |

### URLs úteis

- Painel: http://localhost:5173
- API docs: http://localhost:8000/docs
- Evolution (diagnóstico WhatsApp): http://localhost:8080

### Parar ambiente

```bash
docker compose down
```

Frontend: `Ctrl+C` no terminal do Vite.

### Rebuild completo (se algo estranho)

```bash
docker compose down
docker compose up -d --build
docker compose run --rm --no-deps backend alembic upgrade head
```

### Banco dessincronizado (migrations falham / colunas faltando)

Sintomas: `DuplicateTable` no Alembic, `UndefinedColumn` nos logs, `/health` lento ou 500.

Causa comum: volume Postgres antigo + `create_all` em dev sem Alembic alinhado.

**Reset só do Postgres de dev** (apaga dados locais):

```bash
docker compose stop backend db
docker volume rm dx-connect_postgres_data
docker compose up -d
docker compose run --rm --no-deps backend alembic upgrade head
docker compose exec backend python -m app.seed
```

### Frontend: dependências faltando

Se Vite avisar `recharts` / `react-markdown` não resolvidos:

```bash
cd frontend && npm install
```

Reinicie `npm run dev` após instalar.

Se o Vite já estava rodando **antes** do `npm install`, pare (`Ctrl+C`) e suba de novo — senão a UI fica preta com erro `Failed to resolve import`.

## Referências

- `README.md` — desenvolvimento
- `docs/WHATSAPP_EVOLUTION.md` — QR Code WhatsApp em dev
- `docs/ALEMBIC_MIGRATIONS.md` — troubleshooting migrations
