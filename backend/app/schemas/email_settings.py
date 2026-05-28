from pydantic import BaseModel, Field


class TicketEmailGraceOpcao(BaseModel):
    segundos: int
    rotulo: str


class EmailSettingsRead(BaseModel):
    """Estado do envio transaccional (sem expor segredos). Configuração efectiva: variáveis de ambiente no servidor."""

    transactional_from_email: str | None = None
    transactional_from_name: str | None = None
    transactional_reply_to_email: str | None = None
    outbound_configured: bool = False
    has_transactional_api_key: bool = Field(
        default=False,
        description="Legado: API key gravada na BD (preferir RESEND_API_KEY no servidor).",
    )
    ticket_mensagem_email_grace_seconds: int = Field(
        default=120,
        description="Espera antes de enviar e-mail ao cliente (0 = imediato).",
    )
    opcoes_ticket_mensagem_email_grace: list[TicketEmailGraceOpcao] = Field(
        default_factory=list,
        description="Opções disponíveis na UI de configurações.",
    )


class EmailSettingsUpdate(BaseModel):
    transactional_api_key: str | None = Field(
        default=None,
        description="API Key da Resend; omitir para manter; vazio para remover",
    )
    transactional_from_email: str | None = None
    transactional_from_name: str | None = None
    ticket_mensagem_email_grace_seconds: int | None = Field(
        default=None,
        description="Espera antes do envio (0 = imediato). Omitir para não alterar.",
    )


class EmailTestResult(BaseModel):
    ok: bool
    detail: str | None = None
