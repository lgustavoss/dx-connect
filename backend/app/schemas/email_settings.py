from pydantic import BaseModel, Field


class EmailSettingsRead(BaseModel):
    smtp_host: str | None = None
    smtp_port: int | None = None
    smtp_user: str | None = None
    has_smtp_password: bool = False
    smtp_use_starttls: bool = True
    smtp_from_email: str | None = None
    smtp_from_name: str | None = None

    imap_host: str | None = None
    imap_port: int | None = None
    imap_user: str | None = None
    has_imap_password: bool = False
    imap_use_ssl: bool = True
    imap_folder: str | None = None


class EmailSettingsUpdate(BaseModel):
    smtp_host: str | None = None
    smtp_port: int | None = None
    smtp_user: str | None = None
    smtp_password: str | None = Field(default=None, description="Opcional; omitir para manter; vazio para limpar")
    smtp_use_starttls: bool | None = None
    smtp_from_email: str | None = None
    smtp_from_name: str | None = None

    imap_host: str | None = None
    imap_port: int | None = None
    imap_user: str | None = None
    imap_password: str | None = Field(default=None, description="Opcional; omitir para manter; vazio para limpar")
    imap_use_ssl: bool | None = None
    imap_folder: str | None = None


class EmailTestResult(BaseModel):
    ok: bool
    detail: str | None = None

