"""Revision ID: 036_ticket_classificacao_prioridade
Revises: 035_empresa_pdvs
"""

from alembic import op
import sqlalchemy as sa

revision = "036_ticket_classificacao"
down_revision = "035_empresa_pdvs"
branch_labels = None
depends_on = None

PRIORIDADE = sa.Enum("baixa", "normal", "alta", "urgente", name="ticket_prioridade", native_enum=False)

NATUREZAS_SEED = (
    ("Erro", "erro", 10),
    ("Dúvida", "duvida", 20),
    ("Solicitação", "solicitacao", 30),
)

MOTIVOS_SEED = (
    ("erro", "Falha no PDV", "falha-pdv", 10),
    ("erro", "Entrada de NF", "entrada-nf", 20),
    ("erro", "Outros", "outros", 99),
    ("duvida", "Operacional", "operacional", 10),
    ("duvida", "Fiscal", "fiscal", 20),
    ("duvida", "Outros", "outros", 99),
    ("solicitacao", "Configuração", "configuracao", 10),
    ("solicitacao", "Treinamento", "treinamento", 20),
    ("solicitacao", "Outros", "outros", 99),
)


def upgrade() -> None:
    op.create_table(
        "ticket_naturezas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nome", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(50), nullable=False),
        sa.Column("ordem", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("slug", name="uq_ticket_natureza_slug"),
    )
    op.create_index("ix_ticket_naturezas_slug", "ticket_naturezas", ["slug"])

    op.create_table(
        "ticket_motivos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("natureza_id", sa.Integer(), sa.ForeignKey("ticket_naturezas.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("nome", sa.String(120), nullable=False),
        sa.Column("slug", sa.String(50), nullable=False),
        sa.Column("ordem", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("natureza_id", "slug", name="uq_ticket_motivo_natureza_slug"),
    )
    op.create_index("ix_ticket_motivos_natureza_id", "ticket_motivos", ["natureza_id"])

    PRIORIDADE.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "tickets",
        sa.Column("prioridade", PRIORIDADE, nullable=False, server_default="normal"),
    )
    op.add_column("tickets", sa.Column("motivo_id", sa.Integer(), nullable=True))
    op.add_column("tickets", sa.Column("motivo_outro_texto", sa.String(255), nullable=True))
    op.create_foreign_key(
        "fk_tickets_motivo_id",
        "tickets",
        "ticket_motivos",
        ["motivo_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_tickets_motivo_id", "tickets", ["motivo_id"])

    conn = op.get_bind()
    slug_to_natureza_id: dict[str, int] = {}
    for nome, slug, ordem in NATUREZAS_SEED:
        r = conn.execute(
            sa.text(
                "INSERT INTO ticket_naturezas (nome, slug, ordem, ativo) "
                "VALUES (:nome, :slug, :ordem, true) RETURNING id"
            ),
            {"nome": nome, "slug": slug, "ordem": ordem},
        )
        slug_to_natureza_id[slug] = r.scalar_one()

    for natureza_slug, nome, motivo_slug, ordem in MOTIVOS_SEED:
        conn.execute(
            sa.text(
                "INSERT INTO ticket_motivos (natureza_id, nome, slug, ordem, ativo) "
                "VALUES (:natureza_id, :nome, :slug, :ordem, true)"
            ),
            {
                "natureza_id": slug_to_natureza_id[natureza_slug],
                "nome": nome,
                "slug": motivo_slug,
                "ordem": ordem,
            },
        )


def downgrade() -> None:
    op.drop_index("ix_tickets_motivo_id", table_name="tickets")
    op.drop_constraint("fk_tickets_motivo_id", "tickets", type_="foreignkey")
    op.drop_column("tickets", "motivo_outro_texto")
    op.drop_column("tickets", "motivo_id")
    op.drop_column("tickets", "prioridade")
    op.drop_index("ix_ticket_motivos_natureza_id", table_name="ticket_motivos")
    op.drop_table("ticket_motivos")
    op.drop_index("ix_ticket_naturezas_slug", table_name="ticket_naturezas")
    op.drop_table("ticket_naturezas")
    PRIORIDADE.drop(op.get_bind(), checkfirst=True)
