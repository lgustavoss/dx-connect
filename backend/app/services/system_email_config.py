"""
Configuração de e-mail do sistema (singleton `email_settings`).

Expõe leitura descriptografada para uso interno (envio IMAP/SMTP, jobs, #21/#20),
sem passar pelo schema da API (que mascara segredos).
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

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
