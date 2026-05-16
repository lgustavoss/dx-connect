from pydantic import BaseModel, Field


class EmailSettingsRead(BaseModel):
    """Estado do envio transaccional (sem expor segredos). Configuração efectiva: variáveis de ambiente no servidor."""

    transactional_from_email: str | None = None
    transactional_from_name: str | None = None
    outbound_configured: bool = False
    has_transactional_api_key: bool = Field(
        default=False,
        description="Legado: API key gravada na BD (preferir RESEND_API_KEY no servidor).",
    )


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
