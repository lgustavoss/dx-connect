"""
Infra de testes (#46): variáveis de ambiente antes de importar `app`.

`DX_CONNECT_TESTING=1` ativa lifespan mínimo em `app.main` (create_all, sem seed/IBGE).
"""
from __future__ import annotations

import os

# Sobrescreve .env local: SQLite em memória e modo de teste.
os.environ["DX_CONNECT_TESTING"] = "1"
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["SECRET_KEY"] = "01234567890123456789012345678901"
os.environ["ENVIRONMENT"] = "development"

import pytest
from starlette.testclient import TestClient


@pytest.fixture(scope="session")
def app():
    from app.main import app as fastapi_app

    return fastapi_app


@pytest.fixture(scope="session")
def client(app):
    with TestClient(app) as c:
        yield c


@pytest.fixture
def db_session(client):
    """Sessão SQLAlchemy (tabelas já criadas pelo `TestClient` / lifespan)."""
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
