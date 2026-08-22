"""Geolocalização opcional nas batidas de ponto.

Revision ID: 108_ponto_geolocalizacao
Revises: 107_ponto_jornada_diaria
Create Date: 2026-08-21
"""

import sqlalchemy as sa
from alembic import op

revision = "108_ponto_geolocalizacao"
down_revision = "107_ponto_jornada_diaria"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("ponto_batidas"):
        return
    cols = {c["name"] for c in insp.get_columns("ponto_batidas")}
    if "latitude" not in cols:
        op.add_column("ponto_batidas", sa.Column("latitude", sa.Float(), nullable=True))
    if "longitude" not in cols:
        op.add_column("ponto_batidas", sa.Column("longitude", sa.Float(), nullable=True))
    if "accuracy_metros" not in cols:
        op.add_column("ponto_batidas", sa.Column("accuracy_metros", sa.Float(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("ponto_batidas"):
        return
    cols = {c["name"] for c in insp.get_columns("ponto_batidas")}
    for name in ("accuracy_metros", "longitude", "latitude"):
        if name in cols:
            op.drop_column("ponto_batidas", name)
