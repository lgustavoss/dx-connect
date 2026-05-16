from pydantic import BaseModel, Field


class EmailSettingsRead(BaseModel):
    transactional_from_email: str | None = None
    transactional_from_name: str | None = None
    has_transactional_api_key: bool = False


class EmailSettingsUpdate(BaseModel):
    transactional_api_key: str | None = Field(
        default=None,
        description="API Key da Resend; omitir para manter; vazio para remover",
    )
    transactional_from_email: str | None = None
    transactional_from_name: str | None = None


class EmailTestResult(BaseModel):
    ok: bool
    detail: str | None = None
