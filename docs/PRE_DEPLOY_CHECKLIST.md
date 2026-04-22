# Checklist pré-deploy (antes de contratar VPS)

Objetivo: o projeto ser **implantável** de forma repetível, não só na sua máquina.

Legenda: **OK** atendido no repositório | **Você** validação manual no servidor/domínio | **Parcial** requer atenção.

## Código e configuração

| Item | Status |
|------|--------|
| Backend com modo seguro (equivalente a `DEBUG=False`) | **OK** — `DEBUG=false` no `.env`; em `ENVIRONMENT=production` o app **recusa** subir com `DEBUG=true`. |
| Backend com servidor de produção (Gunicorn) | **OK** — imagem Docker usa `gunicorn` + `uvicorn.workers.UvicornWorker` (`gunicorn_conf.py`). Dev local continua com `uvicorn --reload` no `docker-compose.yml`. |
| Variáveis sensíveis fora do código | **OK** — `.env` / ambiente; `.env` no `.gitignore`. |
| Sem URL da API hardcoded no app (produção) | **OK** — frontend: `VITE_API_URL`; CORS: `CORS_ORIGINS`. Referências a `localhost` só em defaults de dev e no proxy do `vite.config.ts` (modo dev). |
| Frontend consome API via variável de ambiente | **OK** — build exige `VITE_API_URL`. |

**Nota:** Gunicorn **não roda no Windows** nativamente; valide com `docker build` / container Linux ou no próprio VPS.

## Banco de dados

| Item | Status |
|------|--------|
| PostgreSQL em todos os ambientes | **OK** — não há SQLite no caminho principal. |
| Migrations versionadas (Alembic) | **OK** — pasta `alembic/versions/`; com **`ENVIRONMENT=production`** o arranque **exige** tabela `alembic_version` (`production_require_alembic` em `app/core/lifecycle.py`) e **não** corre `create_all`. |
| Primeiro deploy (produção) | **Você** — criar DB/usuário no provedor; executar **`alembic upgrade head`** (ex.: `docker compose -f docker-compose.prod.yml run --rm backend alembic upgrade head`) **antes** da API subir; sem revisão Alembic a API encerra com erro explícito. |
| Desenvolvimento local | **Parcial** — fora de produção o lifespan pode executar `create_all` + seed (`app/main.py`); para espelhar produção/CI, preferir também `alembic upgrade head` no Postgres de dev. |
| Persistência após reinício | **Você** — dados ficam no PostgreSQL do provedor; reiniciar só o container não apaga o DB. |

## Frontend

| Item | Status |
|------|--------|
| `npm run build` sem erro | **OK** — com `VITE_API_URL` definida (ex.: `.env.production`). |
| Rodar com build estático / preview | **Você** — `npm run preview` ou servir `dist/` com nginx/painel. |
| Sem dependência de `npm run dev` em produção | **OK** — produção é só arquivos estáticos + API. |

## Docker (backend)

| Item | Status |
|------|--------|
| Container sobe sem passo manual extra | **OK** — `docker compose -f docker-compose.prod.yml up -d --build` + `.env` no servidor. |
| Não usa runserver / reload em produção | **OK** — `Dockerfile` = Gunicorn; compose de **dev** sobrescreve com `--reload`. |
| Variáveis injetadas corretamente | **OK** — `env_file` + `environment` onde necessário. |
| Simular produção localmente | **OK** — `docker-compose.prod.yml` apontando `DATABASE_URL` para um Postgres acessível (ex.: IP local ou túnel). |

## Integração

| Item | Status |
|------|--------|
| Frontend fala com API fora do localhost | **Você** — definir `VITE_API_URL` pública e publicar o `dist/`. |
| CORS correto | **Você** — `CORS_ORIGINS` com a origem HTTPS exata do site (com/sem `www`). |
| Login + fluxo principal | **Você** — testar em HTTPS após deploy. |

## Deploy automático (GitHub Actions)

| Item | Status |
|------|--------|
| Pipeline (build, rsync, Alembic no VPS, Compose) | **OK** — descrito em [`deploy/github-actions.md`](../deploy/github-actions.md); implementação em [`.github/workflows/deploy.yml`](../.github/workflows/deploy.yml). |
| Ramo que dispara em `push` | **OK** — por defeito **`staging`** (e `paths` em `backend/`, `frontend/`, `docker-compose.prod.yml`, workflow). Alinhe com a política do repositório (`main` vs `staging`). |
| Secrets e preparação do VPS | **Você** — tabela no `github-actions.md`; primeiro deploy continua a exigir `.env`, Postgres e `alembic upgrade head` como nas secções acima. |

## Segurança mínima

| Item | Status |
|------|--------|
| `SECRET_KEY` fora do repositório | **OK** — só no `.env` do servidor / CI. |
| `DEBUG=False` validado em produção | **OK** — `DEBUG=true` + `ENVIRONMENT=production` falha na validação. |
| Rotas sensíveis sem controle | **Parcial** — `/docs` e OpenAPI **desligados** quando `ENVIRONMENT=production`; demais rotas seguem auth nas próprias rotas. |
| JWT: sessão curta em produção | **OK** — `ACCESS_TOKEN_EXPIRE_MINUTES` máximo **30** com `ENVIRONMENT=production`. |
| `DATABASE_URL` com TLS ao PostgreSQL | **OK** — em produção a URL deve incluir `sslmode=require` (ou `verify-full` / `ssl=true`). **Você** confere no painel do provedor. |
| Header `Host` (cache poisoning) | **OK** — `TrustedHostMiddleware` quando `ALLOWED_HOSTS` ≠ `*` (obrigatório em produção). |
| Gunicorn `forwarded_allow_ips` | **OK** — padrão `127.0.0.1`; ajuste `GUNICORN_FORWARDED_ALLOW_IPS` se o proxy não for localhost. |
| Telas só admin no frontend | **OK** — `AdminRoute` exibe página 403 para não-admin (defesa em profundidade além da API). |
| XSS / dependências JS | **Você** — `npm audit` no frontend; CSP no Nginx; token em storage continua sensível a XSS até eventual refresh em cookie httpOnly. |
| CI + Dependabot no GitHub | **OK** — `.github/workflows/ci.yml` e `.github/dependabot.yml` (se usar outro Git, replique os passos manualmente). |

---

Antes de contratar o VPS, o mínimo **a fazer na sua máquina**: build do frontend com `VITE_API_URL`, `docker build` do backend (Linux), e um teste de login contra uma API já validada (pode ser staging). Se usar o deploy por Actions, siga também [`deploy/github-actions.md`](../deploy/github-actions.md) (secrets, SSH e ordem Alembic + `up`).
