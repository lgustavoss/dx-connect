"""Sistema: empresa_sistema e email_settings (SMTP/IMAP).

Revision ID: 017_sys_email
Revises: 016_ticket_anexos
Create Date: 2026-04-29
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "017_sys_email"
down_revision = "016_ticket_anexos"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)

    if not insp.has_table("empresa_sistema"):
        op.create_table(
            "empresa_sistema",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("cnpj", sa.String(length=18), nullable=True),
            sa.Column("nome", sa.String(length=255), nullable=True),
            sa.Column("razao_social", sa.String(length=255), nullable=True),
            sa.Column("nome_fantasia", sa.String(length=255), nullable=True),
            sa.Column("email", sa.String(length=255), nullable=True),
            sa.Column("telefone", sa.String(length=20), nullable=True),
            sa.Column("endereco", sa.String(length=255), nullable=True),
            sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index(op.f("ix_empresa_sistema_id"), "empresa_sistema", ["id"], unique=False)
        op.create_index(op.f("ix_empresa_sistema_cnpj"), "empresa_sistema", ["cnpj"], unique=False)

    if not insp.has_table("email_settings"):
        op.create_table(
            "email_settings",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("smtp_host", sa.String(length=255), nullable=True),
            sa.Column("smtp_port", sa.Integer(), nullable=True),
            sa.Column("smtp_user", sa.String(length=255), nullable=True),
            sa.Column("smtp_password_enc", sa.String(length=2048), nullable=True),
            sa.Column("smtp_use_starttls", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("smtp_from_email", sa.String(length=255), nullable=True),
            sa.Column("smtp_from_name", sa.String(length=255), nullable=True),
            sa.Column("imap_host", sa.String(length=255), nullable=True),
            sa.Column("imap_port", sa.Integer(), nullable=True),
            sa.Column("imap_user", sa.String(length=255), nullable=True),
            sa.Column("imap_password_enc", sa.String(length=2048), nullable=True),
            sa.Column("imap_use_ssl", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("imap_folder", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index(op.f("ix_email_settings_id"), "email_settings", ["id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if insp.has_table("email_settings"):
        op.drop_index(op.f("ix_email_settings_id"), table_name="email_settings")
        op.drop_table("email_settings")
    if insp.has_table("empresa_sistema"):
        op.drop_index(op.f("ix_empresa_sistema_cnpj"), table_name="empresa_sistema")
        op.drop_index(op.f("ix_empresa_sistema_id"), table_name="empresa_sistema")
        op.drop_table("empresa_sistema")

