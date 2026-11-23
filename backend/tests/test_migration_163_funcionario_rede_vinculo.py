"""Exercita a migration 163 (N:N contato × rede) em SQLite descartável.

Não roda a cadeia inteira do Alembic (o projeto tem migrations específicas de
Postgres); monta o schema mínimo que a 163 toca e executa upgrade/backfill/
downgrade com `alembic.operations` reais sobre um banco temporário.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

BASE = Path(__file__).resolve().parents[1]
MIGRATION_PATH = BASE / "alembic" / "versions" / "163_funcionario_rede_vinculo.py"


def _carregar_migration():
    spec = importlib.util.spec_from_file_location("migration_163", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _executar(engine: sa.Engine, modulo, funcao) -> None:
    with engine.begin() as conn:
        contexto = MigrationContext.configure(conn)
        original = modulo.op
        modulo.op = Operations(contexto)
        try:
            funcao()
        finally:
            modulo.op = original


def _preparar_schema(engine: sa.Engine) -> None:
    with engine.begin() as conn:
        conn.exec_driver_sql(
            "CREATE TABLE redes ("
            " id INTEGER PRIMARY KEY, tenant_id INTEGER NOT NULL,"
            " nome VARCHAR(255) NOT NULL, ativo BOOLEAN)"
        )
        conn.exec_driver_sql(
            "CREATE TABLE empresas ("
            " id INTEGER PRIMARY KEY, tenant_id INTEGER NOT NULL,"
            " rede_id INTEGER NOT NULL REFERENCES redes(id), nome VARCHAR(255) NOT NULL,"
            " ativo BOOLEAN)"
        )
        conn.exec_driver_sql(
            "CREATE TABLE funcionarios_rede ("
            " id INTEGER PRIMARY KEY, nome VARCHAR(255) NOT NULL,"
            " tipo VARCHAR(20) NOT NULL,"
            " rede_id INTEGER REFERENCES redes(id),"
            " empresa_id INTEGER REFERENCES empresas(id))"
        )
        conn.exec_driver_sql(
            "CREATE TABLE funcionario_rede_empresa ("
            " id INTEGER PRIMARY KEY,"
            " funcionario_id INTEGER NOT NULL REFERENCES funcionarios_rede(id) ON DELETE CASCADE,"
            " empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE)"
        )
        conn.exec_driver_sql("INSERT INTO redes (id, tenant_id, nome) VALUES (1, 1, 'Rede 1'), (2, 1, 'Rede 2')")
        conn.exec_driver_sql(
            "INSERT INTO empresas (id, tenant_id, rede_id, nome) VALUES"
            " (10, 1, 1, 'Empresa da Rede 1'), (20, 1, 2, 'Empresa da Rede 2')"
        )
        conn.exec_driver_sql(
            "INSERT INTO funcionarios_rede (id, nome, tipo, rede_id, empresa_id) VALUES"
            " (1, 'Socio', 'socio', 1, NULL),"
            " (2, 'Supervisor', 'supervisor', NULL, NULL),"
            " (3, 'Colaborador', 'colaborador', NULL, 20),"
            " (4, 'Supervisor so uma rede', 'supervisor', NULL, NULL),"
            " (5, 'Socio sem rede', 'socio', NULL, NULL)"
        )
        conn.exec_driver_sql(
            "INSERT INTO funcionario_rede_empresa (id, funcionario_id, empresa_id) VALUES"
            " (1, 2, 10), (2, 2, 20), (3, 4, 10)"
        )


def _vinculos(engine: sa.Engine) -> set[tuple[int, int]]:
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text("SELECT funcionario_id, rede_id FROM funcionario_rede_vinculo")
        ).all()
    return {(int(fid), int(rid)) for fid, rid in rows}


def test_upgrade_backfill_idempotente_e_downgrade(tmp_path):
    engine = sa.create_engine(f"sqlite+pysqlite:///{tmp_path / 'migracao_163.db'}")
    _preparar_schema(engine)
    modulo = _carregar_migration()

    assert modulo.revision == "163_funcionario_rede_vinculo"
    assert modulo.down_revision == "162_titulo_multa"

    _executar(engine, modulo, modulo.upgrade)
    esperado = {
        (1, 1),  # sócio → rede_id
        (2, 1),  # supervisor → rede da empresa 10
        (2, 2),  # supervisor → rede da empresa 20
        (3, 2),  # colaborador → rede da empresa_id
        (4, 1),  # supervisor com uma única empresa
    }
    assert _vinculos(engine) == esperado

    # Rodar o upgrade de novo não duplica vínculos (backfill idempotente).
    _executar(engine, modulo, modulo.upgrade)
    assert _vinculos(engine) == esperado

    _executar(engine, modulo, modulo.downgrade)
    insp = sa.inspect(engine)
    assert not insp.has_table("funcionario_rede_vinculo")
