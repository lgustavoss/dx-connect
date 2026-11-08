"""Merge das duas cabeças: dispositivos FCM (#1311) e faturamento (#326/#328).

As migrations `155_dispositivos_fcm` (mobile) e `155_faturamento_anexos` foram
criadas em ramos paralelos com o mesmo número, cada uma apontando para
`154_deskremote_enroll`. Esta revisão junta as duas cabeças para o
`alembic upgrade head` voltar a ter um único destino.

Revision ID: 157_merge_fcm_faturamento
Revises: 155_dispositivos_fcm, 156_faturamento_titulos
Create Date: 2026-11-03
"""

from __future__ import annotations

revision = "157_merge_fcm_faturamento"
down_revision = ("155_dispositivos_fcm", "156_faturamento_titulos")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
