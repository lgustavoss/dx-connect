# Testes da API (pytest)

O `conftest.py` define `DX_CONNECT_TESTING=1`, `DATABASE_URL` em **SQLite em memória** e `SECRET_KEY` de teste **antes** de importar a app. Os testes **não** usam o Postgres do `docker-compose` (evita apagar dados locais).

## Com Docker (recomendado no projeto)

O `docker-compose.yml` compila o backend com **`INSTALL_DEV=1`**, instalando `requirements-dev.txt` (pytest, httpx) na imagem.

```bash
# Na raiz do repositório
docker compose build backend
docker compose run --rm -v ./backend:/app backend pytest -q
```

- `pytest` substitui o comando padrão (`uvicorn`) só nesta execução.
- O bind mount (`-v ./backend:/app`) garante que **os testes do seu workspace** sejam executados (inclusive novos arquivos em `backend/tests/`).
- Se a imagem já existia de antes da issue #46, faça **`build`** de novo para incluir as dev deps.

## Sem Docker (máquina local)

```bash
cd backend
python -m pip install -r requirements-dev.txt
pytest
```

## PR e CI

O merge do PR deve passar no job **Pytest** do GitHub Actions. Se quiser **só mergear depois de ver verde**, rode o comando Docker acima antes de aprovar.

## Próximo passo

Casos de RBAC / tickets na issue **#47** (depende desta infra).
