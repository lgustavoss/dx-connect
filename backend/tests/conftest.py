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
os.environ["DEFAULT_TENANT_ID"] = "1"
os.environ["INBOUND_EMAIL_DOMAIN"] = "inbound.dx.test"

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


@pytest.fixture(autouse=True)
def _clean_db(db_session):
    """Limpa dados entre testes (SQLite :memory: é compartilhado via StaticPool)."""
    from app.database import Base

    for table in reversed(Base.metadata.sorted_tables):
        db_session.execute(table.delete())
    db_session.commit()
    yield


@pytest.fixture
def seed_base(db_session):
    """Dados mínimos para testes de RBAC/tickets (sem depender de seed automático)."""
    from app.core.security import hash_senha
    from app.models import Atendente, Empresa, Rede, Setor, StatusTicket, Tenant

    t = Tenant(id=1, nome="Teste", ativo=True)
    db_session.add(t)
    db_session.flush()

    # Setores
    s1 = Setor(tenant_id=1, nome="Suporte", slug="suporte", ativo=True)
    s2 = Setor(tenant_id=1, nome="Financeiro", slug="financeiro", ativo=True)
    db_session.add_all([s1, s2])

    # Rede/Empresa (Ticket exige empresa_id)
    r = Rede(tenant_id=1, nome="Rede Teste", ativo=True)
    db_session.add(r)
    db_session.flush()
    e = Empresa(tenant_id=1, rede_id=r.id, nome="Empresa Teste", ativo=True)
    db_session.add(e)

    # Status inicial (Ticket.create exige ao menos um status ativo)
    st = StatusTicket(nome="Aguardando atendimento", slug="aguardando_atendimento", ordem=1, ativo=True)
    db_session.add(st)

    # Usuários
    admin = Atendente(
        tenant_id=1,
        email="admin@test.local",
        nome="Admin",
        senha_hash=hash_senha("admin123"),
        role="admin",
        ativo=True,
        must_change_password=False,
    )
    a1 = Atendente(
        tenant_id=1,
        email="atendente1@test.local",
        nome="Atendente 1",
        senha_hash=hash_senha("at123"),
        role="atendente",
        ativo=True,
        must_change_password=False,
    )
    a2 = Atendente(
        tenant_id=1,
        email="atendente2@test.local",
        nome="Atendente 2",
        senha_hash=hash_senha("at123"),
        role="atendente",
        ativo=True,
        must_change_password=False,
    )
    comercial = Atendente(
        tenant_id=1,
        email="comercial@test.local",
        nome="Comercial",
        senha_hash=hash_senha("com123"),
        role="comercial",
        ativo=True,
        must_change_password=False,
    )
    db_session.add_all([admin, a1, a2, comercial])
    db_session.flush()

    # Vínculos de setor (admin sem setores; atendentes em setores distintos)
    a1.setores.append(s1)
    a2.setores.append(s2)

    db_session.commit()
    return {
        "tenant": t,
        "setor1": s1,
        "setor2": s2,
        "rede": r,
        "empresa": e,
        "status": st,
        "admin": admin,
        "a1": a1,
        "a2": a2,
        "comercial": comercial,
    }


@pytest.fixture
def auth_headers(seed_base):
    """Cabeçalhos Authorization para os usuários seed."""
    from app.core.security import criar_access_token

    def headers_for(email: str) -> dict[str, str]:
        tok = criar_access_token({"sub": email, "tid": 1})
        return {
            "Authorization": f"Bearer {tok}",
            "X-Dx-Tenant-Id": "1",
        }

    return {
        "admin": headers_for(seed_base["admin"].email),
        "a1": headers_for(seed_base["a1"].email),
        "a2": headers_for(seed_base["a2"].email),
        "comercial": headers_for(seed_base["comercial"].email),
    }
