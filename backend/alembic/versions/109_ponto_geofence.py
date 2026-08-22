"""Geofence: locais da empresa + política de geo (#844).

Revision ID: 109_ponto_geofence
Revises: 108_ponto_geolocalizacao
Create Date: 2026-08-22
"""

import sqlalchemy as sa
from alembic import op

revision = "109_ponto_geofence"
down_revision = "108_ponto_geolocalizacao"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if insp.has_table("ponto_settings"):
        cols = {c["name"] for c in insp.get_columns("ponto_settings")}
        if "politica_geolocalizacao" not in cols:
            op.add_column(
                "ponto_settings",
                sa.Column(
                    "politica_geolocalizacao",
                    sa.String(20),
                    nullable=False,
                    server_default="opcional",
                ),
            )

    if not insp.has_table("ponto_locais"):
        op.create_table(
            "ponto_locais",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column(
                "tenant_id",
                sa.Integer(),
                sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
                nullable=False,
                index=True,
            ),
            sa.Column("nome", sa.String(255), nullable=False),
            sa.Column("latitude", sa.Float(), nullable=False),
            sa.Column("longitude", sa.Float(), nullable=False),
            sa.Column("raio_metros", sa.Integer(), nullable=False, server_default="200"),
            sa.Column("ativo", sa.Boolean(), nullable=False, server_default="true"),
        )

    if insp.has_table("ponto_batidas"):
        cols = {c["name"] for c in insp.get_columns("ponto_batidas")}
        if "fora_area" not in cols:
            op.add_column(
                "ponto_batidas",
                sa.Column("fora_area", sa.Boolean(), nullable=False, server_default="false"),
            )
        if "distancia_metros" not in cols:
            op.add_column("ponto_batidas", sa.Column("distancia_metros", sa.Float(), nullable=True))
        if "local_id" not in cols:
            op.add_column(
                "ponto_batidas",
                sa.Column(
                    "local_id",
                    sa.Integer(),
                    sa.ForeignKey("ponto_locais.id", ondelete="SET NULL"),
                    nullable=True,
                ),
            )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("ponto_batidas"):
        cols = {c["name"] for c in insp.get_columns("ponto_batidas")}
        for name in ("local_id", "distancia_metros", "fora_area"):
            if name in cols:
                op.drop_column("ponto_batidas", name)
    if insp.has_table("ponto_locais"):
        op.drop_table("ponto_locais")
    if insp.has_table("ponto_settings"):
        cols = {c["name"] for c in insp.get_columns("ponto_settings")}
        if "politica_geolocalizacao" in cols:
            op.drop_column("ponto_settings", "politica_geolocalizacao")
