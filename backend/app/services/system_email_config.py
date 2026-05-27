"""
Configuração de e-mail do sistema (singleton `email_settings`).

Envio transaccional via **Resend API** (HTTP). Colunas SMTP/IMAP mantêm-se na BD por compatibilidade
migratória, mas o fluxo activo de tickets usa apenas a configuração transaccional.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.config import settings as app_settings
from app.models.email_settings import EmailSettings
from app.services.secret_box import decrypt_str


def get_singleton_email_settings(db: Session) -> EmailSettings | None:
    return db.query(EmailSettings).order_by(EmailSettings.id.asc()).first()


@dataclass(frozen=True)
class SmtpRuntimeConfig:
    host: str
    port: int
    user: str | None
    password: str | None
    use_starttls: bool
    from_email: str | None
    from_name: str | None


@dataclass(frozen=True)
class ImapRuntimeConfig:
    host: str
    port: int
    user: str
    password: str
    use_ssl: bool
    folder: str


def smtp_runtime_from_row(row: EmailSettings | None) -> SmtpRuntimeConfig | None:
    if not row:
        return None
    host = (row.smtp_host or "").strip()
    port = row.smtp_port
    if not host or not isinstance(port, int) or port <= 0:
        return None
    pwd = None
    if row.smtp_password_enc and str(row.smtp_password_enc).strip():
        pwd = decrypt_str(row.smtp_password_enc)
    return SmtpRuntimeConfig(
        host=host,
        port=port,
        user=(row.smtp_user or "").strip() or None,
        password=pwd,
        use_starttls=bool(row.smtp_use_starttls),
        from_email=(row.smtp_from_email or "").strip() or None,
        from_name=(row.smtp_from_name or "").strip() or None,
    )


def imap_runtime_from_row(row: EmailSettings | None) -> ImapRuntimeConfig | None:
    if not row:
        return None
    host = (row.imap_host or "").strip()
    port = row.imap_port
    if not host or not isinstance(port, int) or port <= 0:
        return None
    user = (row.imap_user or "").strip()
    pwd = None
    if row.imap_password_enc and str(row.imap_password_enc).strip():
        pwd = decrypt_str(row.imap_password_enc)
    if not user or not pwd:
        return None
    folder = (row.imap_folder or "INBOX").strip() or "INBOX"
    return ImapRuntimeConfig(
        host=host,
        port=port,
        user=user,
        password=pwd,
        use_ssl=bool(row.imap_use_ssl),
        folder=folder,
    )


@dataclass(frozen=True)
class TransactionalEmailConfig:
    api_key: str
    from_email: str
    from_name: str | None
    reply_to: str | None = None


def transactional_config_from_row(row: EmailSettings | None) -> TransactionalEmailConfig | None:
    """API Key: coluna cifrada na BD ou ``RESEND_API_KEY`` no ambiente. Remetente: BD ou env."""
    key = ""
    if row and row.transactional_api_key_enc and str(row.transactional_api_key_enc).strip():
        key = decrypt_str(row.transactional_api_key_enc) or ""
    key = (key or "").strip() or (app_settings.RESEND_API_KEY or "").strip()
    if not key:
        return None

    from_email = ""
    if row and (row.transactional_from_email or "").strip():
        from_email = str(row.transactional_from_email).strip()
    if not from_email:
        from_email = (app_settings.TRANSACTIONAL_FROM_EMAIL or "").strip()
    if not from_email:
        return None

    from_name = None
    if row and (row.transactional_from_name or "").strip():
        from_name = str(row.transactional_from_name).strip()
    if not from_name:
        fn = (app_settings.TRANSACTIONAL_FROM_NAME or "").strip()
        from_name = fn or None

    reply_to = (app_settings.SUPPORT_REPLY_TO_EMAIL or "").strip() or None

    return TransactionalEmailConfig(
        api_key=key,
        from_email=from_email,
        from_name=from_name,
        reply_to=reply_to,
    )
