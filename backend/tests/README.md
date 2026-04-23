# Testes da API (pytest)

O `conftest.py` define `DX_CONNECT_TESTING=1`, `DATABASE_URL` em **SQLite em memória** e `SECRET_KEY` de teste **antes** de importar a app. Os testes **não** usam o Postgres do `docker-compose` (evita apagar dados locais).

## Com Docker (recomendado no projeto)

O `docker-compose.yml` compila o backend com **`INSTALL_DEV=1`**, instalando `requirements-dev.txt` (pytest, httpx) na imagem, e monta **`./backend` em `/app`**, para que alterações em `tests/` e em `app/` entrem no container **sem rebuild**.

```bash
# Na raiz do repositório (onde está docker-compose.yml)
docker compose build backend   # primeira vez ou após mudar requirements / Dockerfile
docker compose run --rm --no-deps backend pytest -q
```

- `pytest` substitui o comando padrão (`uvicorn`) só nesta execução.
- **`--no-deps`**: não sobe o Postgres; o `conftest.py` força SQLite em memória para os testes.
- **Rebuild** só é necessário quando mudam `requirements*.txt`, `Dockerfile` ou outras dependências da imagem — não por cada alteração em `.py` de testes ou da app.

## Sem Docker (máquina local)

```bash
cd backend
python -m pip install -r requirements-dev.txt
pytest
```

## PR e CI

O merge do PR deve passar no job **Pytest** do GitHub Actions. Se quiser **só mergear depois de ver verde**, rode o comando Docker acima antes de aprovar.

## Documentação de RBAC

Resumo das rotas v1 e perfis: [`../../docs/BACKEND_RBAC.md`](../../docs/BACKEND_RBAC.md).
