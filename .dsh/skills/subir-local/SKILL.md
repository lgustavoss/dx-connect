---
name: subir-local
description: "Sobe o DX Connect em desenvolvimento (Docker + API + frontend Vite), aplica migrations, faz seed se preciso e confirma health/portas."
whenToUse: "Quando o usuário pedir /subir-local, subir o ambiente local, rodar a stack em dev ou testar a UI localmente."
---

# /subir-local — ambiente local

Este skill é o comando `/subir-local` do DX Connect. O playbook completo está em
`.cursor/commands/subir-local.md` — **leia antes de começar**; se divergir deste
resumo, o playbook vence.

## Regras que não se negociam

- Executar na **raiz do repositório**.
- Nunca commitar `backend/.env`.
- **Não apagar o volume do Postgres** (`dx-connect_postgres_data`) sem avisar: é
  reset de dados locais. Só faça se o usuário pedir ou aprovar.
- Se o Docker não responder, pare e peça para abrir o Docker Desktop.

## Passos

1. **Diagnóstico**: `docker version`, `docker compose version`, `node --version`,
   `npm --version`.
2. **`backend/.env`**: se não existir, copie de `backend/.env.example`.
3. **Stack**: `docker compose up -d --build` (use `--build` se Dockerfile,
   `requirements*.txt` ou `docker-compose.yml` mudaram; senão `up -d`).
   Confira `docker compose ps` (db 5432, backend 8000, evolution-api 8080).
4. **Migrations** (obrigatório após pull com migration nova):
   ```
   docker compose run --rm --no-deps backend alembic heads
   docker compose run --rm --no-deps backend alembic upgrade head
   ```
5. **Seed** (primeiro uso/banco vazio; o backend tenta automático em dev):
   `docker compose exec backend python -m app.seed`.
   Login dev: http://localhost:5173/login — `admin@email.com` / `admin123`.
6. **Health**: `curl -s http://localhost:8000/health` (docs em `/docs`).
   Se não subir: `docker compose logs backend --tail 80` e
   `docker compose logs db --tail 30`.
7. **Frontend**: `cd frontend && npm install` (pule se `node_modules` e
   `package.json` estão ok) e `npm run dev` → http://localhost:5173 (proxy
   `/api` → 8000, sem `.env` em dev).
8. **Entrega**: tabela com Docker, migrations, health, frontend e login.

## Notas deste ambiente (Windows + DSH, já verificadas)

- Docker Desktop pode estar fechado. Inicie com
  `Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"` e aguarde o
  engine responder (`docker version`); pode levar ~40s.
- Rode o Vite como **job em background** (não bloqueie o chat):
  `cd frontend && npm run dev` em background e depois abra a URL.
- Backend "congelou" (reload do uvicorn preso em SSE, `/health` sem resposta):
  `docker compose up -d --force-recreate --no-deps backend` e confirme o health.
- Cache de imagem velho (falta `pytest-xdist`, dependências): reconstrua com
  `docker compose build backend` (o compose passa `INSTALL_DEV=1`).
- Vite estava rodando antes de um `npm install`? Pare e suba de novo, senão a UI
  fica preta com `Failed to resolve import`.
- Não existe Python no host; use sempre os comandos dentro do container.

## URLs

Painel http://localhost:5173 · API docs http://localhost:8000/docs · Evolution
http://localhost:8080 · parar com `docker compose down`.
