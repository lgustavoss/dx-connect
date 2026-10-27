"""Driver Postgres do SQLAlchemy 2.1 — postgresql:// não pode cair no psycopg 3."""

from sqlalchemy.engine.url import make_url

from app.config import _database_url_exige_ssl
from app.database import database_url_psycopg2


def test_postgresql_sem_driver_vira_psycopg2():
    assert (
        database_url_psycopg2("postgresql://u:p@db:5432/x?sslmode=require")
        == "postgresql+psycopg2://u:p@db:5432/x?sslmode=require"
    )


def test_postgres_scheme_vira_psycopg2():
    assert database_url_psycopg2("postgres://u:p@h/db") == "postgresql+psycopg2://u:p@h/db"


def test_psycopg2_explicito_permanece():
    url = "postgresql+psycopg2://u:p@h/db"
    assert database_url_psycopg2(url) == url


def test_sqlite_nao_muda():
    assert database_url_psycopg2("sqlite+pysqlite:///:memory:") == "sqlite+pysqlite:///:memory:"


def test_sqlalchemy_carrega_dialeto_psycopg2():
    url = database_url_psycopg2("postgresql://u:p@localhost/db")
    assert make_url(url).get_dialect().driver == "psycopg2"


def test_producao_ssl_aceita_url_com_driver():
    assert _database_url_exige_ssl("postgresql+psycopg2://u:p@db/x?sslmode=require")
    assert not _database_url_exige_ssl("postgresql+psycopg2://u:p@db/x")
