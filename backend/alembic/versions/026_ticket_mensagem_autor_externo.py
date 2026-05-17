"""ticket_mensagens: autor_externo para remetente de e-mail inbound.

Revision ID: 026_ticket_msg_autor_ext
Revises: 025_ticket_empresa_null
Create Date: 2026-05-17
"""

from alembic import op
import sqlalchemy as sa

revision = "026_ticket_msg_autor_ext"
down_revision = "025_ticket_empresa_null"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ticket_mensagens", sa.Column("autor_externo", sa.String(length=512), nullable=True))


def downgrade() -> None:
    op.drop_column("ticket_mensagens", "autor_externo")
