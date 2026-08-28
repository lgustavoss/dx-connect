"""Idempotência da migration 134 — ponto_dias_convocados (#985)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import event
from sqlalchemy.pool import StaticPool

_MIGRATION_PATH = (
    Path(__file__).resolve().parents[1] / "alembic" / "versions" / "134_ponto_dia_convocado_985.py"
)

_OPTIONAL_COLUMNS = frozenset(
    {
        "tolerancia_minutos",
        "estado",
        "criado_por_id",
        "created_at",
        "cancelado_por_id",
        "cancelado_em",
    }
)

_EXPECTED_INDEXES = frozenset(
    {
        "ix_ponto_dias_convocados_tenant_id",
        "ix_ponto_dias_convocados_atendente_id",
        "ix_ponto_dias_convocados_data_ref",
        "ix_ponto_dias_convocados_atendente_data",
    }
)


def _load_migration():
    spec = importlib.util.spec_from_file_location("migration_134", _MIGRATION_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _sqlite_engine():
    engine = sa.create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _pragma_fk(dbapi_conn, _record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def _bootstrap_parents(conn) -> None:
    conn.execute(sa.text("CREATE TABLE tenants (id INTEGER PRIMARY KEY)"))
    conn.execute(sa.text("CREATE TABLE atendentes (id INTEGER PRIMARY KEY)"))
    conn.execute(sa.text("INSERT INTO tenants (id) VALUES (1)"))
    conn.execute(sa.text("INSERT INTO atendentes (id) VALUES (1)"))


def _run_upgrade(migration, engine) -> None:
    with engine.begin() as conn:
        ctx = MigrationContext.configure(conn)
        with Operations.context(ctx):
            migration.upgrade()


def _create_partial_convocados_table(conn) -> None:
    """Núcleo obrigatório + FKs como INTEGER (DDL manual típico); faltam opcionais simples."""
    conn.execute(
        sa.text(
            """
            CREATE TABLE ponto_dias_convocados (
                id INTEGER PRIMARY KEY,
                tenant_id INTEGER NOT NULL REFERENCES tenants(id),
                atendente_id INTEGER NOT NULL REFERENCES atendentes(id),
                data_ref DATE NOT NULL,
                inicio VARCHAR(5) NOT NULL,
                fim VARCHAR(5) NOT NULL,
                motivo VARCHAR(1000) NOT NULL,
                criado_por_id INTEGER,
                cancelado_por_id INTEGER
            )
            """
        )
    )


def _create_full_convocados_table_without_indexes(conn) -> None:
    conn.execute(
        sa.text(
            """
            CREATE TABLE ponto_dias_convocados (
                id INTEGER PRIMARY KEY,
                tenant_id INTEGER NOT NULL REFERENCES tenants(id),
                atendente_id INTEGER NOT NULL REFERENCES atendentes(id),
                data_ref DATE NOT NULL,
                inicio VARCHAR(5) NOT NULL,
                fim VARCHAR(5) NOT NULL,
                tolerancia_minutos INTEGER,
                motivo VARCHAR(1000) NOT NULL,
                estado VARCHAR(20) NOT NULL DEFAULT 'ativa',
                criado_por_id INTEGER REFERENCES atendentes(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                cancelado_por_id INTEGER REFERENCES atendentes(id),
                cancelado_em DATETIME
            )
            """
        )
    )


def _assert_schema_complete(engine) -> None:
    insp = sa.inspect(engine)
    assert insp.has_table("ponto_dias_convocados")
    cols = {c["name"] for c in insp.get_columns("ponto_dias_convocados")}
    assert _OPTIONAL_COLUMNS.issubset(cols)
    idxs = {i["name"] for i in insp.get_indexes("ponto_dias_convocados")}
    assert _EXPECTED_INDEXES.issubset(idxs)


def test_134_upgrade_idempotente_tabela_parcial():
    """DDL manual com núcleo + FKs como INTEGER; upgrade duas vezes completa opcionais simples."""
    migration = _load_migration()
    engine = _sqlite_engine()
    with engine.begin() as conn:
        _bootstrap_parents(conn)
        _create_partial_convocados_table(conn)

    _run_upgrade(migration, engine)
    _run_upgrade(migration, engine)
    _assert_schema_complete(engine)


def test_134_upgrade_idempotente_tabela_completa_sem_indices():
    """Tabela completa criada manualmente sem índices: upgrade duas vezes cria índices."""
    migration = _load_migration()
    engine = _sqlite_engine()
    with engine.begin() as conn:
        _bootstrap_parents(conn)
        _create_full_convocados_table_without_indexes(conn)

    _run_upgrade(migration, engine)
    _run_upgrade(migration, engine)
    _assert_schema_complete(engine)
