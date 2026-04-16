# Testes da API (pytest)

## Pré-requisitos

```bash
cd backend
python -m pip install -r requirements-dev.txt
```

## Executar

```bash
cd backend
pytest
```

Variáveis de ambiente para SQLite em memória e `DX_CONNECT_TESTING=1` são definidas em `conftest.py` antes de importar a aplicação.

## Próximo passo

Casos de RBAC / tickets na issue **#47** (depende desta infra).
