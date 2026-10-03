from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.sql import func

from app.database import Base


class WhatsappFigurinhaFavorita(Base):
    """Galeria pessoal de figurinhas do atendente (#S202610-0001). Arquivo próprio, fora da retenção de mídia."""

    __tablename__ = "whatsapp_figurinhas_favoritas"
    __table_args__ = (
        UniqueConstraint("atendente_id", "sha256", name="uq_wpp_figurinha_fav_atendente_sha256"),
    )

    id = Column(Integer, primary_key=True, index=True)
    atendente_id = Column(
        Integer, ForeignKey("atendentes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    arquivo_nome = Column(String(500), nullable=False)
    mimetype = Column(String(128), nullable=False)
    sha256 = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
