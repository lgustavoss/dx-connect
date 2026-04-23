"""Garante que a sessão de teste vê o mesmo SQLite que o lifespan (StaticPool)."""

from app.models import Atendente


def test_db_session_shares_schema_with_app(client, db_session):
    assert db_session.query(Atendente).count() == 0
