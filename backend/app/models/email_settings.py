from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.database import Base


class EmailSettings(Base):
    """
    Singleton (1 linha): envio transaccional (Resend API) e colunas legadas SMTP/IMAP (não usadas no fluxo actual).
    A API Key fica em ``transactional_api_key_enc`` (cifrada); nunca exposta no GET.
    """

    __tablename__ = "email_settings"

    id = Column(Integer, primary_key=True, index=True)

    transactional_api_key_enc = Column(String(2048), nullable=True)
    transactional_from_email = Column(String(255), nullable=True)
    transactional_from_name = Column(String(255), nullable=True)

    smtp_host = Column(String(255), nullable=True)
    smtp_port = Column(Integer, nullable=True)
    smtp_user = Column(String(255), nullable=True)
    smtp_password_enc = Column(String(2048), nullable=True)
    smtp_use_starttls = Column(Boolean, default=True)
    smtp_from_email = Column(String(255), nullable=True)
    smtp_from_name = Column(String(255), nullable=True)

    imap_host = Column(String(255), nullable=True)
    imap_port = Column(Integer, nullable=True)
    imap_user = Column(String(255), nullable=True)
    imap_password_enc = Column(String(2048), nullable=True)
    imap_use_ssl = Column(Boolean, default=True)
    imap_folder = Column(String(255), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

